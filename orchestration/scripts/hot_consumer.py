"""
Hot table consumer: Kafka 'stock-intraday' → intraday.duckdb

Reads 1-minute bar messages from Kafka and upserts them into the
intraday_bars table in a local DuckDB file on the shared data volume.

On startup, stale data from previous trading days is cleared automatically.
The table resets each calendar day so it only holds the current session.

Requires:
  KAFKA_BOOTSTRAP_SERVERS   — e.g. kafka:9092
  INTRADAY_DUCKDB_PATH      — e.g. /data/intraday.duckdb
"""

import json
import os
from datetime import date, timezone

import duckdb
from kafka import KafkaConsumer

KAFKA_TOPIC = 'stock-intraday'
INTRADAY_DUCKDB_PATH = os.environ.get('INTRADAY_DUCKDB_PATH', '/data/intraday.duckdb')

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS intraday_bars (
    symbol      VARCHAR     NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      BIGINT,
    vwap        DOUBLE,
    trade_count INTEGER,
    PRIMARY KEY (symbol, timestamp)
)
"""

_UPSERT = """
INSERT INTO intraday_bars
    (symbol, timestamp, open, high, low, close, volume, vwap, trade_count)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (symbol, timestamp) DO UPDATE SET
    open        = excluded.open,
    high        = excluded.high,
    low         = excluded.low,
    close       = excluded.close,
    volume      = excluded.volume,
    vwap        = excluded.vwap,
    trade_count = excluded.trade_count
"""


def _setup(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_CREATE_TABLE)
    # Clear any rows from previous trading days
    today = date.today().isoformat()
    deleted = conn.execute(
        "DELETE FROM intraday_bars WHERE timestamp::DATE < ?", [today]
    ).rowcount
    if deleted:
        print(f'Cleared {deleted} stale rows from previous trading day(s)', flush=True)
    count = conn.execute('SELECT count(*) FROM intraday_bars').fetchone()[0]
    print(f'intraday_bars ready — {count} existing bars for today', flush=True)


def main() -> None:
    # Run setup with a short-lived connection
    with duckdb.connect(INTRADAY_DUCKDB_PATH) as conn:
        _setup(conn)

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset='latest',
        group_id='hot-consumer',
    )

    today = date.today()
    print(f'Hot consumer listening on topic "{KAFKA_TOPIC}"…', flush=True)

    for msg in consumer:
        bar = msg.value

        # Open, write, close — releases the lock so the API can read between writes
        with duckdb.connect(INTRADAY_DUCKDB_PATH) as conn:
            # Reset table at day boundary
            current_day = date.today()
            if current_day != today:
                conn.execute('DELETE FROM intraday_bars')
                today = current_day
                print(f'New trading day {today} — intraday table cleared', flush=True)

            conn.execute(_UPSERT, [
                bar['symbol'],
                bar['timestamp'],
                bar.get('open'),
                bar.get('high'),
                bar.get('low'),
                bar.get('close'),
                bar.get('volume'),
                bar.get('vwap'),
                bar.get('trade_count'),
            ])

        print(f'Consumed: {bar["symbol"]} close={bar.get("close")} @ {bar["timestamp"]}', flush=True)


if __name__ == '__main__':
    main()
