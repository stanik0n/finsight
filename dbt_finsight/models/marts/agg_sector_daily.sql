-- Sector-level daily aggregates: average RSI, volume z-score, and top movers per sector.

select
    t.sector,
    f.date,
    round(avg(f.rsi_14),          2) as avg_rsi,
    round(avg(f.volume_zscore),   2) as avg_volume_zscore,
    round(avg(f.pct_change),      2) as avg_pct_change,
    round(max(f.pct_change),      2) as max_pct_change,
    round(min(f.pct_change),      2) as min_pct_change,
    count(distinct f.symbol)          as ticker_count,

    -- Top gainer and loser symbols
    arg_max(f.symbol, f.pct_change)   as top_gainer_symbol,
    arg_min(f.symbol, f.pct_change)   as top_loser_symbol

from {{ ref('fct_daily_stock_metrics') }} f
join {{ ref('dim_tickers') }}             t on f.symbol = t.symbol

group by t.sector, f.date
