"""
Streaming producer: Alpaca WebSocket (StockDataStream) → Kafka topic 'stock-intraday'.

Subscribes to 1-minute bars for all 50 tickers and publishes each bar as a JSON
message to Kafka. Runs indefinitely; restart policy handles reconnects.

Requires:
  ALPACA_API_KEY, ALPACA_SECRET_KEY  — Alpaca credentials
  KAFKA_BOOTSTRAP_SERVERS            — e.g. kafka:9092
"""

import json
import os
import sys

import yaml
from alpaca.data.live import StockDataStream
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

KAFKA_TOPIC = 'stock-intraday'


def load_tickers() -> list[str]:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tickers.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return [ticker for sector in config['sectors'].values() for ticker in sector]


def make_producer() -> KafkaProducer:
    servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    return KafkaProducer(
        bootstrap_servers=servers,
        value_serializer=lambda v: json.dumps(v, default=str).encode(),
        acks='all',
        retries=5,
    )


def main() -> None:
    api_key = os.environ.get('ALPACA_API_KEY', '')
    secret_key = os.environ.get('ALPACA_SECRET_KEY', '')
    if not api_key or not secret_key:
        print('ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set', flush=True)
        sys.exit(1)

    try:
        producer = make_producer()
    except NoBrokersAvailable:
        print('ERROR: Cannot reach Kafka brokers. Is Kafka running?', flush=True)
        sys.exit(1)

    tickers = load_tickers()
    print(f'Starting stream for {len(tickers)} tickers → topic "{KAFKA_TOPIC}"', flush=True)

    stream = StockDataStream(api_key=api_key, secret_key=secret_key)

    async def bar_handler(bar) -> None:
        msg = {
            'symbol': bar.symbol,
            'timestamp': bar.timestamp.isoformat(),
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': int(bar.volume),
            'vwap': float(bar.vwap) if bar.vwap is not None else None,
            'trade_count': int(bar.trade_count) if bar.trade_count is not None else None,
        }
        producer.send(KAFKA_TOPIC, msg)
        producer.flush()
        print(f'Published: {bar.symbol} close={bar.close} @ {bar.timestamp}', flush=True)

    stream.subscribe_bars(bar_handler, *tickers)
    stream.run()


if __name__ == '__main__':
    main()
