import os
import json
import httpx
from supabase import create_client, Client
from core.logger import get_logger

log = get_logger("supabase")
_client: Client = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        log.info("Initialising Supabase client → %s", url)
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def run_query(sql: str) -> list[dict]:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_KEY"]

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    log.info("Executing SQL:\n%s", sql)

    response = httpx.post(
        f"{url}/rest/v1/rpc/execute_sql",
        headers=headers,
        json={"query": sql},
        timeout=30,
    )

    log.debug("Supabase response status: %s", response.status_code)

    if response.status_code == 404:
        raise Exception(
            "RPC function 'execute_sql' not found. Run supabase_setup.sql first."
        )
    if response.status_code != 200:
        log.error("Supabase error %s: %s", response.status_code, response.text)
        raise Exception(f"Supabase error {response.status_code}: {response.text}")

    data = response.json()
    row_count = len(data) if isinstance(data, list) else 1
    log.info("Query returned %d rows", row_count)

    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, str):
        parsed = json.loads(data)
        return parsed if isinstance(parsed, list) else [parsed]
    return []


def fetch_live_columns(table_name: str) -> list[dict]:
    """
    Fetch current columns from Supabase information_schema.
    Returns list of {name, type} dicts.
    """
    sql = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """
    rows = run_query(sql)
    log.info("Fetched %d columns from Supabase for table '%s'", len(rows), table_name)
    return [{"name": r["column_name"], "type": r["data_type"]} for r in rows]
