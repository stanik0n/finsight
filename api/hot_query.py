"""
Hot path: NL question → SQL → intraday.duckdb

Uses a separate schema context describing the intraday_bars table
(1-minute bars for the current trading session) instead of the Gold
mart_query_context used by the cold path.
"""

import os
import re

import duckdb
from groq import Groq

GROQ_MODEL = 'llama-3.3-70b-versatile'
INTRADAY_DUCKDB_PATH = os.environ.get('INTRADAY_DUCKDB_PATH', '/data/intraday.duckdb')

_INTRADAY_DDL = """
Table: intraday_bars

Columns:
  symbol      VARCHAR     -- Ticker symbol, e.g. 'AAPL', 'NVDA'
  timestamp   TIMESTAMPTZ -- 1-minute bar timestamp (UTC); current trading session only
  open        DOUBLE      -- Bar open price
  high        DOUBLE      -- Bar intraday high
  low         DOUBLE      -- Bar intraday low
  close       DOUBLE      -- Bar close (last trade price in the minute)
  volume      BIGINT      -- Shares traded in this 1-minute bar
  vwap        DOUBLE      -- Volume-weighted average price for the bar
  trade_count INTEGER     -- Number of individual trades in the bar

Data: real-time 1-minute bars for 50 US equities, current session only.
All timestamps are UTC. Market hours are 14:30–21:00 UTC (09:30–16:00 ET).
""".strip()

_HOT_SYSTEM_PROMPT = f"""
You are a financial data analyst assistant. You generate DuckDB-compatible SQL queries
against a real-time intraday market data table, then summarise results in plain English.

{_INTRADAY_DDL}

Rules:
- Generate valid DuckDB SQL only.
- Always query the table: intraday_bars
- Return only the SQL inside a ```sql ... ``` block — nothing before or after.
- For recent data use: WHERE timestamp >= now() - INTERVAL '1 hour'
- Use ORDER BY timestamp DESC and LIMIT 50 unless the user specifies otherwise.
- Do not explain the SQL — only output the SQL block.
""".strip()

_FORBIDDEN = re.compile(
    r'\b(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|TRUNCATE|ATTACH|COPY|EXPORT)\b',
    re.IGNORECASE,
)


def _extract_sql(text: str) -> str:
    match = re.search(r'```sql\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    text = text.strip()
    if text.upper().startswith(('SELECT', 'WITH')):
        return text
    raise ValueError(f'No SQL block found in LLM response:\n{text}')


def hot_query(question: str) -> dict:
    """
    Full hot-path pipeline: question → SQL (intraday schema) → execute → results.

    Returns the same shape as qwen_agent.query() with path='hot'.
    """
    groq_key = os.environ.get('GROQ_API_KEY', '')
    if not groq_key:
        raise RuntimeError('GROQ_API_KEY is not set.')

    client = Groq(api_key=groq_key)
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': _HOT_SYSTEM_PROMPT},
            {'role': 'user',   'content': question},
        ],
        temperature=0.1,
        max_tokens=400,
    )

    sql = _extract_sql(completion.choices[0].message.content)

    if _FORBIDDEN.search(sql):
        kw = _FORBIDDEN.search(sql).group(0).upper()
        raise ValueError(f'Generated SQL contains forbidden keyword: {kw}')

    conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
    finally:
        conn.close()

    return {
        'question': question,
        'sql': sql,
        'results': [dict(zip(columns, row)) for row in rows],
        'path': 'hot',
    }
