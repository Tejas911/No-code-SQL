import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from core.config_loader import load_config
cfg = load_config()
if cfg["langsmith"]["tracing_enabled"]:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", cfg["langsmith"]["project_name"])

from core.sql_gen import generate_sql, generate_answer, SCHEMA
from core.supabase_client import run_query
from core.data_handler import (
    to_dataframe, get_descriptive_stats,
    to_csv_bytes, to_excel_bytes, classify_result_size
)

import re as _re
_DOWNLOAD_KEYWORDS = _re.compile(
    r"\b(download|export|extract|give me (a |the )?(file|csv|excel)|save|get (the )?file)\b",
    _re.IGNORECASE,
)

def _wants_download(question: str) -> bool:
    return bool(_DOWNLOAD_KEYWORDS.search(question))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NLP to SQL — Shopping Insights",
    page_icon="🛍️",
    layout="wide",
)

# ── Session state init ────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of {question, sql, answer, row_count, df, error}
if "sample_q_trigger" not in st.session_state:
    st.session_state.sample_q_trigger = ""


# ── Helpers ───────────────────────────────────────────────────────────────────
def render_stats(df):
    numeric_stats, cat_stats = get_descriptive_stats(df)
    if not numeric_stats.empty:
        st.markdown("**Numeric Columns**")
        st.dataframe(numeric_stats, use_container_width=True)
    if not cat_stats.empty:
        st.markdown("**Categorical Columns**")
        st.dataframe(cat_stats, use_container_width=True)


def render_answer(answer: str):
    """Render the LLM answer as a styled card with proper markdown rendering."""
    import re
    # Convert markdown to HTML
    html = answer
    # **bold** → <strong>
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    # • or - bullets → styled list items
    lines = html.split("\n")
    rendered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("•") or stripped.startswith("-"):
            content = stripped.lstrip("•-").strip()
            rendered_lines.append(
                f'<div style="margin: 6px 0; padding-left: 8px; border-left: 2px solid #7c3aed22;">'
                f'{content}</div>'
            )
        elif stripped:
            rendered_lines.append(f'<p style="margin: 6px 0;">{stripped}</p>')
        else:
            rendered_lines.append('<br/>')
    body = "\n".join(rendered_lines)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
            border-left: 4px solid #7c3aed;
            border-radius: 12px;
            padding: 20px 24px;
            margin: 12px 0;
            box-shadow: 0 4px 15px rgba(124, 58, 237, 0.15);
        ">
            <div style="
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1.5px;
                color: #7c3aed;
                text-transform: uppercase;
                margin-bottom: 12px;
            ">✦ Insight</div>
            <div style="color: #e2e8f0; font-size: 15px; line-height: 1.8;">
                {body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_download_buttons(df, key_suffix=""):
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            "⬇️ Download CSV",
            data=to_csv_bytes(df),
            file_name="query_results.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_{key_suffix}",
        )
    with dl_col2:
        st.download_button(
            "⬇️ Download Excel",
            data=to_excel_bytes(df),
            file_name="query_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"xlsx_{key_suffix}",
        )


def render_result(turn: dict, idx: int):
    """Render a single chat turn result (data table + answer)."""
    if turn.get("error"):
        st.error(turn["error"])
        return

    df = turn.get("df")
    row_count = turn.get("row_count", 0)
    size_class = classify_result_size(row_count)

    st.caption(f"`{row_count}` rows returned")

    if turn.get("sql") and st.session_state.get("show_sql", True):
        with st.expander("Generated SQL", expanded=True):
            st.code(turn["sql"], language="sql")

    if size_class == "large":
        st.warning(f"⚠️ {row_count} rows — too large to display directly.")
        tab1, tab2 = st.tabs(["📥 Download Flat File", "📊 Descriptive Statistics"])
        with tab1:
            render_download_buttons(df, key_suffix=f"{idx}_large")
        with tab2:
            render_stats(df)

    elif size_class == "medium":
        st.dataframe(df, use_container_width=True)
        with st.expander("📥 Download"):
            render_download_buttons(df, key_suffix=f"{idx}_med")
        with st.expander("📊 Descriptive Statistics"):
            render_stats(df)
        if turn.get("answer"):
            render_answer(turn["answer"])

    else:
        st.dataframe(df, use_container_width=True)
        if turn.get("answer"):
            render_answer(turn["answer"])
        with st.expander("📊 Descriptive Statistics"):
            render_stats(df)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")

    llm_cfg = cfg["llm"]
    st.markdown("**LLM Settings**")

    # Provider selector
    from core.llm import get_all_models
    provider = st.selectbox(
        "Provider",
        options=["groq", "google"],
        index=0 if st.session_state.get("llm_provider", "groq") == "groq" else 1,
        key="llm_provider",
    )

    # Fetch models for selected provider
    all_models = get_all_models(os.environ.get("GROQ_API_KEY", ""))
    model_list = all_models.get(provider, [])
    saved_model = st.session_state.get("llm_model", llm_cfg["model"])
    default_idx = model_list.index(saved_model) if saved_model in model_list else 0

    llm_model = st.selectbox(
        "Model",
        options=model_list,
        index=default_idx,
        key="llm_model",
    )
    llm_max_tokens = st.slider(
        "Max Output Tokens",
        min_value=256,
        max_value=8192,
        step=256,
        value=st.session_state.get("llm_max_tokens", llm_cfg["max_tokens"]),
        key="llm_max_tokens",
    )
    llm_temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        value=float(st.session_state.get("llm_temperature", llm_cfg["temperature"])),
        key="llm_temperature",
    )
    llm_top_p = st.slider(
        "Top-P",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        value=float(st.session_state.get("llm_top_p", llm_cfg.get("top_p", 1.0))),
        key="llm_top_p",
    )

    data_cfg = cfg["data"]
    st.divider()
    st.markdown("**Data Thresholds**")
    st.code(
        f"Display rows limit:   {data_cfg['max_display_rows']}\n"
        f"Large data threshold: {data_cfg['large_data_threshold']}",
        language="yaml",
    )

    st.markdown("**Guardrails**")
    gr = cfg["guardrails"]
    st.code(
        f"Block destructive: {gr['block_destructive_queries']}\n"
        f"Allowed ops:       {gr['allowed_operations']}",
        language="yaml",
    )

    st.divider()

    # Schema section header with sync button inline
    schema_col, sync_col = st.columns([3, 1])
    with schema_col:
        st.markdown("**Dataset Schema**")
    with sync_col:
        sync_clicked = st.button("🔄", help="Sync schema from Supabase", use_container_width=True)

    if sync_clicked:
        with st.spinner("Syncing schema from Supabase..."):
            try:
                from core.schema_sync import sync_schema
                result = sync_schema()
                if result["unchanged"]:
                    st.success("✅ Schema is up to date — no changes detected.")
                else:
                    msgs = []
                    if result["added"]:
                        msgs.append(f"➕ Added: `{'`, `'.join(result['added'])}`")
                    if result["removed"]:
                        msgs.append(f"➖ Removed: `{'`, `'.join(result['removed'])}`")
                    if result["changed"]:
                        msgs.append(f"🔁 Type changed: `{'`, `'.join(result['changed'])}`")
                    st.warning("Schema updated:\n\n" + "\n\n".join(msgs))
                    # Reload SCHEMA in sql_gen so new queries use updated context
                    import core.sql_gen as sql_gen_module
                    import importlib
                    importlib.reload(sql_gen_module)
                    from core.sql_gen import SCHEMA as UPDATED_SCHEMA
                    st.session_state["live_schema"] = UPDATED_SCHEMA
                    st.rerun()
            except Exception as e:
                st.error(f"Sync failed: {e}")

    # Use live schema if synced this session
    display_schema = st.session_state.get("live_schema", SCHEMA)
    with st.expander("View columns", expanded=False):
        for col in display_schema["columns"]:
            st.markdown(f"- `{col['name']}` — {col['description']}")

    st.divider()
    st.markdown("**Sample Questions**")
    sample_q = st.selectbox(
        "Try one:",
        [""] + SCHEMA.get("sample_questions", []),
        label_visibility="collapsed",
    )
    if sample_q:
        st.session_state.sample_q_trigger = sample_q

    st.divider()
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("🛍️ NLP to SQL — Customer Shopping Insights")
st.caption("Ask questions in plain English. Powered by Groq + LangChain + Supabase.")

show_sql = st.toggle("Show generated SQL", value=True)
st.session_state["show_sql"] = show_sql

st.divider()

# ── Render existing chat history ──────────────────────────────────────────────
for i, turn in enumerate(st.session_state.chat_history):
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        render_result(turn, idx=i)

# ── Chat input ────────────────────────────────────────────────────────────────
# Pre-fill from sidebar sample picker
prefill = st.session_state.pop("sample_q_trigger", "") or ""
question = st.chat_input("Ask a question about the shopping data...")

# Allow sidebar sample to trigger a question
if not question and prefill and prefill != st.session_state.get("_last_prefill"):
    question = prefill
    st.session_state["_last_prefill"] = prefill

if question:
    with st.chat_message("user"):
        st.markdown(question)

    # Build history context (exclude df to keep it lightweight)
    history_ctx = [
        {"question": t["question"], "answer": t.get("answer", "")}
        for t in st.session_state.chat_history
    ]

    with st.chat_message("assistant"):
        # Collect UI overrides to pass to LLM
        llm_overrides = {
            "provider":    st.session_state.get("llm_provider", "groq"),
            "model":       st.session_state.get("llm_model"),
            "temperature": st.session_state.get("llm_temperature"),
            "max_tokens":  st.session_state.get("llm_max_tokens"),
            "top_p":       st.session_state.get("llm_top_p"),
        }

        with st.spinner("Generating SQL..."):
            sql, err = generate_sql(question, chat_history=history_ctx, llm_overrides=llm_overrides)

        if err:
            turn = {"question": question, "error": f"🚫 Guardrail: {err}"}
            st.session_state.chat_history.append(turn)
            st.error(turn["error"])
            st.stop()

        with st.spinner("Querying Supabase..."):
            try:
                data = run_query(sql)
            except Exception as e:
                turn = {"question": question, "sql": sql, "error": f"❌ Query failed: {e}"}
                st.session_state.chat_history.append(turn)
                st.error(turn["error"])
                st.stop()

        if not data:
            turn = {"question": question, "sql": sql, "error": "No results returned for this query."}
            st.session_state.chat_history.append(turn)
            st.warning(turn["error"])
            st.stop()

        df = to_dataframe(data)
        row_count = len(df)
        size_class = classify_result_size(row_count)
        if _wants_download(question):
            size_class = "large"  # force download mode

        answer = ""
        if size_class != "large":
            with st.spinner("Generating answer..."):
                answer = generate_answer(question, data, chat_history=history_ctx, llm_overrides=llm_overrides)
        turn = {
            "question": question,
            "sql": sql,
            "answer": answer,
            "row_count": row_count,
            "df": df,
        }
        st.session_state.chat_history.append(turn)
        render_result(turn, idx=len(st.session_state.chat_history) - 1)
