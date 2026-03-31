-- Ticker dimension: symbol metadata from the seed file.

select
    symbol,
    name,
    sector,
    market_cap_tier

from {{ ref('tickers_metadata') }}
