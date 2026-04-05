import json
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langsmith import traceable
from core.llm import get_llm
from core.guardrails import validate_sql
from core.logger import get_logger

log = get_logger("sql_gen")

# Load schema context once
_schema_path = os.path.join(os.path.dirname(__file__), "..", "context", "schema.json")
with open(_schema_path, "r") as f:
    SCHEMA = json.load(f)

SCHEMA_TEXT = (
    f"Table: {SCHEMA['table_name']}\n"
    f"Description: {SCHEMA['description']}\n\n"
    "Columns:\n"
    + "\n".join(
        f"  - {col['name']} ({col['type']}): {col['description']}"
        for col in SCHEMA["columns"]
    )
)

SQL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert PostgreSQL query writer for business analytics.

{schema}

Before writing SQL, reason through these steps:
1. What is the user asking? (aggregation / ranking / comparison / filter / distribution / trend)
2. Which columns are relevant?
3. Is this "top item per group"? → use RANK() OVER (PARTITION BY group ORDER BY COUNT(*) DESC)
4. Is this comparing segments? → write one CTE per segment, then UNION ALL
5. Does it need grouping, ordering, limiting?
6. Will a plain SELECT work, or is a CTE required?

Rules:
- Only SELECT statements — no semicolons, no markdown, no backticks, no explanation
- Use exact column names from the schema
- Always alias aggregated columns with descriptive names
- Never use ORDER BY alone to find top-per-group — always use window functions
- Always use ILIKE for text value filters (e.g. color ILIKE 'pink') — never use = for user-supplied string values

Pattern — top item per group:
WITH ranked AS (
    SELECT col, group_col, COUNT(*) AS cnt,
           RANK() OVER (PARTITION BY group_col ORDER BY COUNT(*) DESC) AS rnk
    FROM table GROUP BY col, group_col
)
SELECT group_col, col, cnt FROM ranked WHERE rnk = 1

Pattern — compare two segments:
WITH seg_a AS (
    SELECT col, COUNT(*) AS cnt, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM table WHERE segment_col = 'A' GROUP BY col
),
seg_b AS (
    SELECT col, COUNT(*) AS cnt, RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM table WHERE segment_col = 'B' GROUP BY col
)
SELECT 'A' AS segment, col, cnt FROM seg_a WHERE rnk = 1
UNION ALL
SELECT 'B' AS segment, col, cnt FROM seg_b WHERE rnk = 1
"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior business analyst presenting findings to non-technical stakeholders.
Given a user question, the TOTAL row count, and a sample of query results (as JSON), deliver a structured, confident, and easy-to-read answer.

Format your response exactly like this:

**[One punchy headline sentence summarising the key finding]**

Then bullet points using relevant emojis, one finding per line:
• [emoji] [Group/Category] → [clear finding with number]
• [emoji] [Group/Category] → [clear finding with number]
...

Then optionally 1 closing "So what?" sentence with a business implication if relevant.

Rules:
- ALWAYS use the provided Total Rows as the authoritative count — never count rows in the JSON sample yourself
- If Total Rows > 0, results exist — never say "0" or "none" when Total Rows is positive
- Use emojis that match the context: 👔🛍💳📦🌍⭐📅💰 etc.
- Plain business language — no SQL, no technical terms
- State numbers directly and confidently — no hedging phrases
- If comparing groups, always show each group on its own bullet
- If Total Rows is 0, say no results were found and suggest rephrasing
- Keep the total response under 120 words
"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "Question: {question}\n\nTotal Rows: {total_rows}\n\nSample Results (up to 50 rows):\n{results}"),
])


def _build_lc_history(chat_history: list[dict]) -> list:
    """Convert app chat history dicts to LangChain message objects."""
    messages = []
    for turn in chat_history:
        messages.append(HumanMessage(content=turn["question"]))
        if turn.get("answer"):
            messages.append(AIMessage(content=turn["answer"]))
    return messages


@traceable(name="generate_sql")
def generate_sql(question: str, chat_history: list[dict] = None, llm_overrides: dict = None) -> tuple[str, str]:
    """Returns (sql, error)."""
    log.info("Generating SQL for: %s", question)
    llm = get_llm(overrides=llm_overrides)
    chain = SQL_PROMPT | llm | StrOutputParser()
    sql = chain.invoke({
        "schema": SCHEMA_TEXT,
        "question": question,
        "history": _build_lc_history(chat_history or []),
    }).strip()

    if sql.startswith("```"):
        sql = "\n".join(sql.split("\n")[1:-1]).strip()

    sql = sql.rstrip(";").strip()
    log.debug("Generated SQL:\n%s", sql)

    is_valid, err = validate_sql(sql)
    if not is_valid:
        log.warning("Guardrail blocked query: %s", err)
        return "", err

    return sql, ""


@traceable(name="generate_answer")
def generate_answer(question: str, results: list[dict], chat_history: list[dict] = None, llm_overrides: dict = None) -> str:
    """Generate a natural language answer from query results."""
    log.info("Generating answer for: %s (%d rows)", question, len(results))
    llm = get_llm(overrides=llm_overrides)
    chain = ANSWER_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({
        "question": question,
        "total_rows": len(results),
        "results": json.dumps(results[:50], indent=2),
        "history": _build_lc_history(chat_history or []),
    })
    log.debug("Answer: %s", answer[:200])
    return answer
