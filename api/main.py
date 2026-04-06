"""
FinSight FastAPI backend — Phase 3.

Endpoints:
  POST /query         — NL question → SQL → results + analyst commentary
                        Routes to hot (intraday.duckdb) or cold (Gold DuckDB) based on intent
  GET  /health        — pipeline status + DuckDB freshness
  GET  /schema        — mart_query_context column list (for UI hints)
  GET  /anomalies     — latest-date anomaly signals from the gold table
  GET  /stream-status — live intraday stream health (bar count, latest timestamp)
  GET  /market-snapshot — latest warehouse-driven sector and mover snapshot
"""

import os
import re
import time
from datetime import datetime, timedelta
from difflib import get_close_matches
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
import requests
import yfinance as yf

from commentary import generate_commentary
from auth import INTERNAL_API_KEY, get_current_user_id
from hot_query import hot_query
from portfolio import (
    build_portfolio_brief,
    calculate_portfolio,
    calculate_saved_portfolio,
    calculate_watchlist_snapshot,
    complete_telegram_link,
    create_telegram_link_code,
    current_central_date,
    delete_holding,
    delete_ticker_note,
    delete_watchlist_symbol,
    ensure_portfolio_tables,
    get_alert_preferences,
    get_telegram_link_status,
    list_holdings,
    list_portfolio_alerts,
    list_telegram_chat_links,
    list_ticker_notes,
    list_watchlist,
    mark_delivery_sent,
    mark_alerts_sent,
    refresh_portfolio_alerts,
    should_send_delivery,
    unlink_telegram_chat_for_user,
    update_alert_preferences,
    upsert_holding,
    upsert_ticker_note,
    upsert_watchlist_symbol,
)
from qwen_agent import query as nl_query
from schema_context import MART_QUERY_CONTEXT_DDL

def _csv_env(name: str, default: str) -> list[str]:
    raw_value = os.environ.get(name, default)
    return [item.strip() for item in raw_value.split(',') if item.strip()]


FINSIGHT_ENV = os.environ.get('FINSIGHT_ENV', 'development').strip().lower()
ALLOWED_ORIGINS = _csv_env('FINSIGHT_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
ALLOWED_HOSTS = _csv_env('FINSIGHT_ALLOWED_HOSTS', 'localhost,127.0.0.1,api')

app = FastAPI(
    title='FinSight API',
    description='Natural Language Analytics Engine for Market Data',
    version='1.0.0',
    docs_url=None if FINSIGHT_ENV == 'production' else '/docs',
    redoc_url=None if FINSIGHT_ENV == 'production' else '/redoc',
    openapi_url=None if FINSIGHT_ENV == 'production' else '/openapi.json',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'X-Requested-With', 'X-Finsight-Service-Key', 'X-Telegram-Chat-Id'],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS or ['*'])


def _send_telegram_message(text: str, chat_id: str | None = None) -> None:
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    resolved_chat_id = (chat_id or '').strip() or os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not bot_token or not resolved_chat_id:
        raise RuntimeError('TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured.')

    resp = requests.post(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        json={
            'chat_id': resolved_chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        },
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get('ok'):
        raise RuntimeError(f"Telegram API error: {payload}")


def _format_portfolio_brief_message(brief: dict) -> str:
    portfolio = brief.get('portfolio', {})
    watchlist = brief.get('watchlist', {}) or {}
    alerts = brief.get('alerts', [])
    as_of_date = brief.get('as_of_date') or 'n/a'
    positions = portfolio.get('positions', [])
    watchlist_items = watchlist.get('items', []) or []
    top_position = portfolio.get('portfolio_insights', {}).get('top_position')

    lines = [
        f"<b>FinSight Portfolio Brief — {as_of_date}</b>",
        '',
        brief.get('summary', 'No portfolio summary available.'),
    ]

    if top_position:
        lines.extend([
            '',
            f"<b>Top concentration:</b> {top_position['symbol']} at {top_position['weight_pct']:.1f}% of value",
        ])

    if positions:
        lines.extend(['', '<b>Tracked holdings:</b>'])
        for position in positions[:5]:
            lines.append(
                f"• {position['symbol']}: ${position['current_price']:.2f} | "
                f"P&L {position['pnl']:+,.2f} ({position['pnl_pct']:+.2f}%)"
            )

    if watchlist_items:
        lines.extend(['', '<b>Watchlist:</b>'])
        for item in watchlist_items[:3]:
            change = item.get('daily_pct_change')
            change_text = f" | {change:+.2f}%" if change is not None else ''
            lines.append(
                f"• {item['symbol']}: ${item['current_price']:.2f}{change_text}"
            )

    if alerts:
        lines.extend(['', f"<b>Alerts ({len(alerts)}):</b>"])
        for alert in alerts[:5]:
            lines.append(f"• {alert['title']} — {alert['message']}")

    return '\n'.join(lines)


def _require_internal_service_key(x_finsight_service_key: str | None) -> None:
    if not INTERNAL_API_KEY or x_finsight_service_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail='Internal service authentication required.')

DUCKDB_PATH = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')
INTRADAY_DUCKDB_PATH = os.environ.get('INTRADAY_DUCKDB_PATH', '/data/intraday.duckdb')
_BENCHMARK_CACHE: dict[str, object] = {'ts': 0.0, 'data': []}
_BENCHMARK_TTL_SECONDS = 300
_HEADER_TICKER_CACHE: dict[str, object] = {'ts': 0.0, 'data': []}
_ETF_CACHE_MINUTES = int(os.environ.get('TWELVE_DATA_CACHE_MINUTES', '15'))
_MARKET_NEWS_CACHE: dict[str, dict[str, object]] = {}
_MARKET_NEWS_TTL_SECONDS = 900
_CENTRAL_TZ = ZoneInfo('America/Chicago')

# Keywords that signal the user wants live intraday data (hot path)
_HOT_KEYWORDS = frozenset([
    'intraday', 'live', 'real-time', 'realtime', 'streaming',
    'current price', 'right now', 'premarket', 'pre-market',
    'after hours', 'afterhours', 'after-hours', 'this morning',
    'latest price', 'trading now',
])

_PRICE_INTENT_KEYWORDS = frozenset([
    'price', 'quote', 'trading', 'move', 'moving', 'up', 'down',
    'change', 'gain', 'loss', 'worth', 'bid', 'ask',
])

_HYBRID_KEYWORDS = frozenset([
    'compare', 'versus', 'vs', 'relative to', 'against',
    'sma', 'moving average', '20-day', '50-day', 'rsi',
    'historical', 'last close', 'daily close',
])
_WATCHLIST_KEYWORDS = frozenset([
    'what should i buy', 'what should i watch', 'buy tomorrow', 'buy next',
    'watchlist', 'best setup', 'setups', 'ideas', 'opportunities',
])
_WATCHLIST_ALERT_KEYWORDS = frozenset([
    'watchlist alert', 'watchlist alerts', 'watchlist signal', 'watchlist signals',
    'tracked names', 'tracked name', 'watchlist momentum', 'anything on my watchlist',
    'what should i know about',
])
_OPINION_KEYWORDS = frozenset([
    'do you think', 'will it go up', 'will it go down', 'go up tomorrow', 'go down tomorrow',
    'bullish', 'bearish', 'be worried', 'worry about', 'good buy', 'good time to buy',
    'should i buy', 'should i sell', 'what do you think about',
])
_NEWS_KEYWORDS = frozenset([
    'market news', 'news', 'headline', 'headlines', 'story', 'stories',
    'article', 'articles', 'press release', 'press releases', 'what matters most',
])

_TRACKED_SYMBOLS = frozenset([
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA', 'AMD', 'INTC', 'CRM',
    'JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK', 'AXP', 'USB', 'COF',
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'MPC', 'VLO', 'OXY', 'HAL',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN',
    'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'BKNG', 'MAR', 'COST',
])

_COMPANY_ALIASES = {
    'apple': 'AAPL',
    'microsoft': 'MSFT',
    'nvidia': 'NVDA',
    'google': 'GOOGL',
    'alphabet': 'GOOGL',
    'meta': 'META',
    'facebook': 'META',
    'amazon': 'AMZN',
    'tesla': 'TSLA',
    'amd': 'AMD',
    'intel': 'INTC',
    'salesforce': 'CRM',
    'jpmorgan': 'JPM',
    'blackrock': 'BLK',
    'exxon': 'XOM',
    'chevron': 'CVX',
    'pfizer': 'PFE',
    'costco': 'COST',
    'booking': 'BKNG',
}

_PORTFOLIO_KEYWORDS = frozenset([
    'my portfolio', 'my holdings', 'my positions', 'portfolio', 'holdings', 'positions',
    'my account', 'my exposure', 'my risk',
])
_PORTFOLIO_FUZZY_TERMS = ('portfolio', 'holdings', 'positions', 'account', 'exposure', 'risk')
_NOTE_KEYWORDS = frozenset([
    'note', 'notes', 'thesis', 'memo', 'remember', 'why do i own', 'save note',
])
_CONVERSATIONAL_KEYWORDS = frozenset([
    'hi', 'hello', 'hey', 'how are you', 'how are u', 'whats up', "what's up",
    'good morning', 'good afternoon', 'good evening', 'yo', 'sup',
    'who are you', 'what can you do', 'thanks', 'thank you',
])


# ── Models ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    results: list[dict]
    path: str               # 'cold', 'hot', or 'hybrid'
    row_count: int
    commentary: str = ''    # analyst summary — Phase 2


# ── Helpers ─────────────────────────────────────────────────────────────────

def _is_hot_query(question: str) -> bool:
    q = question.lower()
    if any(kw in q for kw in _HOT_KEYWORDS):
        return True

    tokens = {token.upper() for token in q.replace('?', ' ').replace(',', ' ').split()}
    resolved_symbol = _extract_symbol(question)
    has_symbol = any(symbol in tokens for symbol in _TRACKED_SYMBOLS)
    has_alias = bool(resolved_symbol)
    has_price_intent = any(keyword in q for keyword in _PRICE_INTENT_KEYWORDS)

    if (has_symbol or has_alias) and has_price_intent:
        return True

    # Short single-ticker/company prompts like "META?" or "google stock" should prefer live routing.
    if (has_symbol or has_alias) and len(tokens) <= 4:
        return True

    return False


def _format_central_time(value) -> str:
    if value is None:
        return 'n/a'

    if isinstance(value, str):
        normalized = value.replace('Z', '+00:00')
        dt = datetime.fromisoformat(normalized)
    else:
        dt = value

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))

    local_dt = dt.astimezone(_CENTRAL_TZ)
    tz_label = local_dt.tzname() or 'CT'
    return local_dt.strftime(f'%b %-d, %-I:%M %p {tz_label}')


def _extract_symbol(question: str) -> str | None:
    q = question.lower()
    cleaned_tokens = [token.strip(" ?!.,:;'\"()[]{}").lower() for token in q.split()]
    tokens = {token.upper() for token in cleaned_tokens if token}

    for symbol in _TRACKED_SYMBOLS:
        if symbol in tokens:
            return symbol

    for alias, symbol in _COMPANY_ALIASES.items():
        if alias in q:
            return symbol

    alias_candidates = list(_COMPANY_ALIASES.keys())
    for token in cleaned_tokens:
        if not token:
            continue
        matches = get_close_matches(token, alias_candidates, n=1, cutoff=0.8)
        if matches:
            return _COMPANY_ALIASES[matches[0]]

    return None


def _is_portfolio_query(question: str) -> bool:
    q = question.lower()
    if _is_note_query(question):
        return True
    if any(keyword in q for keyword in _PORTFOLIO_KEYWORDS):
        return True

    cleaned_tokens = [token.strip(" ?!.,:;'\"()[]{}").lower() for token in q.split()]
    if 'my' not in cleaned_tokens:
        return False

    for token in cleaned_tokens:
        if not token:
            continue
        if token.startswith('portfol'):
            return True
        matches = get_close_matches(token, list(_PORTFOLIO_FUZZY_TERMS), n=1, cutoff=0.78)
        if matches:
            return True

    return False


def _is_note_query(question: str) -> bool:
    q = question.lower()
    return bool(_extract_symbol(question)) and any(keyword in q for keyword in _NOTE_KEYWORDS)


def _notes_by_type(notes: list[dict], note_type: str) -> list[dict]:
    return [note for note in notes if (note.get('note_type') or 'note') == note_type]


def _route_query(question: str) -> str:
    q = question.lower()
    if _is_portfolio_query(question):
        return 'portfolio'
    if _is_hot_query(question):
        if any(keyword in q for keyword in _HYBRID_KEYWORDS) and _extract_symbol(question):
            return 'hybrid'
        return 'hot'
    return 'cold'


def _is_watchlist_query(question: str) -> bool:
    q = question.lower()
    return any(keyword in q for keyword in _WATCHLIST_KEYWORDS) or (
        'buy' in q and any(word in q for word in ['tomorrow', 'next', 'watch', 'idea', 'ideas'])
    )


def _is_watchlist_alert_query(question: str) -> bool:
    q = question.lower()
    return 'watchlist' in q and (
        'alert' in q
        or 'alerts' in q
        or any(keyword in q for keyword in _WATCHLIST_ALERT_KEYWORDS)
    )


def _is_news_query(question: str) -> bool:
    q = question.lower()
    if _is_note_query(question) or _is_portfolio_query(question):
        return False
    return any(keyword in q for keyword in _NEWS_KEYWORDS)


def _is_opinion_query(question: str) -> bool:
    q = question.lower()
    return bool(_extract_symbol(question)) and (
        any(keyword in q for keyword in _OPINION_KEYWORDS) or
        (
            'tomorrow' in q and any(word in q for word in ['up', 'down', 'higher', 'lower'])
        )
    )


def _normalize_small_talk(question: str) -> str:
    return re.sub(r'[^a-z0-9\s\?]', '', question.lower()).strip()


def _is_conversational_query(question: str) -> bool:
    normalized = _normalize_small_talk(question)
    if not normalized:
        return False
    if len(normalized.split()) > 8:
        return False
    return any(keyword in normalized for keyword in _CONVERSATIONAL_KEYWORDS)


def _run_conversational_query(question: str) -> dict:
    normalized = _normalize_small_talk(question)

    if any(phrase in normalized for phrase in ['how are you', 'how are u']):
        commentary = (
            "Doing well. What are you in the mood to look at today?"
        )
    elif any(phrase in normalized for phrase in ['who are you', 'what can you do']):
        commentary = (
            "I'm FinSight. Ask me about markets, stocks, news, or your portfolio."
        )
    elif any(phrase in normalized for phrase in ['thanks', 'thank you']):
        commentary = "Anytime."
    else:
        commentary = (
            "Hey."
        )

    return {
        'question': question,
        'sql': 'conversation: no market query executed',
        'results': [],
        'path': 'conversation',
        'commentary': commentary,
    }


def _run_portfolio_query(question: str, user_id: str | None = None) -> dict:
    portfolio = calculate_saved_portfolio(user_id=user_id)
    holdings = portfolio.get('holdings', [])
    positions = portfolio.get('positions', [])
    insights = portfolio.get('portfolio_insights', {})
    q = question.lower()

    if _is_note_query(question):
        symbol = _extract_symbol(question)
        notes = list_ticker_notes(symbol, user_id=user_id)
        if not notes:
            commentary = (
                f"There are no saved research notes for {symbol} yet. Add one in Portfolio memory or from Telegram with "
                f"`/note {symbol} ...`."
            )
        else:
            thesis_notes = _notes_by_type(notes, 'thesis')
            risk_notes = _notes_by_type(notes, 'risk')
            exit_notes = _notes_by_type(notes, 'exit')
            review_notes = _notes_by_type(notes, 'review')

            if any(keyword in q for keyword in ['why do i own', 'thesis', 'remember']):
                target_note = thesis_notes[0] if thesis_notes else notes[0]
                label = 'thesis' if thesis_notes else 'note'
                commentary = f"Your latest saved {label} for {symbol} is: {target_note['note_text']}"
            elif any(keyword in q for keyword in ['risk', 'risk rule', 'what is the risk', 'why should i worry']):
                if risk_notes:
                    commentary = f"Your current risk rule for {symbol} is: {risk_notes[0]['note_text']}"
                else:
                    commentary = f"You do not have a saved risk note for {symbol} yet."
            elif any(keyword in q for keyword in ['exit', 'sell', 'trim', 'when do i get out']):
                if exit_notes:
                    commentary = f"Your saved exit trigger for {symbol} is: {exit_notes[0]['note_text']}"
                else:
                    commentary = f"You do not have a saved exit note for {symbol} yet."
            elif any(keyword in q for keyword in ['review', 'check-in', 'what changed since my last review']):
                if review_notes:
                    target_note = review_notes[0]
                    review_suffix = f" Next review date: {target_note['review_date']}." if target_note.get('review_date') else ''
                    commentary = f"Your latest review note for {symbol} is: {target_note['note_text']}{review_suffix}"
                else:
                    commentary = f"You do not have a saved review note for {symbol} yet."
            else:
                commentary = (
                    f"You have {len(notes)} saved memory entr{'y' if len(notes) == 1 else 'ies'} for {symbol}: "
                    f"{len(thesis_notes)} thesis, {len(risk_notes)} risk, {len(exit_notes)} exit, and {len(review_notes)} review. "
                    f"The latest is: {notes[0]['note_text']}"
                )
        return {
            'question': question,
            'sql': f'portfolio memory: saved notes for {symbol}',
            'results': notes[:10],
            'path': 'portfolio',
            'commentary': commentary,
        }

    if not holdings:
        return {
            'question': question,
            'sql': 'portfolio: saved holdings summary',
            'results': [],
            'path': 'portfolio',
            'commentary': 'You do not have any saved holdings yet. Add positions in the Portfolio tab first, then ask portfolio-specific questions.',
        }

    if any(keyword in q for keyword in ['overbought', 'oversold', 'rsi']):
        filtered = [
            position for position in positions
            if position.get('rsi_14') is not None and (
                ('overbought' in q and position['rsi_14'] >= 70) or
                ('oversold' in q and position['rsi_14'] <= 30) or
                ('rsi' in q and True)
            )
        ]
        filtered.sort(key=lambda row: row.get('rsi_14') or 0, reverse=True)
        if not filtered:
            commentary = 'None of your saved holdings currently match that RSI condition.'
        elif 'oversold' in q:
            commentary = 'The most oversold holdings in your portfolio are ' + ', '.join(
                f"{row['symbol']} (RSI {row['rsi_14']:.1f})" for row in filtered[:5]
            ) + '.'
        elif 'overbought' in q:
            commentary = 'The most overbought holdings in your portfolio are ' + ', '.join(
                f"{row['symbol']} (RSI {row['rsi_14']:.1f})" for row in filtered[:5]
            ) + '.'
        else:
            commentary = 'Here are the latest RSI readings across your saved holdings.'
        return {
            'question': question,
            'sql': 'portfolio: positions filtered by RSI',
            'results': filtered[:10],
            'path': 'portfolio',
            'commentary': commentary,
        }

    if any(keyword in q for keyword in ['compare', 'versus', 'vs']) and any(benchmark in q for benchmark in ['spy', 'qqq', 'vti', 'iwm']):
        benchmark_map = {item['symbol'].lower(): item for item in _get_benchmark_snapshot()}
        benchmark_symbol = next((ticker for ticker in ['spy', 'qqq', 'vti', 'iwm'] if ticker in q), 'spy')
        benchmark = benchmark_map.get(benchmark_symbol)
        portfolio_daily = insights.get('weighted_daily_change_pct', 0)
        benchmark_change = float(benchmark.get('pct_change', 0)) if benchmark else 0
        delta = round(portfolio_daily - benchmark_change, 2)
        commentary = (
            f"Your portfolio's weighted daily move is {portfolio_daily:+.2f}% versus "
            f"{benchmark_symbol.upper()} at {benchmark_change:+.2f}%, a relative difference of {delta:+.2f}%."
        )
        return {
            'question': question,
            'sql': f'portfolio: weighted daily move compared to {benchmark_symbol.upper()}',
            'results': [{
                'portfolio_daily_change_pct': portfolio_daily,
                'benchmark_symbol': benchmark_symbol.upper(),
                'benchmark_daily_change_pct': benchmark_change,
                'relative_difference_pct': delta,
            }],
            'path': 'portfolio',
            'commentary': commentary,
        }

    if any(keyword in q for keyword in ['concentrated', 'concentration', 'biggest risk', 'largest position', 'risk']):
        top_position = insights.get('top_position')
        concentration = insights.get('concentration', {})
        sector_exposure = portfolio.get('sector_exposure', [])
        top_sector = sector_exposure[0] if sector_exposure else None
        commentary = (
            f"Your biggest concentration risk is {top_position['symbol']} at {top_position['weight_pct']:.1f}% of portfolio value. "
            f"Sector exposure is led by {top_sector['sector']} at {top_sector['pct']:.1f}%."
            if top_position and top_sector
            else 'Your portfolio concentration looks balanced right now.'
        )
        return {
            'question': question,
            'sql': 'portfolio: concentration summary',
            'results': [{
                'top_position_symbol': top_position['symbol'] if top_position else None,
                'top_position_weight_pct': top_position['weight_pct'] if top_position else 0,
                'concentration_level': concentration.get('level', 'Balanced'),
                'top_sector': top_sector['sector'] if top_sector else None,
                'top_sector_weight_pct': top_sector['pct'] if top_sector else 0,
            }],
            'path': 'portfolio',
            'commentary': commentary,
        }

    top_position = insights.get('top_position')
    concentration = insights.get('concentration', {})
    weighted_daily_change = float(insights.get('weighted_daily_change_pct') or 0)
    summary_row = {
        'portfolio_label': 'Saved Portfolio',
        'position_count': len(positions),
        'total_value': float(portfolio.get('total_value') or 0),
        'total_cost': float(portfolio.get('total_cost') or 0),
        'total_pnl': float(portfolio.get('total_pnl') or 0),
        'total_pnl_pct': float(portfolio.get('total_pnl_pct') or 0),
        'weighted_daily_change_pct': weighted_daily_change,
        'top_position_symbol': top_position.get('symbol') if top_position else None,
        'top_position_weight_pct': float(top_position.get('weight_pct') or 0) if top_position else 0,
        'concentration_level': concentration.get('level', 'Balanced'),
    }
    commentary = (
        f"Your saved portfolio is worth ${summary_row['total_value']:,.2f} across {summary_row['position_count']} positions, "
        f"with total unrealized P&L of {summary_row['total_pnl']:+,.2f} ({summary_row['total_pnl_pct']:+.2f}%). "
        f"The largest position is {summary_row['top_position_symbol'] or 'n/a'} at "
        f"{summary_row['top_position_weight_pct']:.1f}% of portfolio value, and the current concentration profile is "
        f"{summary_row['concentration_level'].lower()}."
    )
    return {
        'question': question,
        'sql': 'portfolio: saved portfolio summary',
        'results': [summary_row],
        'path': 'portfolio',
        'commentary': commentary,
    }


def _run_watchlist_query(question: str, user_id: str | None = None) -> dict:
    if _is_watchlist_alert_query(question):
        alerts = [
            alert for alert in refresh_portfolio_alerts(user_id=user_id)
            if alert.get('source_scope') == 'watchlist'
        ]
        if not alerts:
            snapshot = calculate_watchlist_snapshot(user_id=user_id)
            summary = snapshot.get('summary') or {}
            top_mover = summary.get('top_mover')
            commentary = (
                f"There are no active watchlist alerts right now. Your tracked list has {summary.get('count', 0)} "
                f"name{'s' if summary.get('count', 0) != 1 else ''}"
            )
            if top_mover and top_mover.get('daily_pct_change') is not None:
                commentary += (
                    f", with {top_mover['symbol']} currently moving {top_mover['daily_pct_change']:+.2f}% on the latest snapshot."
                )
            else:
                commentary += '.'
            return {
                'question': question,
                'sql': 'watchlist: active watchlist alerts',
                'results': [],
                'path': 'watchlist',
                'commentary': commentary,
            }

        top_titles = ', '.join(alert['title'] for alert in alerts[:3])
        commentary = (
            f"Your watchlist currently has {len(alerts)} active alert"
            f"{'s' if len(alerts) != 1 else ''}. "
            f"The most important items are {top_titles}."
        )
        return {
            'question': question,
            'sql': 'watchlist: active watchlist alerts',
            'results': alerts[:10],
            'path': 'watchlist',
            'commentary': commentary,
        }

    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        latest_date = conn.execute(
            "SELECT max(date) FROM main_gold.mart_query_context"
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT
                symbol,
                company_name,
                sector,
                close,
                pct_change,
                rsi_14,
                volume_zscore,
                is_above_sma50,
                is_overbought,
                is_oversold
            FROM main_gold.mart_query_context
            WHERE date = ?
              AND COALESCE(is_above_sma50, FALSE) = TRUE
              AND COALESCE(is_overbought, FALSE) = FALSE
              AND COALESCE(rsi_14, 0) BETWEEN 45 AND 68
            ORDER BY COALESCE(volume_zscore, 0) DESC,
                     COALESCE(pct_change, 0) DESC,
                     COALESCE(rsi_14, 0) DESC
            LIMIT 5
            """,
            [latest_date],
        ).fetchall()
    finally:
        conn.close()

    results = [
        {
            'symbol': row[0],
            'company_name': row[1],
            'sector': row[2],
            'close': float(row[3]) if row[3] is not None else None,
            'pct_change': float(row[4]) if row[4] is not None else None,
            'rsi_14': float(row[5]) if row[5] is not None else None,
            'volume_zscore': float(row[6]) if row[6] is not None else None,
            'is_above_sma50': bool(row[7]),
            'is_overbought': bool(row[8]),
            'is_oversold': bool(row[9]),
            'watchlist_tag': 'Momentum watch',
        }
        for row in rows
    ]

    if not results:
        commentary = (
            "I can't responsibly tell you what to buy tomorrow from this snapshot alone. "
            "Right now I also do not see any clean technical watchlist candidates in the tracked universe, "
            "so the better move is to wait for a stronger setup or ask for a sector-specific screen."
        )
        return {
            'question': question,
            'sql': 'watchlist: no clean candidates in latest warehouse snapshot',
            'results': [],
            'path': 'cold',
            'commentary': commentary,
        }

    names = ', '.join(
        f"{row['symbol']} ({row['sector']}, RSI {row['rsi_14']:.1f})"
        for row in results[:3]
        if row.get('rsi_14') is not None
    )
    commentary = (
        "I can't tell you what to buy tomorrow with certainty, but the cleanest watchlist candidates from the latest "
        f"warehouse snapshot are {names}. These names are still above their 50-day trend, are not yet flagged as "
        "overbought, and are showing relatively strong momentum or activity. Treat this as a watchlist, not a buy signal."
    )
    return {
        'question': question,
        'sql': 'watchlist: technical candidates above sma50 with healthy RSI',
        'results': results,
        'path': 'cold',
        'commentary': commentary,
    }


def _run_opinion_query(question: str) -> dict:
    symbol = _extract_symbol(question)
    if not symbol:
        raise ValueError('Opinion query requires a tracked ticker or company name.')

    live_conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
    try:
        live_row = live_conn.execute(
            """
            SELECT symbol, timestamp, close, vwap, volume
            FROM intraday_bars
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [symbol],
        ).fetchone()
    finally:
        live_conn.close()

    gold_conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        gold_row = gold_conn.execute(
            """
            SELECT company_name, sector, date, close, sma_20, sma_50, rsi_14, pct_change
            FROM main_gold.mart_query_context
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            [symbol],
        ).fetchone()
    finally:
        gold_conn.close()

    if not gold_row:
        raise RuntimeError(f'No historical Gold record found for {symbol}.')

    live_price = float(live_row[2]) if live_row and live_row[2] is not None else None
    vwap = float(live_row[3]) if live_row and live_row[3] is not None else None
    intraday_volume = int(live_row[4]) if live_row and live_row[4] is not None else None
    daily_close = float(gold_row[3]) if gold_row[3] is not None else None
    sma_20 = float(gold_row[4]) if gold_row[4] is not None else None
    sma_50 = float(gold_row[5]) if gold_row[5] is not None else None
    rsi_14 = float(gold_row[6]) if gold_row[6] is not None else None
    daily_pct_change = float(gold_row[7]) if gold_row[7] is not None else None

    reference_price = live_price if live_price is not None else daily_close
    live_vs_close = None
    if live_price is not None and daily_close not in (None, 0):
        live_vs_close = round(((live_price - daily_close) / daily_close) * 100, 2)

    above_sma20 = reference_price is not None and sma_20 not in (None, 0) and reference_price > sma_20
    above_sma50 = reference_price is not None and sma_50 not in (None, 0) and reference_price > sma_50

    bullish_score = 0
    bearish_score = 0

    if above_sma20:
        bullish_score += 1
    else:
        bearish_score += 1
    if above_sma50:
        bullish_score += 1
    else:
        bearish_score += 1
    if rsi_14 is not None:
        if 50 <= rsi_14 <= 68:
            bullish_score += 1
        elif rsi_14 >= 70:
            bearish_score += 1
        elif rsi_14 <= 35:
            bearish_score += 1
    if daily_pct_change is not None:
        if daily_pct_change > 0:
            bullish_score += 1
        elif daily_pct_change < 0:
            bearish_score += 1
    if live_vs_close is not None:
        if live_vs_close > 0:
            bullish_score += 1
        elif live_vs_close < 0:
            bearish_score += 1

    if bullish_score >= bearish_score + 2:
        stance = 'bullish-leaning'
    elif bearish_score >= bullish_score + 2:
        stance = 'bearish-leaning'
    else:
        stance = 'mixed'

    bullish_factors = []
    bearish_factors = []

    if above_sma20:
        bullish_factors.append('holding above the 20-day trend')
    else:
        bearish_factors.append('trading below the 20-day trend')
    if above_sma50:
        bullish_factors.append('still above the 50-day trend')
    else:
        bearish_factors.append('trading below the 50-day trend')
    if rsi_14 is not None:
        if 50 <= rsi_14 <= 68:
            bullish_factors.append(f'RSI is constructive at {rsi_14:.1f}')
        elif rsi_14 >= 70:
            bearish_factors.append(f'RSI is stretched at {rsi_14:.1f}')
        elif rsi_14 <= 35:
            bearish_factors.append(f'RSI is weak at {rsi_14:.1f}')
    if live_vs_close is not None:
        if live_vs_close > 0:
            bullish_factors.append(f'live price is {live_vs_close:+.2f}% versus the last close')
        elif live_vs_close < 0:
            bearish_factors.append(f'live price is {live_vs_close:+.2f}% versus the last close')

    company_name = gold_row[0]
    latest_time_text = _format_central_time(live_row[1]) if live_row else None
    lead = (
        f"I can't predict tomorrow with certainty, but the current read on {company_name} ({symbol}) is {stance}."
    )
    price_sentence = (
        f" It is trading at ${live_price:.2f} as of {latest_time_text}"
        if live_price is not None
        else f" The latest daily close is ${daily_close:.2f}" if daily_close is not None else ''
    )
    context_sentence = (
        f" versus a recent close of ${daily_close:.2f}."
        if live_price is not None and daily_close is not None
        else '.'
    )
    bull_sentence = f" Bullish factors: {', '.join(bullish_factors[:3])}." if bullish_factors else ''
    bear_sentence = f" Bearish factors: {', '.join(bearish_factors[:3])}." if bearish_factors else ''
    caution_sentence = " This is a probability read from technical context, not a guaranteed forecast or a buy recommendation."

    commentary = lead + price_sentence + context_sentence + bull_sentence + bear_sentence + caution_sentence

    return {
        'question': question,
        'sql': 'opinion: live quote + historical technical context',
        'results': [{
            'symbol': symbol,
            'company_name': company_name,
            'sector': gold_row[1],
            'close': live_price if live_price is not None else daily_close,
            'timestamp': live_row[1] if live_row else gold_row[2],
            'vwap': vwap,
            'volume': intraday_volume,
            'latest_daily_close': daily_close,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rsi_14': rsi_14,
            'pct_change': live_vs_close if live_vs_close is not None else daily_pct_change,
            'analyst_stance': stance,
        }],
        'path': 'hybrid',
        'commentary': commentary,
    }


def _run_direct_hot_quote(question: str, symbol: str) -> dict:
    conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
    try:
        row = conn.execute(
            """
            SELECT symbol, timestamp, close, volume, vwap
            FROM intraday_bars
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [symbol],
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise RuntimeError(f'No live intraday bars found for {symbol}.')

    result_row = {
        'symbol': row[0],
        'timestamp': row[1],
        'close': float(row[2]) if row[2] is not None else None,
        'volume': int(row[3]) if row[3] is not None else None,
        'vwap': float(row[4]) if row[4] is not None else None,
    }

    return {
        'question': question,
        'sql': f"deterministic: latest intraday quote for {symbol}",
        'results': [result_row],
        'path': 'hot',
        'commentary': '',
    }


def _run_hybrid_query(question: str) -> dict:
    symbol = _extract_symbol(question)
    if not symbol:
        raise ValueError('Hybrid query requires a tracked ticker or company name.')

    live_conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
    try:
        live_row = live_conn.execute(
            """
            SELECT symbol, timestamp, close, vwap, volume
            FROM intraday_bars
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            [symbol],
        ).fetchone()
    finally:
        live_conn.close()

    if not live_row:
        raise RuntimeError(f'No live intraday bars found for {symbol}.')

    gold_conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        gold_row = gold_conn.execute(
            """
            SELECT company_name, sector, date, close, sma_20, sma_50, rsi_14, pct_change
            FROM main_gold.mart_query_context
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            [symbol],
        ).fetchone()
    finally:
        gold_conn.close()

    if not gold_row:
        raise RuntimeError(f'No historical Gold record found for {symbol}.')

    live_price = float(live_row[2]) if live_row[2] is not None else None
    daily_close = float(gold_row[3]) if gold_row[3] is not None else None
    sma_20 = float(gold_row[4]) if gold_row[4] is not None else None
    sma_50 = float(gold_row[5]) if gold_row[5] is not None else None
    rsi_14 = float(gold_row[6]) if gold_row[6] is not None else None

    live_vs_close = None
    if live_price is not None and daily_close not in (None, 0):
        live_vs_close = round(((live_price - daily_close) / daily_close) * 100, 2)

    live_vs_sma20 = None
    if live_price is not None and sma_20 not in (None, 0):
        live_vs_sma20 = round(((live_price - sma_20) / sma_20) * 100, 2)

    result_row = {
        'symbol': symbol,
        'company_name': gold_row[0],
        'sector': gold_row[1],
        'live_timestamp': live_row[1],
        'live_price': live_price,
        'intraday_vwap': float(live_row[3]) if live_row[3] is not None else None,
        'intraday_volume': int(live_row[4]) if live_row[4] is not None else None,
        'latest_daily_date': gold_row[2],
        'latest_daily_close': daily_close,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi_14': rsi_14,
        'daily_pct_change': float(gold_row[7]) if gold_row[7] is not None else None,
        'live_vs_daily_close_pct': live_vs_close,
        'live_vs_sma20_pct': live_vs_sma20,
    }

    commentary_parts = [
        f"{gold_row[0]} ({symbol}) is trading at ${live_price:.2f} as of {live_row[1]}."
        if live_price is not None
        else f"{gold_row[0]} ({symbol}) has no current live price available."
    ]
    if daily_close is not None and gold_row[2] is not None:
        delta_text = (
            f", which is {live_vs_close:+.2f}% versus its latest daily close"
            if live_vs_close is not None
            else ""
        )
        commentary_parts.append(
            f"Its latest warehouse close was ${daily_close:.2f} on {gold_row[2]}{delta_text}."
        )
    if sma_20 is not None and rsi_14 is not None:
        sma_text = (
            f" The live price is {live_vs_sma20:+.2f}% versus the 20-day average of ${sma_20:.2f}."
            if live_vs_sma20 is not None
            else f" The latest 20-day average is ${sma_20:.2f}."
        )
        commentary_parts.append(f"The latest RSI is {rsi_14:.1f}.{sma_text}")

    return {
        'question': question,
        'sql': 'hybrid: latest intraday quote + latest gold indicators',
        'results': [result_row],
        'path': 'hybrid',
        'commentary': ' '.join(commentary_parts),
    }


def _get_duckdb_freshness() -> dict:
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        row = conn.execute(
            "SELECT max(date), count(*) FROM main_gold.mart_query_context"
        ).fetchone()
        conn.close()
        return {'latest_date': str(row[0]) if row[0] else None, 'row_count': row[1]}
    except Exception as e:
        return {'latest_date': None, 'row_count': 0, 'error': str(e)}


def _ensure_etf_cache_table() -> None:
    conn = duckdb.connect(DUCKDB_PATH)
    try:
        conn.execute("CREATE SCHEMA IF NOT EXISTS main_cache")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS main_cache.etf_quotes_cache (
                symbol TEXT,
                label TEXT,
                close DOUBLE,
                pct_change DOUBLE,
                quote_date TEXT,
                source TEXT,
                fetched_at TIMESTAMP
            )
            """
        )
    finally:
        conn.close()


def _read_cached_etf_quotes(max_age_minutes: int) -> list[dict]:
    _ensure_etf_cache_table()
    conn = duckdb.connect(DUCKDB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT symbol, label, close, pct_change, quote_date, source, fetched_at
            FROM main_cache.etf_quotes_cache
            WHERE fetched_at >= CAST(NOW() AS TIMESTAMP) - (? * INTERVAL '1 minute')
            ORDER BY
              CASE symbol
                WHEN 'SPY' THEN 1
                WHEN 'QQQ' THEN 2
                WHEN 'VTI' THEN 3
                WHEN 'IWM' THEN 4
                ELSE 99
              END
            """,
            [max_age_minutes],
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            'symbol': row[0],
            'label': row[1],
            'close': float(row[2]) if row[2] is not None else None,
            'pct_change': float(row[3]) if row[3] is not None else 0.0,
            'date': row[4],
            'source': row[5],
            'fetched_at': str(row[6]) if row[6] is not None else None,
        }
        for row in rows
    ]


def _write_cached_etf_quotes(quotes: list[dict]) -> None:
    if not quotes:
        return

    _ensure_etf_cache_table()
    conn = duckdb.connect(DUCKDB_PATH)
    try:
        conn.execute("DELETE FROM main_cache.etf_quotes_cache")
        for quote in quotes:
            conn.execute(
                """
                INSERT INTO main_cache.etf_quotes_cache
                (symbol, label, close, pct_change, quote_date, source, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, NOW())
                """,
                [
                    quote['symbol'],
                    quote['label'],
                    quote['close'],
                    quote['pct_change'],
                    quote.get('date'),
                    quote.get('source'),
                ],
            )
    finally:
        conn.close()


def _get_intraday_status() -> dict:
    try:
        conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
        row = conn.execute(
            "SELECT count(*), max(timestamp) FROM intraday_bars"
        ).fetchone()
        conn.close()
        bar_count = row[0] or 0
        return {
            'live': bar_count > 0,
            'bar_count': bar_count,
            'latest_bar': str(row[1]) if row[1] else None,
        }
    except Exception as e:
        return {'live': False, 'bar_count': 0, 'latest_bar': None, 'error': str(e)}


def _get_benchmark_snapshot() -> list[dict]:
    now = time.time()
    cached = _BENCHMARK_CACHE.get('data')
    if cached and now - float(_BENCHMARK_CACHE.get('ts', 0.0)) < _BENCHMARK_TTL_SECONDS:
        return cached  # type: ignore[return-value]

    persisted = _read_cached_etf_quotes(_ETF_CACHE_MINUTES)
    if persisted:
        _BENCHMARK_CACHE['ts'] = now
        _BENCHMARK_CACHE['data'] = persisted
        return persisted

    names = {
        'SPY': 'S&P 500',
        'QQQ': 'Nasdaq 100',
        'VTI': 'Vanguard Total Market',
        'IWM': 'Russell 2000',
    }

    twelve_key = os.environ.get('TWELVE_DATA_API_KEY')
    if twelve_key:
        benchmarks = []
        try:
            for symbol in ['SPY', 'QQQ', 'VTI', 'IWM']:
                resp = requests.get(
                    'https://api.twelvedata.com/quote',
                    params={'symbol': symbol, 'apikey': twelve_key},
                    timeout=10,
                )
                resp.raise_for_status()
                payload = resp.json()
                if payload.get('code') or payload.get('status') == 'error':
                    raise RuntimeError(str(payload))

                close = payload.get('close')
                percent_change = payload.get('percent_change') or payload.get('change_percent')
                date_value = payload.get('datetime') or payload.get('timestamp')

                if close is None:
                    continue

                benchmarks.append(
                    {
                        'symbol': symbol,
                        'label': names[symbol],
                        'close': float(close),
                        'pct_change': float(percent_change) if percent_change is not None else 0.0,
                        'date': str(date_value).split(' ')[0] if date_value else None,
                        'source': 'twelve_data',
                    }
                )
        except Exception:
            benchmarks = []

        if benchmarks:
            _write_cached_etf_quotes(benchmarks)
            _BENCHMARK_CACHE['ts'] = now
            _BENCHMARK_CACHE['data'] = benchmarks
            return benchmarks

    try:
        symbols = ['SPY', 'QQQ', 'VTI', 'IWM']
        series_by_symbol = {}
        for symbol in symbols:
            history = yf.Ticker(symbol).history(period='10d', interval='1d', auto_adjust=False)
            if not history.empty and 'Close' in history.columns:
                series_by_symbol[symbol] = history['Close'].dropna()
    except Exception:
        return []

    if not series_by_symbol:
        return []

    benchmarks = []

    for symbol in ['SPY', 'QQQ', 'VTI', 'IWM']:
        close_series = series_by_symbol.get(symbol)
        if close_series is None or len(close_series) < 2:
            continue

        latest = float(close_series.iloc[-1])
        previous = float(close_series.iloc[-2])
        latest_ts = close_series.index[-1]
        pct_change = ((latest - previous) / previous) * 100 if previous else 0
        benchmarks.append(
            {
                'symbol': symbol,
                'label': names[symbol],
                'close': latest,
                'pct_change': float(pct_change),
                'date': str(pd.to_datetime(latest_ts).date()),
                'source': 'yfinance',
            }
        )

    if benchmarks:
        _write_cached_etf_quotes(benchmarks)
        _BENCHMARK_CACHE['ts'] = now
        _BENCHMARK_CACHE['data'] = benchmarks

    return benchmarks


def _get_proxy_benchmarks(conn: duckdb.DuckDBPyConnection, latest_date) -> list[dict]:
    rows = conn.execute(
        """
        WITH base AS (
          SELECT
            close,
            pct_change,
            CASE market_cap_tier
              WHEN 'mega' THEN 3
              WHEN 'large' THEN 2
              ELSE 1
            END AS weight
          FROM main_gold.mart_query_context
          WHERE date = ?
        )
        SELECT
          'SPY' AS symbol,
          'S&P 500' AS label,
          round(avg(close), 2) AS close,
          round(avg(pct_change), 2) AS pct_change
        FROM base

        UNION ALL

        SELECT
          'VTI' AS symbol,
          'Vanguard Total Market' AS label,
          round(sum(close * weight) / nullif(sum(weight), 0), 2) AS close,
          round(sum(pct_change * weight) / nullif(sum(weight), 0), 2) AS pct_change
        FROM base
        """,
        [latest_date],
    ).fetchall()

    return [
        {
            'symbol': row[0],
            'label': row[1],
            'close': float(row[2]) if row[2] is not None else None,
            'pct_change': float(row[3]) if row[3] is not None else 0,
            'date': str(latest_date),
            'source': 'warehouse_proxy',
        }
        for row in rows
    ]


def _get_header_ticker_strip() -> list[dict]:
    now = time.time()
    cached = _HEADER_TICKER_CACHE.get('data')
    if cached and now - float(_HEADER_TICKER_CACHE.get('ts', 0.0)) < _BENCHMARK_TTL_SECONDS:
        return cached  # type: ignore[return-value]

    symbols = [
        ('^IXIC', 'Nasdaq'),
        ('BTC-USD', 'BTC/USD'),
        ('GC=F', 'Gold'),
        ('AAPL', 'AAPL'),
        ('^GSPC', 'S&P 500'),
        ('^VIX', 'VIX'),
    ]

    items: list[dict] = []

    try:
        bulk_history = yf.download(
            [symbol for symbol, _label in symbols],
            period='5d',
            interval='1d',
            auto_adjust=False,
            progress=False,
            group_by='ticker',
            threads=False,
        )

        for symbol, label in symbols:
            try:
                if isinstance(bulk_history.columns, pd.MultiIndex):
                    if symbol not in bulk_history.columns.get_level_values(0):
                        continue
                    close_series = bulk_history[symbol]['Close'].dropna()
                else:
                    if symbol != symbols[0][0] or 'Close' not in bulk_history.columns:
                        continue
                    close_series = bulk_history['Close'].dropna()

                if len(close_series) < 2:
                    continue

                latest = float(close_series.iloc[-1])
                previous = float(close_series.iloc[-2])
                pct_change = ((latest - previous) / previous) * 100 if previous else 0.0
                latest_ts = close_series.index[-1]

                items.append(
                    {
                        'symbol': symbol,
                        'label': label,
                        'close': latest,
                        'pct_change': float(pct_change),
                        'date': str(pd.to_datetime(latest_ts).date()),
                        'source': 'yfinance',
                    }
                )
            except Exception:
                continue
    except Exception:
        items = []

    if items:
        _HEADER_TICKER_CACHE['ts'] = now
        _HEADER_TICKER_CACHE['data'] = items

    return items


def _market_news_query(symbol: str | None = None) -> str:
    base_query = os.environ.get(
        'BRAVE_NEWS_QUERY',
        'latest finance news stocks trading markets federal reserve earnings',
    ).strip()
    if symbol:
        return f'{symbol} stock trading finance news'
    return base_query


def _market_news_fallback_queries(symbol: str | None = None) -> list[str]:
    if symbol:
        raw_value = os.environ.get(
            'BRAVE_SYMBOL_NEWS_FALLBACK_QUERY',
            f'{symbol} business news earnings analyst rating markets',
        ).strip()
    else:
        raw_value = os.environ.get(
            'BRAVE_NEWS_FALLBACK_QUERY',
            'latest business news IPO AI economy big tech markets',
        ).strip()

    return [query.strip() for query in raw_value.split('||') if query.strip()]


def _story_timestamp(value: object) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=ZoneInfo('UTC'))
    try:
        normalized = str(value).replace('Z', '+00:00')
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo('UTC'))
        return parsed
    except ValueError:
        return datetime.min.replace(tzinfo=ZoneInfo('UTC'))


def _infer_story_symbol(title: str, summary: str) -> str | None:
    combined = f'{title} {summary}'
    symbol = _extract_symbol(combined)
    if symbol:
        return symbol

    lowered = combined.lower()
    for alias, mapped_symbol in _COMPANY_ALIASES.items():
        if alias in lowered:
            return mapped_symbol
    return None


def _format_story_source(item: dict) -> str:
    meta = item.get('meta_url')
    if isinstance(meta, dict):
        hostname = meta.get('hostname') or meta.get('netloc')
        if hostname:
            return str(hostname).replace('www.', '')

    provider = item.get('provider')
    if isinstance(provider, dict):
        provider_name = provider.get('name')
        if provider_name:
            return str(provider_name)

    url = item.get('url')
    if url:
        hostname = urlparse(str(url)).netloc.replace('www.', '')
        if hostname:
            return hostname

    return 'Brave News'


def _story_hostname(item: dict) -> str:
    meta = item.get('meta_url')
    if isinstance(meta, dict):
        hostname = meta.get('hostname') or meta.get('netloc')
        if hostname:
            return str(hostname).replace('www.', '').lower()

    url = item.get('url')
    if url:
        hostname = urlparse(str(url)).netloc.replace('www.', '').lower()
        if hostname:
            return hostname

    return ''


def _allowed_news_hosts() -> list[str]:
    raw_value = os.environ.get(
        'BRAVE_NEWS_ALLOWED_HOSTS',
        'reuters.com,apnews.com,bloomberg.com,cnbc.com,wsj.com,marketwatch.com,finance.yahoo.com,'
        'yahoo.com,barrons.com,investing.com,fool.com,businessinsider.com,seekingalpha.com,'
        'axios.com,cnn.com,nytimes.com,washingtonpost.com,forbes.com',
    ).strip()
    return [host.strip().lower() for host in raw_value.split(',') if host.strip()]


def _blocked_news_host_suffixes() -> list[str]:
    raw_value = os.environ.get(
        'BRAVE_NEWS_BLOCKED_HOST_SUFFIXES',
        '.in,.co.in,.co.uk,.uk,.com.au,.ca,.sg,.hk',
    ).strip()
    return [suffix.strip().lower() for suffix in raw_value.split(',') if suffix.strip()]


def _is_allowed_news_source(item: dict) -> bool:
    hostname = _story_hostname(item)
    if not hostname:
        return False

    blocked_suffixes = _blocked_news_host_suffixes()
    if any(hostname.endswith(suffix) for suffix in blocked_suffixes):
        return False

    allowed_hosts = _allowed_news_hosts()
    return any(hostname == host or hostname.endswith(f'.{host}') for host in allowed_hosts)


def _normalize_brave_story(item: dict, requested_symbol: str | None = None) -> dict | None:
    title = str(item.get('title') or '').strip()
    description = str(item.get('description') or item.get('snippet') or '').strip()
    extra_snippets = item.get('extra_snippets') or []
    if isinstance(extra_snippets, list):
        snippet_tail = ' '.join(str(snippet).strip() for snippet in extra_snippets[:2] if str(snippet).strip())
    else:
        snippet_tail = ''

    body_text = ' '.join(part for part in [description, snippet_tail] if part).strip()
    if not title:
        return None

    story_symbol = requested_symbol or _infer_story_symbol(title, body_text)
    publish_value = (
        item.get('page_age')
        or item.get('age')
        or item.get('published')
        or item.get('published_at')
        or item.get('date')
    )
    summary = description or snippet_tail or title

    return {
        'id': str(item.get('url') or f"{story_symbol or 'market'}-{publish_value}-{title}"),
        'symbol': story_symbol,
        'title': title,
        'summary': (summary[:220] + '...') if len(summary) > 220 else summary,
        'body_text': body_text or summary,
        'datetime': str(publish_value) if publish_value else None,
        'source': _format_story_source(item),
        'url': item.get('url'),
    }


def _run_news_query(question: str) -> dict:
    symbol = _extract_symbol(question)
    stories = _get_market_news(symbol=symbol)

    if symbol:
        symbol_stories = [story for story in stories if story.get('symbol') == symbol]
        if symbol_stories:
            stories = symbol_stories

    if not stories:
        commentary = (
            "I do not have any recent market stories available right now. "
            "Try again in a few minutes or ask about a specific company."
        )
        return {
            'question': question,
            'sql': 'news: no recent market stories available',
            'results': [],
            'path': 'news',
            'commentary': commentary,
        }

    top_stories = stories[:3]
    titles = '; '.join(story['title'] for story in top_stories[:2])
    scope_text = f"for {symbol}" if symbol else 'across the market'
    commentary = (
        f"The news flow {scope_text} is being led by {titles}. "
        f"The latest headline came from {top_stories[0]['source']} on {_format_central_time(top_stories[0]['datetime'])}."
    )
    return {
        'question': question,
        'sql': 'news: latest Brave News finance stories',
        'results': top_stories,
        'path': 'news',
        'commentary': commentary,
    }


def _fetch_brave_news_results(
    api_key: str,
    query: str,
    *,
    story_count: int,
    freshness: str,
    country: str,
    search_lang: str,
) -> list[dict]:
    response = requests.get(
        'https://api.search.brave.com/res/v1/news/search',
        headers={'X-Subscription-Token': api_key},
        params={
            'q': query,
            'count': story_count,
            'offset': 0,
            'freshness': freshness,
            'country': country,
            'search_lang': search_lang,
            'extra_snippets': 'true',
            'safesearch': 'moderate',
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get('results') or payload.get('items') or []
    return [item for item in items if isinstance(item, dict)]


def _get_market_news(symbol: str | None = None) -> list[dict]:
    now = time.time()
    cache_key = symbol or '__market__'
    cached_entry = _MARKET_NEWS_CACHE.get(cache_key)
    if cached_entry and now - float(cached_entry.get('ts', 0.0)) < _MARKET_NEWS_TTL_SECONDS:
        return cached_entry.get('data', [])  # type: ignore[return-value]

    api_key = os.environ.get('BRAVE_SEARCH_API_KEY', '').strip()
    if not api_key:
        return []

    story_count = max(1, min(int(os.environ.get('BRAVE_NEWS_COUNT', '10')), 10))
    freshness = os.environ.get('BRAVE_NEWS_FRESHNESS', 'pd').strip() or 'pd'
    country = os.environ.get('BRAVE_NEWS_COUNTRY', 'US').strip() or 'US'
    search_lang = os.environ.get('BRAVE_NEWS_SEARCH_LANG', 'en').strip() or 'en'

    stories: list[dict] = []
    seen_ids: set[str] = set()
    queries = [_market_news_query(symbol=symbol), *_market_news_fallback_queries(symbol=symbol)]
    for query in queries:
        items = _fetch_brave_news_results(
            api_key,
            query,
            story_count=story_count,
            freshness=freshness,
            country=country,
            search_lang=search_lang,
        )
        for item in items:
            if not _is_allowed_news_source(item):
                continue
            normalized = _normalize_brave_story(item, requested_symbol=symbol)
            if not normalized:
                continue
            story_id = str(normalized.get('id'))
            if story_id in seen_ids:
                continue
            seen_ids.add(story_id)
            stories.append(normalized)
            if len(stories) >= story_count:
                break
        if len(stories) >= story_count:
            break

    stories.sort(key=lambda item: _story_timestamp(item.get('datetime')), reverse=True)
    trimmed = stories[:story_count]
    _MARKET_NEWS_CACHE[cache_key] = {'ts': now, 'data': trimmed}
    return trimmed


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post('/query', response_model=QueryResponse)
async def run_query(req: QueryRequest, user_id: str | None = Depends(get_current_user_id)):
    """
    Translate a natural language question to SQL and execute it.

    Routes to the hot path (intraday.duckdb) when the question contains
    live/intraday keywords; otherwise routes to the cold path (Gold DuckDB).
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail='Question cannot be empty')

    if _is_conversational_query(req.question):
        result = _run_conversational_query(req.question)
        return QueryResponse(
            question=result['question'],
            sql=result['sql'],
            results=result['results'],
            path=result['path'],
            row_count=len(result['results']),
            commentary=result['commentary'],
        )

    if _is_news_query(req.question):
        try:
            result = _run_news_query(req.question)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))

        commentary = result.get('commentary') or generate_commentary(result['question'], result['results'])
        return QueryResponse(
            question=result['question'],
            sql=result['sql'],
            results=result['results'],
            path=result['path'],
            row_count=len(result['results']),
            commentary=commentary,
        )

    if _is_opinion_query(req.question):
        try:
            result = _run_opinion_query(req.question)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        commentary = result.get('commentary') or generate_commentary(result['question'], result['results'])
        return QueryResponse(
            question=result['question'],
            sql=result['sql'],
            results=result['results'],
            path=result['path'],
            row_count=len(result['results']),
            commentary=commentary,
        )

    route = _route_query(req.question)
    stripped_question = req.question.strip()
    hot_symbol = _extract_symbol(req.question)
    hot_tokens = stripped_question.replace('?', ' ').replace(',', ' ').split()

    try:
        if route == 'portfolio':
            result = _run_portfolio_query(req.question, user_id=user_id)
        elif route == 'hybrid':
            result = _run_hybrid_query(req.question)
        elif route == 'hot':
            if hot_symbol and len(hot_tokens) <= 3:
                result = _run_direct_hot_quote(req.question, hot_symbol)
            else:
                result = hot_query(req.question)
        else:
            if _is_watchlist_query(req.question):
                result = _run_watchlist_query(req.question, user_id=user_id)
            else:
                freshness = _get_duckdb_freshness()
                latest_date = freshness.get('latest_date')
                result = nl_query(req.question, DUCKDB_PATH, latest_date=latest_date)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except duckdb.Error as e:
        raise HTTPException(status_code=400, detail=f'SQL execution error: {e}')

    commentary = result.get('commentary') or generate_commentary(result['question'], result['results'])

    return QueryResponse(
        question=result['question'],
        sql=result['sql'],
        results=result['results'],
        path=result['path'],
        row_count=len(result['results']),
        commentary=commentary,
    )


@app.get('/health')
async def health():
    freshness = _get_duckdb_freshness()
    groq_configured = bool(os.environ.get('GROQ_API_KEY'))
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'duckdb_path': DUCKDB_PATH,
        'data': freshness,
        'groq_configured': groq_configured,
    }


@app.get('/schema')
async def schema():
    return {'ddl': MART_QUERY_CONTEXT_DDL}


@app.get('/anomalies')
async def anomalies():
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        rows = conn.execute("""
            SELECT symbol, company_name, sector, date,
                   close, pct_change, rsi_14, volume_zscore,
                   is_oversold, is_overbought, is_volume_spike, is_large_move
            FROM main_gold.mart_query_context
            WHERE date = (SELECT max(date) FROM main_gold.mart_query_context)
              AND (is_oversold OR is_overbought OR is_volume_spike OR is_large_move)
            ORDER BY symbol
        """).fetchall()
        conn.close()
        if not rows:
            return {'date': None, 'anomalies': []}
        columns = [
            'symbol', 'company_name', 'sector', 'date',
            'close', 'pct_change', 'rsi_14', 'volume_zscore',
            'is_oversold', 'is_overbought', 'is_volume_spike', 'is_large_move',
        ]
        result = [dict(zip(columns, row)) for row in rows]
        return {'date': str(result[0]['date']), 'anomalies': result}
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/stream-status')
async def stream_status():
    """Return live intraday stream health: bar count and latest bar timestamp."""
    return _get_intraday_status()


@app.get('/market-snapshot')
async def market_snapshot():
    """Return a dashboard snapshot derived from the latest Gold warehouse date."""
    try:
        conn = duckdb.connect(DUCKDB_PATH)

        latest_date_row = conn.execute(
            "SELECT max(date) FROM main_gold.mart_query_context"
        ).fetchone()
        latest_date = latest_date_row[0]

        if not latest_date:
            conn.close()
            return {
                'date': None,
                'benchmarks': [],
                'faang': [],
                'sector_cards': [],
                'leaders': [],
                'summary': {
                    'avg_pct_change': 0,
                    'avg_rsi': 0,
                    'ticker_count': 0,
                },
            }

        sector_rows = conn.execute(
            """
            SELECT sector, avg_rsi, avg_pct_change, ticker_count, top_gainer_symbol, top_loser_symbol
            FROM main_gold.agg_sector_daily
            WHERE date = ?
            ORDER BY
              CASE sector
                WHEN 'Technology' THEN 1
                WHEN 'Financials' THEN 2
                WHEN 'Energy' THEN 3
                WHEN 'Healthcare' THEN 4
                WHEN 'Consumer Discretionary' THEN 5
                ELSE 99
              END
            """,
            [latest_date],
        ).fetchall()

        leader_rows = conn.execute(
            """
            SELECT symbol, company_name, sector, close, pct_change, rsi_14, volume_zscore
            FROM main_gold.mart_query_context
            WHERE date = ?
            ORDER BY abs(pct_change) DESC, abs(volume_zscore) DESC
            LIMIT 4
            """,
            [latest_date],
        ).fetchall()

        daily_faang_rows = conn.execute(
            """
            SELECT symbol, company_name, sector, close, rsi_14, volume_zscore
            FROM main_gold.mart_query_context
            WHERE date = ?
              AND symbol IN ('AAPL', 'AMZN', 'GOOGL', 'META')
            """,
            [latest_date],
        ).fetchall()

        summary_row = conn.execute(
            """
            SELECT round(avg(pct_change), 2), round(avg(rsi_14), 2), count(*)
            FROM main_gold.mart_query_context
            WHERE date = ?
            """,
            [latest_date],
        ).fetchone()

        benchmarks = _get_benchmark_snapshot()
        if not benchmarks:
            benchmarks = _get_proxy_benchmarks(conn, latest_date)
        ticker_strip = _get_header_ticker_strip()

        conn.close()

        intraday_conn = duckdb.connect(INTRADAY_DUCKDB_PATH, read_only=True)
        try:
            live_faang_rows = intraday_conn.execute(
                """
                SELECT
                  symbol,
                  timestamp,
                  close,
                  row_number() OVER (PARTITION BY symbol ORDER BY timestamp DESC) AS rn
                FROM intraday_bars
                WHERE symbol IN ('AAPL', 'AMZN', 'GOOGL', 'META')
                """,
            ).fetchall()
        finally:
            intraday_conn.close()

        daily_map = {
            row[0]: {
                'company_name': row[1],
                'sector': row[2],
                'daily_close': float(row[3]) if row[3] is not None else None,
                'rsi_14': float(row[4]) if row[4] is not None else None,
                'volume_zscore': float(row[5]) if row[5] is not None else None,
            }
            for row in daily_faang_rows
        }

        faang_rows = []
        for row in live_faang_rows:
            symbol, _timestamp, live_close, rn = row
            if rn != 1 or symbol not in daily_map:
                continue
            daily = daily_map[symbol]
            daily_close = daily['daily_close']
            live_close_value = float(live_close) if live_close is not None else None
            pct_change = 0.0
            if live_close_value is not None and daily_close not in (None, 0):
                pct_change = round(((live_close_value - daily_close) / daily_close) * 100, 4)

            faang_rows.append(
                (
                    symbol,
                    daily['company_name'],
                    daily['sector'],
                    live_close_value,
                    pct_change,
                    daily['rsi_14'],
                    daily['volume_zscore'],
                )
            )

        faang_rows.sort(key=lambda row: abs(row[4]), reverse=True)

        return {
            'date': str(latest_date),
            'ticker_strip': ticker_strip,
            'benchmarks': benchmarks,
            'faang': [
                {
                    'symbol': row[0],
                    'company_name': row[1],
                    'sector': row[2],
                    'close': float(row[3]) if row[3] is not None else 0,
                    'pct_change': float(row[4]) if row[4] is not None else 0,
                    'rsi_14': float(row[5]) if row[5] is not None else None,
                    'volume_zscore': float(row[6]) if row[6] is not None else None,
                }
                for row in faang_rows
            ],
            'sector_cards': [
                {
                    'sector': row[0],
                    'avg_rsi': float(row[1]) if row[1] is not None else None,
                    'avg_pct_change': float(row[2]) if row[2] is not None else 0,
                    'ticker_count': int(row[3]) if row[3] is not None else 0,
                    'top_gainer_symbol': row[4],
                    'top_loser_symbol': row[5],
                }
                for row in sector_rows
            ],
            'leaders': [
                {
                    'symbol': row[0],
                    'company_name': row[1],
                    'sector': row[2],
                    'close': float(row[3]) if row[3] is not None else 0,
                    'pct_change': float(row[4]) if row[4] is not None else 0,
                    'rsi_14': float(row[5]) if row[5] is not None else None,
                    'volume_zscore': float(row[6]) if row[6] is not None else None,
                }
                for row in leader_rows
            ],
            'summary': {
                'avg_pct_change': float(summary_row[0]) if summary_row and summary_row[0] is not None else 0,
                'avg_rsi': float(summary_row[1]) if summary_row and summary_row[1] is not None else 0,
                'ticker_count': int(summary_row[2]) if summary_row and summary_row[2] is not None else 0,
            },
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/market-news')
async def market_news():
    """Return cached Brave News stories for the latest finance and trading flow."""
    try:
        news = _get_market_news()
        return {
            'stories': news,
            'count': len(news),
            'source': 'brave_news_search',
            'query': _market_news_query(),
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f'News fetch failed: {e}')


class HoldingIn(BaseModel):
    symbol: str
    shares: float
    avg_cost: float


class PortfolioRequest(BaseModel):
    holdings: list[HoldingIn]


class HoldingUpsert(BaseModel):
    symbol: str
    shares: float
    avg_cost: float


class WatchlistUpsert(BaseModel):
    symbol: str


class AlertPreferencesUpsert(BaseModel):
    concentration_alerts_enabled: bool | None = None
    concentration_threshold_pct: float | None = None
    rsi_alerts_enabled: bool | None = None
    overbought_rsi_threshold: float | None = None
    oversold_rsi_threshold: float | None = None
    daily_move_alerts_enabled: bool | None = None
    daily_move_threshold_pct: float | None = None
    telegram_daily_brief_enabled: bool | None = None
    telegram_alerts_enabled: bool | None = None


class TickerNoteUpsert(BaseModel):
    symbol: str
    note_text: str
    note_id: int | None = None
    note_type: str | None = 'note'
    note_title: str | None = None
    review_date: str | None = None


class TelegramLinkCompleteRequest(BaseModel):
    code: str
    chat_id: str
    telegram_username: str | None = None
    note_id: int | None = None


@app.on_event('startup')
async def startup() -> None:
    ensure_portfolio_tables()


@app.post('/portfolio')
async def portfolio(req: PortfolioRequest):
    """Calculate current portfolio value, P&L, and sector exposure."""
    try:
        result = calculate_portfolio([h.model_dump() for h in req.holdings])
        return result
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/portfolio')
async def saved_portfolio(user_id: str | None = Depends(get_current_user_id)):
    """Return the calculated portfolio summary for saved holdings."""
    try:
        return calculate_saved_portfolio(user_id=user_id)
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/portfolio/alerts')
async def get_portfolio_alerts(
    status: str | None = None,
    refresh: bool = False,
    user_id: str | None = Depends(get_current_user_id),
):
    """Return saved portfolio alerts, optionally regenerating them first."""
    try:
        alerts = refresh_portfolio_alerts(user_id=user_id) if refresh else list_portfolio_alerts(status=status, user_id=user_id)
        return {
            'alerts': alerts,
            'grouped_alerts': {
                'portfolio': [alert for alert in alerts if alert.get('source_scope', 'portfolio') == 'portfolio'],
                'watchlist': [alert for alert in alerts if alert.get('source_scope') == 'watchlist'],
            },
            'count': len(alerts),
            'telegram_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID')),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/portfolio/alert-preferences')
async def get_portfolio_alert_preferences(user_id: str | None = Depends(get_current_user_id)):
    """Return the saved alert preference profile."""
    try:
        return get_alert_preferences(user_id=user_id)
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.put('/portfolio/alert-preferences')
async def put_portfolio_alert_preferences(req: AlertPreferencesUpsert, user_id: str | None = Depends(get_current_user_id)):
    """Update the saved alert preference profile."""
    payload = {key: value for key, value in req.model_dump().items() if value is not None}

    if 'concentration_threshold_pct' in payload and payload['concentration_threshold_pct'] <= 0:
        raise HTTPException(status_code=400, detail='concentration_threshold_pct must be positive.')
    if 'overbought_rsi_threshold' in payload and not 0 <= payload['overbought_rsi_threshold'] <= 100:
        raise HTTPException(status_code=400, detail='overbought_rsi_threshold must be between 0 and 100.')
    if 'oversold_rsi_threshold' in payload and not 0 <= payload['oversold_rsi_threshold'] <= 100:
        raise HTTPException(status_code=400, detail='oversold_rsi_threshold must be between 0 and 100.')
    if 'daily_move_threshold_pct' in payload and payload['daily_move_threshold_pct'] <= 0:
        raise HTTPException(status_code=400, detail='daily_move_threshold_pct must be positive.')

    try:
        preferences = update_alert_preferences(payload, user_id=user_id)
        alerts = refresh_portfolio_alerts(user_id=user_id)
        return {
            'preferences': preferences,
            'alerts': alerts,
            'count': len(alerts),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.post('/portfolio/alerts/refresh')
async def refresh_saved_portfolio_alerts(user_id: str | None = Depends(get_current_user_id)):
    """Regenerate portfolio alerts from the latest holdings snapshot."""
    try:
        alerts = refresh_portfolio_alerts(user_id=user_id)
        return {'alerts': alerts, 'count': len(alerts)}
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/portfolio/brief')
async def get_portfolio_brief(user_id: str | None = Depends(get_current_user_id)):
    """Return a generated portfolio daily brief plus current alerts."""
    try:
        brief = build_portfolio_brief(user_id=user_id)
        return {
            **brief,
            'telegram_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID')),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/portfolio/watchlist')
async def get_watchlist(user_id: str | None = Depends(get_current_user_id)):
    """Return the saved watchlist and current warehouse snapshot."""
    try:
        return {
            'watchlist': list_watchlist(user_id=user_id),
            'snapshot': calculate_watchlist_snapshot(user_id=user_id),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/notes')
async def get_ticker_notes(symbol: str | None = None, user_id: str | None = Depends(get_current_user_id)):
    """Return saved ticker notes, optionally filtered by symbol."""
    try:
        notes = list_ticker_notes(symbol, user_id=user_id)
        grouped = {
            'thesis': [note for note in notes if note.get('note_type') == 'thesis'],
            'risk': [note for note in notes if note.get('note_type') == 'risk'],
            'exit': [note for note in notes if note.get('note_type') == 'exit'],
            'review': [note for note in notes if note.get('note_type') == 'review'],
            'note': [note for note in notes if note.get('note_type') == 'note'],
        }
        return {
            'notes': notes,
            'grouped_notes': grouped,
            'count': len(notes),
            'symbol': symbol.upper().strip() if symbol else None,
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.put('/notes')
async def put_ticker_note(req: TickerNoteUpsert, user_id: str | None = Depends(get_current_user_id)):
    """Create or update a saved ticker note."""
    if not req.symbol.strip():
        raise HTTPException(status_code=400, detail='Symbol cannot be empty.')
    if not req.note_text.strip():
        raise HTTPException(status_code=400, detail='Note text cannot be empty.')
    valid_types = {'thesis', 'risk', 'exit', 'review', 'note'}
    note_type = (req.note_type or 'note').strip().lower()
    if note_type not in valid_types:
        raise HTTPException(status_code=400, detail='note_type must be one of thesis, risk, exit, review, or note.')

    try:
        note = upsert_ticker_note(
            req.symbol,
            req.note_text,
            req.note_id,
            note_type=note_type,
            note_title=req.note_title,
            review_date=req.review_date,
            user_id=user_id,
        )
        notes = list_ticker_notes(user_id=user_id)
        return {
            'note': note,
            'notes': notes,
            'symbol': note['symbol'],
            'count': len(notes),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.delete('/notes/{note_id}')
async def remove_ticker_note(note_id: int, user_id: str | None = Depends(get_current_user_id)):
    """Delete a saved ticker note by note id."""
    try:
        deleted = delete_ticker_note(note_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f'No note found for id {note_id}.')
        return {
            'deleted_note_id': note_id,
            'notes': list_ticker_notes(user_id=user_id),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/telegram/link')
async def get_telegram_link(user_id: str | None = Depends(get_current_user_id)):
    """Return Telegram link status for the signed-in user."""
    if not user_id:
        return {'linked': False, 'pending_code': None}
    try:
        return get_telegram_link_status(user_id)
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.post('/telegram/link-code')
async def create_telegram_link(user_id: str | None = Depends(get_current_user_id)):
    """Generate a one-time Telegram link code for the signed-in user."""
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in to generate a Telegram link code.')
    try:
        return create_telegram_link_code(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.delete('/telegram/link')
async def delete_telegram_link(user_id: str | None = Depends(get_current_user_id)):
    """Remove the Telegram chat currently linked to the signed-in user."""
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in to manage Telegram links.')
    try:
        deleted = unlink_telegram_chat_for_user(user_id)
        return {
            'unlinked': deleted,
            'status': get_telegram_link_status(user_id),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.post('/telegram/link/complete')
async def complete_telegram_link_from_bot(
    req: TelegramLinkCompleteRequest,
    x_finsight_service_key: str | None = Header(default=None),
):
    """Link a Telegram chat to a Clerk user from the bot via a one-time code."""
    _require_internal_service_key(x_finsight_service_key)
    try:
        status = complete_telegram_link(req.code, req.chat_id, telegram_username=req.telegram_username)
        return {
            'linked': True,
            'status': status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/telegram/links')
async def get_telegram_links(x_finsight_service_key: str | None = Header(default=None)):
    """Return linked Telegram chats for internal scheduling."""
    _require_internal_service_key(x_finsight_service_key)
    try:
        return {
            'links': list_telegram_chat_links(),
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.put('/portfolio/watchlist')
async def put_watchlist(req: WatchlistUpsert, user_id: str | None = Depends(get_current_user_id)):
    """Upsert a watchlist symbol."""
    if not req.symbol.strip():
        raise HTTPException(status_code=400, detail='Symbol cannot be empty.')
    try:
        watch = upsert_watchlist_symbol(req.symbol, user_id=user_id)
        snapshot = calculate_watchlist_snapshot(user_id=user_id)
        alerts = refresh_portfolio_alerts(user_id=user_id)
        return {
            'watchlist_symbol': watch,
            'watchlist': list_watchlist(user_id=user_id),
            'snapshot': snapshot,
            'alerts': alerts,
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.delete('/portfolio/watchlist/{symbol}')
async def remove_watchlist(symbol: str, user_id: str | None = Depends(get_current_user_id)):
    """Delete a saved watchlist symbol."""
    try:
        deleted = delete_watchlist_symbol(symbol, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f'No watchlist symbol found for {symbol.upper()}.')
        snapshot = calculate_watchlist_snapshot(user_id=user_id)
        alerts = refresh_portfolio_alerts(user_id=user_id)
        return {
            'deleted': symbol.upper(),
            'watchlist': list_watchlist(user_id=user_id),
            'snapshot': snapshot,
            'alerts': alerts,
        }
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.post('/portfolio/brief/send-telegram')
async def send_portfolio_brief_to_telegram(
    scheduled: bool = False,
    user_id: str | None = Depends(get_current_user_id),
):
    """Send the current portfolio brief to the configured Telegram chat."""
    try:
        brief = build_portfolio_brief(user_id=user_id)
        preferences = brief.get('preferences') or get_alert_preferences(user_id=user_id)
        if not preferences.get('telegram_daily_brief_enabled', True):
            return {
                'sent': False,
                'scheduled': scheduled,
                'reason': 'disabled_in_preferences',
                'as_of_date': brief.get('as_of_date'),
                'alert_count': len(brief.get('alerts', [])),
            }

        delivery_key = 'telegram_daily_brief'
        send_date = current_central_date()
        if scheduled and not should_send_delivery(delivery_key, send_date, user_id=user_id):
            return {
                'sent': False,
                'scheduled': True,
                'reason': 'already_sent_today',
                'send_date': send_date,
                'as_of_date': brief.get('as_of_date'),
                'alert_count': len(brief.get('alerts', [])),
            }

        message = _format_portfolio_brief_message(brief)
        telegram_link = get_telegram_link_status(user_id) if user_id else {'linked': False}
        telegram_chat_id = telegram_link.get('chat_id') if telegram_link.get('linked') else None
        if user_id and not telegram_chat_id:
            raise RuntimeError('Link a Telegram chat to this account before sending a brief.')

        _send_telegram_message(message, chat_id=telegram_chat_id)
        alert_ids = [alert['alert_id'] for alert in brief.get('alerts', [])]
        mark_alerts_sent(alert_ids, user_id=user_id)
        if scheduled:
            mark_delivery_sent(delivery_key, sent_date=send_date, user_id=user_id)
        return {
            'sent': True,
            'scheduled': scheduled,
            'send_date': send_date,
            'as_of_date': brief.get('as_of_date'),
            'alert_count': len(alert_ids),
            'telegram_chat_id': telegram_chat_id,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f'Telegram send failed: {e}')
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.get('/portfolio/holdings')
async def get_holdings(user_id: str | None = Depends(get_current_user_id)):
    """Return the saved portfolio holdings."""
    try:
        return {'holdings': list_holdings(user_id=user_id)}
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.put('/portfolio/holdings')
async def put_holding(req: HoldingUpsert, user_id: str | None = Depends(get_current_user_id)):
    """Upsert a saved holding."""
    if not req.symbol.strip():
        raise HTTPException(status_code=400, detail='Symbol cannot be empty.')
    if req.shares <= 0 or req.avg_cost <= 0:
        raise HTTPException(status_code=400, detail='Shares and average cost must be positive.')

    try:
        holding = upsert_holding(req.symbol, req.shares, req.avg_cost, user_id=user_id)
        return {'holding': holding, 'portfolio': calculate_saved_portfolio(user_id=user_id)}
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')


@app.delete('/portfolio/holdings/{symbol}')
async def remove_holding(symbol: str, user_id: str | None = Depends(get_current_user_id)):
    """Delete a saved holding by symbol."""
    try:
        deleted = delete_holding(symbol, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f'No holding found for {symbol.upper()}.')
        return {'deleted': symbol.upper(), 'portfolio': calculate_saved_portfolio(user_id=user_id)}
    except duckdb.Error as e:
        raise HTTPException(status_code=503, detail=f'DuckDB error: {e}')
