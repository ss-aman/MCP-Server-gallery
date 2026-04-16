"""
07 - Data Analysis MCP Server
================================
Exposes pandas + numpy-powered data analysis as MCP tools.
The server keeps a small in-memory "session store" of loaded DataFrames so
multiple tool calls in the same conversation can work on the same dataset.

Demonstrates:
  - Session state inside an MCP server (in-memory dict)
  - Returning structured analysis results
  - Pandas + NumPy integration
  - CSV loading from a path OR from inline text content
  - Statistical summaries, filtering, sorting, group-by, correlation

Tech stack: mcp[cli], pandas, numpy
Transport:  stdio

Run:
    pip install mcp[cli] pandas numpy
    mcp dev server.py
"""

import io
import json
from typing import Any

import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("data-analysis")

# In-memory store: dataset_name → pd.DataFrame
_store: dict[str, pd.DataFrame] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_df(name: str) -> pd.DataFrame:
    if name not in _store:
        raise KeyError(f"Dataset '{name}' not found. Load it first with load_csv or load_inline.")
    return _store[name]


def _df_to_records(df: pd.DataFrame, max_rows: int = 100) -> list[dict]:
    """Convert a DataFrame to a JSON-serialisable list of dicts."""
    truncated = df.head(max_rows)
    return json.loads(truncated.to_json(orient="records", date_format="iso"))


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="number").columns.tolist()


# ---------------------------------------------------------------------------
# Tools — loading data
# ---------------------------------------------------------------------------

@mcp.tool()
def load_csv(path: str, name: str = "df", sep: str = ",") -> dict:
    """
    Load a CSV file from disk into the session store.

    Args:
        path: Absolute or relative path to the CSV file.
        name: Session name to assign to this dataset (default 'df').
        sep:  Column separator character (default ',').
    """
    df = pd.read_csv(path, sep=sep)
    _store[name] = df
    return {
        "dataset": name,
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


@mcp.tool()
def load_inline(csv_text: str, name: str = "df", sep: str = ",") -> dict:
    """
    Load CSV data supplied as inline text.

    Args:
        csv_text: Raw CSV content (header + rows).
        name:     Session name for the dataset (default 'df').
        sep:      Column separator character (default ',').
    """
    df = pd.read_csv(io.StringIO(csv_text), sep=sep)
    _store[name] = df
    return {
        "dataset": name,
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


@mcp.tool()
def list_datasets() -> list[str]:
    """List all datasets currently loaded in the session."""
    return list(_store.keys())


@mcp.tool()
def drop_dataset(name: str) -> str:
    """Remove a dataset from the session store."""
    if name not in _store:
        raise KeyError(f"Dataset '{name}' not found.")
    del _store[name]
    return f"Dataset '{name}' removed."


# ---------------------------------------------------------------------------
# Tools — exploration
# ---------------------------------------------------------------------------

@mcp.tool()
def head(name: str = "df", rows: int = 10) -> list[dict]:
    """Return the first N rows of a dataset."""
    return _df_to_records(_get_df(name).head(rows))


@mcp.tool()
def tail(name: str = "df", rows: int = 10) -> list[dict]:
    """Return the last N rows of a dataset."""
    return _df_to_records(_get_df(name).tail(rows))


@mcp.tool()
def schema(name: str = "df") -> dict:
    """
    Return column names, data types, and null counts for a dataset.
    """
    df = _get_df(name)
    return {
        "dataset": name,
        "rows": len(df),
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "unique_count": int(df[col].nunique()),
            }
            for col in df.columns
        ],
    }


# ---------------------------------------------------------------------------
# Tools — statistics
# ---------------------------------------------------------------------------

@mcp.tool()
def describe(name: str = "df", include_all: bool = False) -> dict:
    """
    Generate descriptive statistics (count, mean, std, min, quartiles, max).

    Args:
        name:        Dataset name.
        include_all: Include non-numeric columns (default False).
    """
    df = _get_df(name)
    kwargs: dict[str, Any] = {"include": "all"} if include_all else {}
    desc = df.describe(**kwargs)
    return json.loads(desc.to_json())


@mcp.tool()
def correlation(name: str = "df", method: str = "pearson") -> dict:
    """
    Compute pairwise correlation between numeric columns.

    Args:
        name:   Dataset name.
        method: 'pearson' (default), 'spearman', or 'kendall'.
    """
    df = _get_df(name)
    corr = df[_numeric_cols(df)].corr(method=method)
    return json.loads(corr.to_json())


@mcp.tool()
def value_counts(name: str = "df", column: str = "") -> dict:
    """
    Count unique values in a column.

    Args:
        name:   Dataset name.
        column: Column to count.
    """
    df = _get_df(name)
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not in dataset. Available: {list(df.columns)}")
    counts = df[column].value_counts()
    return {"column": column, "counts": counts.to_dict()}


# ---------------------------------------------------------------------------
# Tools — transformation / querying
# ---------------------------------------------------------------------------

@mcp.tool()
def filter_rows(
    name: str = "df",
    column: str = "",
    operator: str = "==",
    value: Any = None,
    result_name: str | None = None,
) -> dict:
    """
    Filter rows by a simple column condition and optionally save as a new dataset.

    Args:
        name:        Source dataset.
        column:      Column to filter on.
        operator:    One of: ==, !=, >, >=, <, <=, contains, startswith, endswith.
        value:       Value to compare against.
        result_name: If given, save the filtered result under this name.
    """
    df = _get_df(name)
    col = df[column]

    match operator:
        case "==":   mask = col == value
        case "!=":   mask = col != value
        case ">":    mask = col > value
        case ">=":   mask = col >= value
        case "<":    mask = col < value
        case "<=":   mask = col <= value
        case "contains":    mask = col.astype(str).str.contains(str(value), na=False)
        case "startswith":  mask = col.astype(str).str.startswith(str(value))
        case "endswith":    mask = col.astype(str).str.endswith(str(value))
        case _:
            raise ValueError(f"Unknown operator '{operator}'.")

    result = df[mask]
    if result_name:
        _store[result_name] = result

    return {
        "matched_rows": len(result),
        "total_rows": len(df),
        "preview": _df_to_records(result, 20),
    }


@mcp.tool()
def sort_by(
    name: str = "df",
    columns: list[str] = None,
    ascending: bool = True,
    result_name: str | None = None,
) -> list[dict]:
    """
    Sort a dataset by one or more columns.

    Args:
        name:        Dataset name.
        columns:     Columns to sort by (in order).
        ascending:   Sort ascending (default True).
        result_name: Save sorted result under this name.
    """
    df = _get_df(name)
    sorted_df = df.sort_values(by=columns or df.columns.tolist(), ascending=ascending)
    if result_name:
        _store[result_name] = sorted_df
    return _df_to_records(sorted_df)


@mcp.tool()
def group_and_aggregate(
    name: str = "df",
    group_by: list[str] = None,
    agg: dict[str, str] = None,
    result_name: str | None = None,
) -> list[dict]:
    """
    Group rows and aggregate numeric columns.

    Args:
        name:        Dataset name.
        group_by:    Columns to group by.
        agg:         Dict of {column: agg_func} — e.g. {"sales": "sum", "age": "mean"}.
                     Supported: sum, mean, min, max, count, std, median, first, last.
        result_name: Save result under this name.
    """
    df = _get_df(name)
    result = df.groupby(group_by or []).agg(agg or {}).reset_index()
    if result_name:
        _store[result_name] = result
    return _df_to_records(result)


@mcp.tool()
def select_columns(
    name: str = "df",
    columns: list[str] = None,
    result_name: str | None = None,
) -> list[dict]:
    """
    Select a subset of columns from a dataset.

    Args:
        name:        Dataset name.
        columns:     Columns to keep.
        result_name: Save result under this name.
    """
    df = _get_df(name)
    result = df[columns or df.columns.tolist()]
    if result_name:
        _store[result_name] = result
    return _df_to_records(result)


@mcp.tool()
def numeric_summary(name: str = "df") -> dict:
    """
    Return richer stats for numeric columns: mean, median, std, skew, kurtosis, IQR.
    """
    df = _get_df(name)
    num = df[_numeric_cols(df)]
    summary = {}
    for col in num.columns:
        s = num[col].dropna()
        q1, q3 = float(np.percentile(s, 25)), float(np.percentile(s, 75))
        summary[col] = {
            "count": int(s.count()),
            "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std": round(float(s.std()), 4),
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(q3 - q1, 4),
            "skew": round(float(s.skew()), 4),
            "kurtosis": round(float(s.kurtosis()), 4),
            "null_count": int(num[col].isna().sum()),
        }
    return summary


if __name__ == "__main__":
    mcp.run()
