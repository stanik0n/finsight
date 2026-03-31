"""
FinSight FastAPI backend — Phase 1.

Endpoints:
  POST /query   — NL question → SQL → results
  GET  /health  — pipeline status + DuckDB freshness
  GET  /schema  — mart_query_context column list (for UI hints)
"""

import os
from datetime import datetime

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


# ── Models ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    results: list[dict]
    path: str          # 'cold' for Phase 1; 'hot' added in Phase 3
    row_count: int


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_duckdb_freshness() -> dict:
    """Return the latest date in mart_query_context, or None if the table doesn't exist."""
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        row = conn.execute(
            "SELECT max(date), count(*) FROM main_gold.mart_query_context"
        ).fetchone()
        conn.close()
        return {'latest_date': str(row[0]) if row[0] else None, 'row_count': row[1]}
    except Exception as e:
        return {'latest_date': None, 'row_count': 0, 'error': str(e)}


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post('/query', response_model=QueryResponse)
async def run_query(req: QueryRequest):
    """
    Translate a natural language question to SQL, execute against Gold DuckDB,
    and return the results.

    Requires GROQ_API_KEY to be set. Get a free key at console.groq.com.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail='Question cannot be empty')

    try:
        freshness = _get_duckdb_freshness()
        latest_date = freshness.get('latest_date')
        result = nl_query(req.question, DUCKDB_PATH, latest_date=latest_date)
    except RuntimeError as e:
        # GROQ_API_KEY missing or connection error
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        # SQL parsing failed
        raise HTTPException(status_code=422, detail=str(e))
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=f'SQL execution error: {e}')

    return QueryResponse(
        question=result['question'],
        sql=result['sql'],
        results=result['results'],
        path=result['path'],
        row_count=len(result['results']),
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
    """Return the mart_query_context DDL for the UI's schema hint panel."""
    return {'ddl': MART_QUERY_CONTEXT_DDL}
