"""
FinSight FastAPI backend — Phase 3.

Endpoints:
  POST /query         — NL question → SQL → results + analyst commentary
                        Routes to hot (intraday.duckdb) or cold (Gold DuckDB) based on intent
  GET  /health        — pipeline status + DuckDB freshness
  GET  /schema        — mart_query_context column list (for UI hints)
  GET  /anomalies     — latest-date anomaly signals from the gold table
  GET  /stream-status — live intraday stream health (bar count, latest timestamp)
"""

import os
from datetime import datetime

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from commentary import generate_commentary
from hot_query import hot_query
from qwen_agent import query as nl_query
from schema_context import MART_QUERY_CONTEXT_DDL

app = FastAPI(
    title='FinSight API',
    description='Natural Language Analytics Engine for Market Data',
    version='1.0.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],   # tighten in production
    allow_methods=['*'],
    allow_headers=['*'],
)

DUCKDB_PATH = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')
INTRADAY_DUCKDB_PATH = os.environ.get('INTRADAY_DUCKDB_PATH', '/data/intraday.duckdb')

# Keywords that signal the user wants live intraday data (hot path)
_HOT_KEYWORDS = frozenset([
    'intraday', 'live', 'real-time', 'realtime', 'streaming',
    'current price', 'right now', 'premarket', 'pre-market',
    'after hours', 'afterhours', 'after-hours', 'this morning',
    'latest price', 'trading now',
])


# ── Models ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    results: list[dict]
    path: str               # 'cold' (Gold DuckDB) or 'hot' (intraday.duckdb)
    row_count: int
    commentary: str = ''    # analyst summary — Phase 2


# ── Helpers ─────────────────────────────────────────────────────────────────

def _is_hot_query(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _HOT_KEYWORDS)


def _get_duckdb_freshness() -> dict:
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        row = conn.execute(
            "SELECT max(date), count(*) FROM main_gold.mart_query_context"
        ).fetchone()
        conn.close()
        return {'latest_date': str(row[0]) if row[0] else None, 'row_count': row[1]}
    except Exception as e:
        return {'latest_date': None, 'row_count': 0, 'error': str(e)}


def _get_intraday_status() -> dict:
    try:
        conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
        row = conn.execute(
            "SELECT count(*), max(timestamp) FROM intraday_bars"
        ).fetchone()
        conn.close()
        bar_count = row[0] or 0
        return {
            'live': bar_count > 0,
            'bar_count': bar_count,
            'latest_bar': str(row[1]) if row[1] else None,
        }
    except Exception as e:
        return {'live': False, 'bar_count': 0, 'latest_bar': None, 'error': str(e)}


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post('/query', response_model=QueryResponse)
async def run_query(req: QueryRequest):
    """
    Translate a natural language question to SQL and execute it.

    Routes to the hot path (intraday.duckdb) when the question contains
    live/intraday keywords; otherwise routes to the cold path (Gold DuckDB).
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail='Question cannot be empty')

    use_hot = _is_hot_query(req.question)

    try:
        if use_hot:
            result = hot_query(req.question)
        else:
            freshness = _get_duckdb_freshness()
            latest_date = freshness.get('latest_date')
            result = nl_query(req.question, DUCKDB_PATH, latest_date=latest_date)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=f'SQL execution error: {e}')

    commentary = generate_commentary(result['question'], result['results'])

    return QueryResponse(
        question=result['question'],
        sql=result['sql'],
        results=result['results'],
        path=result['path'],
        row_count=len(result['results']),
        commentary=commentary,
    )


@app.get('/health')
async def health():
    freshness = _get_duckdb_freshness()
    groq_configured = bool(os.environ.get('GROQ_API_KEY'))
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'duckdb_path': DUCKDB_PATH,
        'data': freshness,
        'groq_configured': groq_configured,
    }


@app.get('/schema')
async def schema():
    return {'ddl': MART_QUERY_CONTEXT_DDL}


@app.get('/anomalies')
async def anomalies():
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        rows = conn.execute("""
            SELECT symbol, company_name, sector, date,
                   close, pct_change, rsi_14, volume_zscore,
                   is_oversold, is_overbought, is_volume_spike, is_large_move
            FROM main_gold.mart_query_context
            WHERE date = (SELECT max(date) FROM main_gold.mart_query_context)
              AND (is_oversold OR is_overbought OR is_volume_spike OR is_large_move)
            ORDER BY symbol
        """).fetchall()
        conn.close()
        if not rows:
            return {'date': None, 'anomalies': []}
        columns = [
            'symbol', 'company_name', 'sector', 'date',
            'close', 'pct_change', 'rsi_14', 'volume_zscore',
            'is_oversold', 'is_overbought', 'is_volume_spike', 'is_large_move',
        ]
        result = [dict(zip(columns, row)) for row in rows]
        return {'date': str(result[0]['date']), 'anomalies': result}
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/stream-status')
async def stream_status():
    """Return live intraday stream health: bar count and latest bar timestamp."""
    return _get_intraday_status()
