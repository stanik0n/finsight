-- Wide denormalized view used by the Qwen text-to-SQL layer.
-- This is the primary table the LLM generates SQL against.
-- Includes all indicators + ticker metadata in a single flat table.

select
    f.symbol,
    t.name                          as company_name,
    t.sector,
    t.market_cap_tier,
    f.date,
    f.open,
    f.high,
    f.low,
    f.close,
    f.volume,
    f.vwap,
    round(f.sma_20,         4)      as sma_20,
    round(f.sma_50,         4)      as sma_50,
    round(f.rsi_14,         2)      as rsi_14,
    round(f.volume_zscore,  2)      as volume_zscore,
    round(f.vwap_deviation, 4)      as vwap_deviation,
    round(f.pct_change,     4)      as pct_change,

    -- Derived convenience flags (useful for natural language queries)
    case when f.rsi_14 < 30  then true else false end as is_oversold,
    case when f.rsi_14 > 70  then true else false end as is_overbought,
    case when f.volume_zscore > 2.5 then true else false end as is_volume_spike,
    case when f.close > f.sma_50    then true else false end as is_above_sma50,
    case when abs(f.pct_change) > 5 then true else false end as is_large_move

from {{ ref('fct_daily_stock_metrics') }} f
join {{ ref('dim_tickers') }}             t on f.symbol = t.symbol
