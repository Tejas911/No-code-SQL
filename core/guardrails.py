import re
from core.config_loader import load_config


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validates generated SQL against guardrail rules.
    Returns (is_valid, error_message).
    """
    cfg = load_config()["guardrails"]

    if len(sql) > cfg["max_query_length"]:
        return False, f"Query exceeds max allowed length of {cfg['max_query_length']} characters."

    if cfg["block_destructive_queries"]:
        destructive = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]
        sql_upper = sql.upper()
        for keyword in destructive:
            # Use word boundary to avoid false positives
            if re.search(rf"\b{keyword}\b", sql_upper):
                return False, f"Destructive operation '{keyword}' is not allowed. Only SELECT queries are permitted."

    allowed_ops = [op.upper() for op in cfg["allowed_operations"]]
    stripped = sql.strip().upper()
    # Allow CTEs (WITH ... SELECT) in addition to plain SELECT
    if not any(stripped.startswith(op) for op in allowed_ops) and not stripped.startswith("WITH"):
        return False, f"Only {allowed_ops} operations are allowed."

    return True, ""
