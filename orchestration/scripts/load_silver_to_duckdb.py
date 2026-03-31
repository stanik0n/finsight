"""
Loads the Silver Iceberg table from MinIO into the DuckDB file (silver.stock_metrics).
This runs after spark_transform and before dbt_run.
"""

import os
import sys
from datetime import date, timedelta

import duckdb
from pyiceberg.catalog.sql import SqlCatalog


def get_catalog() -> SqlCatalog:
    duckdb_path = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')
    catalog_db = duckdb_path.replace('finsight.duckdb', 'iceberg_catalog.db')
    return SqlCatalog(
        'finsight',
        **{
            'uri': f'sqlite:////{catalog_db}',
            'warehouse': f's3://{os.environ.get("S3_BUCKET", "finsight")}/warehouse',
            's3.endpoint': os.environ['MINIO_ENDPOINT'],
            's3.access-key-id': os.environ['MINIO_ACCESS_KEY'],
            's3.secret-access-key': os.environ['MINIO_SECRET_KEY'],
        }
    )


def load(target_date: date) -> None:
    duckdb_path = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')
    catalog = get_catalog()

    try:
        catalog.load_table('silver.stock_metrics')
    except Exception:
        raise RuntimeError("[load_silver] Silver Iceberg table does not exist - run spark_transform first")

    table = catalog.load_table('silver.stock_metrics')
    arrow_df = table.scan(row_filter=f"date = '{target_date}'").to_arrow()

    if len(arrow_df) == 0:
        raise RuntimeError(f"[load_silver] No Silver rows for {target_date}")

    conn = duckdb.connect(duckdb_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS silver")

    existing_tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'silver'"
    ).fetchall()
    table_names = [r[0] for r in existing_tables]

    if 'stock_metrics' in table_names:
        conn.execute(f"DELETE FROM silver.stock_metrics WHERE date = '{target_date}'")
        conn.register('_silver_arrow', arrow_df)
        conn.execute("INSERT INTO silver.stock_metrics SELECT * FROM _silver_arrow")
    else:
        conn.register('_silver_arrow', arrow_df)
        conn.execute("CREATE TABLE silver.stock_metrics AS SELECT * FROM _silver_arrow")

    conn.unregister('_silver_arrow')
    count = conn.execute(f"SELECT COUNT(*) FROM silver.stock_metrics WHERE date = '{target_date}'").fetchone()[0]
    conn.close()

    print(f"[load_silver] Loaded {count} rows into DuckDB silver.stock_metrics for {target_date}")


if __name__ == '__main__':
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today() - timedelta(days=1)
    load(target)
