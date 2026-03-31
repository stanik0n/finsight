"""
Portfolio calculation: takes a list of holdings and returns current
value, P&L per position, and sector exposure using Gold DuckDB prices.
"""

import os

import duckdb

DUCKDB_PATH = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')


def calculate_portfolio(holdings: list[dict]) -> dict:
    """
    Args:
        holdings: [{'symbol': 'AAPL', 'shares': 100, 'avg_cost': 150.0}, ...]

    Returns:
        {
            'as_of_date': str,
            'total_value': float,
            'total_cost': float,
            'total_pnl': float,
            'total_pnl_pct': float,
            'positions': [...],
            'sector_exposure': [...],
        }
    """
    if not holdings:
        return {
            'as_of_date': None,
            'total_value': 0,
            'total_cost': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'positions': [],
            'sector_exposure': [],
        }

    symbols = [h['symbol'].upper() for h in holdings]
    placeholders = ', '.join('?' for _ in symbols)

    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        rows = conn.execute(f"""
            SELECT symbol, company_name, sector, close, date
            FROM main_gold.mart_query_context
            WHERE date = (SELECT max(date) FROM main_gold.mart_query_context)
              AND symbol IN ({placeholders})
        """, symbols).fetchall()
    finally:
        conn.close()

    # Map symbol → latest price row
    prices = {r[0]: {'company_name': r[1], 'sector': r[2], 'close': r[3], 'date': str(r[4])}
              for r in rows}

    as_of_date = rows[0][4] if rows else None
    positions = []

    for h in holdings:
        sym = h['symbol'].upper()
        if sym not in prices:
            continue  # unknown ticker — skip silently
        p = prices[sym]
        value = p['close'] * h['shares']
        cost = h['avg_cost'] * h['shares']
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        positions.append({
            'symbol': sym,
            'company_name': p['company_name'],
            'sector': p['sector'],
            'shares': h['shares'],
            'avg_cost': h['avg_cost'],
            'current_price': p['close'],
            'value': round(value, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        })

    total_value = sum(p['value'] for p in positions)
    total_cost = sum(p['shares'] * p['avg_cost'] for p in positions)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    # Sector exposure
    sector_totals: dict[str, float] = {}
    for p in positions:
        sector_totals[p['sector']] = sector_totals.get(p['sector'], 0) + p['value']

    sector_exposure = [
        {
            'sector': sector,
            'value': round(value, 2),
            'pct': round(value / total_value * 100, 1) if total_value else 0,
        }
        for sector, value in sorted(sector_totals.items(), key=lambda x: -x[1])
    ]

    return {
        'as_of_date': str(as_of_date) if as_of_date else None,
        'total_value': round(total_value, 2),
        'total_cost': round(total_cost, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl_pct, 2),
        'positions': positions,
        'sector_exposure': sector_exposure,
    }
