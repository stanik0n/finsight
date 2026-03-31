"""
Detect anomalies in the Gold DuckDB table for a given trading date — Phase 2.

Writes a JSON file to /data/anomalies_{date}.json containing any rows where
is_oversold, is_overbought, is_volume_spike, or is_large_move is true.

Usage:
    python orchestration/scripts/detect_anomalies.py 2025-03-28
"""

import json
import os
import sys
from pathlib import Path

import duckdb

DUCKDB_PATH = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')


def detect(ds: str) -> list[dict]:
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        rows = conn.execute("""
            SELECT symbol, company_name, sector, date,
                   close, pct_change, rsi_14, volume_zscore,
                   is_oversold, is_overbought, is_volume_spike, is_large_move
            FROM main_gold.mart_query_context
            WHERE date = ?
              AND (is_oversold OR is_overbought OR is_volume_spike OR is_large_move)
            ORDER BY symbol
        """, [ds]).fetchall()
    finally:
        conn.close()

    columns = [
        'symbol', 'company_name', 'sector', 'date',
        'close', 'pct_change', 'rsi_14', 'volume_zscore',
        'is_oversold', 'is_overbought', 'is_volume_spike', 'is_large_move',
    ]
    return [dict(zip(columns, row)) for row in rows]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: detect_anomalies.py <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(1)

    ds = sys.argv[1]
    anomalies = detect(ds)

    out_path = Path(f'/data/anomalies_{ds}.json')
    out_path.write_text(json.dumps({'date': ds, 'anomalies': anomalies}, default=str))

    print(f"[detect_anomalies] {ds}: {len(anomalies)} anomalies written to {out_path}")


if __name__ == '__main__':
    main()
