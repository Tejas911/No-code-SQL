-- ============================================================
-- 1. Create the shopping_preferences table
-- ============================================================
CREATE TABLE IF NOT EXISTS shopping_preferences (
    customer_id           INTEGER PRIMARY KEY,
    age                   INTEGER,
    gender                TEXT,
    item_purchased        TEXT,
    category              TEXT,
    purchase_amount_usd   NUMERIC(10, 2),
    location              TEXT,
    size                  TEXT,
    color                 TEXT,
    season                TEXT,
    review_rating         NUMERIC(3, 1),
    subscription_status   TEXT,
    shipping_type         TEXT,
    discount_applied      TEXT,
    promo_code_used       TEXT,
    previous_purchases    INTEGER,
    payment_method            TEXT,
    preferred_payment_method  TEXT,
    frequency_of_purchases    TEXT
);

-- ============================================================
-- 2. Create a secure RPC function to execute dynamic SQL
--    This is required by the app to run generated SELECT queries.
--    SECURITY: Only allows SELECT statements (enforced in app guardrails too).
-- ============================================================
CREATE OR REPLACE FUNCTION execute_sql(query TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
    trimmed TEXT := upper(trim(query));
BEGIN
    -- Allow plain SELECT and CTEs (WITH ... SELECT)
    IF trimmed NOT LIKE 'SELECT%' AND trimmed NOT LIKE 'WITH%' THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;

    EXECUTE 'SELECT jsonb_agg(row_to_json(t)) FROM (' || query || ') t'
    INTO result;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$;

-- Grant execute to anon and authenticated roles
GRANT EXECUTE ON FUNCTION execute_sql(TEXT) TO anon, authenticated;

-- ============================================================
-- 3. (Optional) Enable Row Level Security
-- ============================================================
-- ALTER TABLE shopping_preferences ENABLE ROW LEVEL SECURITY;

-- Allow read-only access to all
-- CREATE POLICY "Allow read access" ON shopping_preferences
--     FOR SELECT USING (true);
