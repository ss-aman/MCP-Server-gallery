# 07 · Data Analysis MCP Server

A **pandas + numpy** powered server for exploring and analysing tabular data. Keeps loaded datasets in session memory so multiple tools can work on the same DataFrame across a conversation.

## What it shows

| Concept | Detail |
|---------|--------|
| **Library** | `FastMCP` + `pandas` + `numpy` |
| **Transport** | stdio |
| **Primitives** | Tools |
| **Key pattern** | In-memory session state, structured results, data pipeline chaining |

## Tools

### Loading data

| Tool | Description |
|------|-------------|
| `load_csv` | Load a CSV file from disk |
| `load_inline` | Load CSV from inline text |
| `list_datasets` | List loaded datasets |
| `drop_dataset` | Remove a dataset from memory |

### Exploration

| Tool | Description |
|------|-------------|
| `head` | First N rows |
| `tail` | Last N rows |
| `schema` | Column types, null counts, unique counts |

### Statistics

| Tool | Description |
|------|-------------|
| `describe` | Count / mean / std / min / max / quartiles |
| `numeric_summary` | Adds skew, kurtosis, IQR |
| `correlation` | Pairwise correlation matrix |
| `value_counts` | Frequency count for a column |

### Transformation

| Tool | Description |
|------|-------------|
| `filter_rows` | Filter by column condition (`==`, `>`, `contains`, …) |
| `sort_by` | Sort by column(s) |
| `group_and_aggregate` | Group-by + agg (`sum`, `mean`, `count`, …) |
| `select_columns` | Project to a column subset |

## Quick start

```bash
pip install -r requirements.txt
mcp dev server.py
```

A `sample.csv` is included. Example prompts once connected:

```
Load sample.csv and name it 'employees'.
What is the average salary by department?
Filter to Engineering employees with salary > 100000.
Show the correlation between salary, age, and performance_score.
```

## Example pipeline

```
load_csv("sample.csv", name="employees")
  → group_and_aggregate(group_by=["department"], agg={"salary":"mean","age":"mean"})
  → sort_by(columns=["salary"], ascending=False)
```
