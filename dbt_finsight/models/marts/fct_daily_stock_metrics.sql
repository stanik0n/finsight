-- Gold fact table: one row per ticker per trading day.
-- This is the primary analytical table queried by mart_query_context.

select
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume,
    vwap,
    sma_20,
    sma_50,
    rsi_14,
    volume_zscore,
    vwap_deviation,
    pct_change,
    ingested_at

from {{ ref('stg_stock_metrics') }}
