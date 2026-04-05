import json
import os
from core.supabase_client import fetch_live_columns
from core.config_loader import load_config
from core.logger import get_logger

log = get_logger("schema_sync")

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "context", "schema.json")

# Postgres type → friendly type label
_TYPE_MAP = {
    "integer": "integer",
    "bigint": "integer",
    "smallint": "integer",
    "numeric": "numeric",
    "real": "numeric",
    "double precision": "numeric",
    "character varying": "text",
    "text": "text",
    "boolean": "text",
    "date": "text",
    "timestamp without time zone": "text",
    "timestamp with time zone": "text",
}


def _load_schema() -> dict:
    with open(_SCHEMA_PATH, "r") as f:
        return json.load(f)


def _save_schema(schema: dict):
    with open(_SCHEMA_PATH, "w") as f:
        json.dump(schema, f, indent=2)


def sync_schema() -> dict:
    """
    Compare live Supabase columns against schema.json.
    Updates schema.json if columns have changed.

    Returns:
        {
            "added":   [col_name, ...],
            "removed": [col_name, ...],
            "changed": [col_name, ...],   # type changed
            "unchanged": bool,
            "schema":  <updated schema dict>
        }
    """
    cfg = load_config()
    table = cfg["supabase"]["table_name"]

    live_cols = fetch_live_columns(table)
    schema = _load_schema()

    existing = {c["name"]: c for c in schema["columns"]}
    live_map  = {c["name"]: _TYPE_MAP.get(c["type"], "text") for c in live_cols}

    added   = [n for n in live_map if n not in existing]
    removed = [n for n in existing if n not in live_map]
    changed = [
        n for n in live_map
        if n in existing and existing[n]["type"] != live_map[n]
    ]

    if not added and not removed and not changed:
        log.info("Schema in sync — no changes detected")
        return {"added": [], "removed": [], "changed": [], "unchanged": True, "schema": schema}

    log.info("Schema drift detected — added=%s removed=%s changed=%s", added, removed, changed)

    # Rebuild columns list: keep existing descriptions, add new cols, drop removed
    updated_cols = []
    for col in schema["columns"]:
        if col["name"] in removed:
            continue
        if col["name"] in changed:
            col = {**col, "type": live_map[col["name"]]}
        updated_cols.append(col)

    for name in added:
        updated_cols.append({
            "name": name,
            "type": live_map[name],
            "description": f"{name.replace('_', ' ').title()} (auto-synced)"
        })

    schema["columns"] = updated_cols
    _save_schema(schema)
    log.info("schema.json updated successfully")

    return {"added": added, "removed": removed, "changed": changed, "unchanged": False, "schema": schema}
