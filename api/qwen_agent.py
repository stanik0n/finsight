"""
Qwen2.5-7B-Instruct via Groq API — Phase 1 Role: Text-to-SQL.

Sends the user's natural language question to Qwen with a system prompt containing
the full DDL of mart_query_context, parses the generated SQL, executes it against
DuckDB, and returns the SQL + results.

Set GROQ_API_KEY in your environment. Get a free key at console.groq.com.
"""

import os
import re
from typing import Optional

import duckdb

from schema_context import SYSTEM_PROMPT

GROQ_MODEL = 'llama-3.3-70b-versatile'  # Groq model for text-to-SQL


def _extract_sql(text: str) -> Optional[str]:
    """Parse SQL from a ```sql ... ``` block in the LLM response."""
    match = re.search(r'```sql\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: if the response starts with SELECT/WITH directly
    text = text.strip()
    if text.upper().startswith(('SELECT', 'WITH')):
        return text
    return None


def generate_sql(question: str) -> str:
    """Call Groq API with Qwen2.5 to generate SQL for the given question."""
    groq_key = os.environ.get('GROQ_API_KEY', '')
    if not groq_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at console.groq.com and add it to your .env file."
        )

    from groq import Groq
    client = Groq(api_key=groq_key)

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user',   'content': question},
        ],
        temperature=0.1,
        max_tokens=512,
    )

    raw = completion.choices[0].message.content
    sql = _extract_sql(raw)

    if not sql:
        raise ValueError(f"Could not parse SQL from LLM response:\n{raw}")

    return sql


_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|TRUNCATE|ATTACH|COPY|EXPORT)\b',
    re.IGNORECASE,
)
_ALLOWED_SCHEMAS = re.compile(r'\b(?:main_silver|main_bronze|silver|bronze)\b', re.IGNORECASE)


def _validate_sql(sql: str) -> None:
    """Reject SQL that contains write/DDL operations or references non-gold schemas."""
    if _FORBIDDEN_KEYWORDS.search(sql):
        keyword = _FORBIDDEN_KEYWORDS.search(sql).group(0).upper()
        raise ValueError(f"Generated SQL contains forbidden keyword: {keyword}")
    if _ALLOWED_SCHEMAS.search(sql):
        schema = _ALLOWED_SCHEMAS.search(sql).group(0).lower()
        raise ValueError(f"Generated SQL references non-gold schema: {schema}")


def execute_sql(sql: str, duckdb_path: str) -> list[dict]:
    """Execute the SQL against DuckDB and return rows as a list of dicts."""
    _validate_sql(sql)
    conn = duckdb.connect(duckdb_path, read_only=True)
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def query(question: str, duckdb_path: str, latest_date: str | None = None) -> dict:
    """
    Full pipeline: question → SQL → execute → return results.

    Returns:
        {
            "question": str,
            "sql": str,
            "results": list[dict],
            "path": "cold",
        }
    """
    date_hint = f"\n\nIMPORTANT: The latest available date in the database is {latest_date}. Use this as your reference for 'today', 'yesterday', 'last week', etc." if latest_date else ""
    sql = generate_sql(question + date_hint)
    results = execute_sql(sql, duckdb_path)

    return {
        'question': question,
        'sql': sql,
        'results': results,
        'path': 'cold',
    }
