-- Staging model: light cleaning on Silver stock_metrics.
-- Drops rows with null close or zero volume (data quality guard before Gold).

select
    symbol,
    cast(date as date)          as date,
    cast(open   as double)      as open,
    cast(high   as double)      as high,
    cast(low    as double)      as low,
    cast(close  as double)      as close,
    cast(volume as bigint)      as volume,
    cast(vwap   as double)      as vwap,
    cast(sma_20          as double) as sma_20,
    cast(sma_50          as double) as sma_50,
    cast(rsi_14          as double) as rsi_14,
    cast(volume_zscore   as double) as volume_zscore,
    cast(vwap_deviation  as double) as vwap_deviation,
    cast(pct_change      as double) as pct_change,
    ingested_at

from {{ source('silver', 'stock_metrics') }}

where close  is not null
  and volume is not null
  and volume > 0
