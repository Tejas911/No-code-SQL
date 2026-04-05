import io
import pandas as pd
from core.config_loader import load_config


def get_thresholds() -> tuple[int, int]:
    cfg = load_config()["data"]
    return cfg["max_display_rows"], cfg["large_data_threshold"]


def to_dataframe(data: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_descriptive_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns descriptive statistics for numeric and categorical columns."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_stats = df[numeric_cols].describe().T if numeric_cols else pd.DataFrame()

    cat_cols = df.select_dtypes(include="object").columns.tolist()
    cat_stats = []
    for col in cat_cols:
        vc = df[col].value_counts()
        cat_stats.append({
            "column": col,
            "unique_values": df[col].nunique(),
            "top_value": vc.index[0] if len(vc) > 0 else None,
            "top_count": int(vc.iloc[0]) if len(vc) > 0 else 0,
            "null_count": int(df[col].isna().sum()),
        })

    return numeric_stats, pd.DataFrame(cat_stats)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return buf.getvalue()


def classify_result_size(row_count: int) -> str:
    """
    Returns: 'small' | 'medium' | 'large'
    small  → display inline
    medium → display inline + offer download
    large  → too large, offer download or stats
    """
    _, large_threshold = get_thresholds()
    max_display, _ = get_thresholds()

    if row_count <= max_display:
        return "small"
    elif row_count <= large_threshold:
        return "medium"
    else:
        return "large"
