# NLP to SQL — Customer Shopping Insights

Ask questions in plain English, get answers from your Supabase database.

## Stack
- **UI**: Streamlit
- **LLM**: Groq (via LangChain)
- **Database**: Supabase (PostgreSQL)
- **Observability**: LangSmith
- **Guardrails**: LangChain + custom SQL validator

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in your keys in .env
```

### 3. Set up Supabase
- Create a new Supabase project
- Run `supabase_setup.sql` in the Supabase SQL editor
- Upload your CSV data to the `shopping_preferences` table via the Supabase dashboard (Table Editor → Import CSV)

### 4. Configure settings
Edit `config.yaml` to change:
- LLM model and hyperparameters
- Row display/download thresholds
- Guardrail rules

### 5. Run the app
```bash
streamlit run app.py
```

## How it works
1. User types a natural language question
2. LangChain + Groq generates a SQL SELECT query
3. Guardrails validate the SQL (blocks destructive ops)
4. Query runs against Supabase
5. Based on row count:
   - **Small** (≤100 rows): display table + LLM answer
   - **Medium** (101–500 rows): display table + download + stats + LLM answer
   - **Large** (>500 rows): offer CSV/Excel download OR descriptive statistics
6. All traces logged to LangSmith

## CSV Column Mapping
When importing your CSV, ensure column names match exactly:
`customer_id, age, gender, item_purchased, category, purchase_amount_usd, location, size, color, season, review_rating, subscription_status, shipping_type, discount_applied, promo_code_used, previous_purchases, payment_method, frequency_of_purchases`
