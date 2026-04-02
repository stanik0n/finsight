import os
import time
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import requests


BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
API_BASE = os.environ.get('FINSIGHT_API_URL', 'http://api:8000').rstrip('/')
INTERNAL_API_KEY = os.environ.get('FINSIGHT_INTERNAL_API_KEY', '').strip()
POLL_TIMEOUT_SECONDS = int(os.environ.get('TELEGRAM_POLL_TIMEOUT_SECONDS', '30'))
DAILY_BRIEF_SCHEDULE_ENABLED = os.environ.get('TELEGRAM_DAILY_BRIEF_SCHEDULE_ENABLED', 'true').lower() == 'true'
DAILY_BRIEF_HOUR_CT = int(os.environ.get('TELEGRAM_DAILY_BRIEF_HOUR_CT', '8'))
DAILY_BRIEF_MINUTE_CT = int(os.environ.get('TELEGRAM_DAILY_BRIEF_MINUTE_CT', '0'))
_CENTRAL_TZ = ZoneInfo('America/Chicago')
SMALL_TALK_INPUTS = {
    'hi',
    'hey',
    'hello',
    'yo',
    'sup',
    'whats up',
    "what's up",
    'how are you',
    'how r you',
    'good morning',
    'good afternoon',
    'good evening',
    'thanks',
    'thank you',
}
TRACKED_SYMBOLS = {
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA', 'AMD', 'INTC', 'CRM',
    'JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'BLK', 'AXP', 'USB', 'COF',
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'MPC', 'VLO', 'OXY', 'HAL',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN',
    'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'BKNG', 'MAR', 'COST',
}
COMPANY_ALIASES = {
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


def telegram_api(method: str, **payload):
    if not BOT_TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured.')

    resp = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',
        json=payload,
        timeout=POLL_TIMEOUT_SECONDS + 10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get('ok'):
        raise RuntimeError(f'Telegram API error: {data}')
    return data


def send_message(chat_id: int | str, text: str) -> None:
    telegram_api(
        'sendMessage',
        chat_id=chat_id,
        text=text,
        parse_mode='HTML',
        disable_web_page_preview=True,
    )


def _api_headers() -> dict:
    return {'X-Finsight-Service-Key': INTERNAL_API_KEY} if INTERNAL_API_KEY else {}


def api_get(path: str) -> dict:
    resp = requests.get(f'{API_BASE}{path}', headers=_api_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, payload: dict | None = None) -> dict:
    resp = requests.post(f'{API_BASE}{path}', headers=_api_headers(), json=payload or {}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def api_put(path: str, payload: dict | None = None) -> dict:
    resp = requests.put(f'{API_BASE}{path}', headers=_api_headers(), json=payload or {}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def api_delete(path: str) -> dict:
    resp = requests.delete(f'{API_BASE}{path}', headers=_api_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


def format_brief_response(data: dict) -> str:
    summary = escape(data.get('summary', 'No portfolio summary available.'))
    alerts = data.get('alerts', [])
    watchlist = data.get('watchlist', {}) or {}
    watchlist_items = watchlist.get('items', []) or []
    date_value = data.get('as_of_date') or 'n/a'
    lines = [f'<b>FinSight Brief - {date_value}</b>', '', summary]

    if watchlist_items:
        lines.extend(['', '<b>Watchlist:</b>'])
        for item in watchlist_items[:3]:
            change = item.get('daily_pct_change')
            change_text = f" | {change:+.2f}%" if change is not None else ''
            lines.append(
                f"- <b>{escape(item['symbol'])}</b> - ${item['current_price']:.2f}{change_text}"
            )

    if alerts:
        lines.extend(['', f'<b>Alerts ({len(alerts)}):</b>'])
        for alert in alerts[:5]:
            lines.append(f"- <b>{escape(alert['title'])}</b> - {escape(alert['message'])}")
    return '\n'.join(lines)


def format_alerts_response(data: dict) -> str:
    alerts = data.get('alerts', [])
    if not alerts:
        return '<b>FinSight Alerts</b>\n\nNo active alerts right now.'

    lines = [f"<b>FinSight Alerts ({len(alerts)})</b>", '']
    for alert in alerts[:8]:
        symbol = f" [{escape(alert['symbol'])}]" if alert.get('symbol') else ''
        lines.append(f"- <b>{escape(alert['title'])}</b>{symbol}\n  {escape(alert['message'])}")
    return '\n'.join(lines)


def format_watchlist_response(data: dict) -> str:
    snapshot = data.get('snapshot', {}) or {}
    items = snapshot.get('items', []) or []
    if not items:
        return '<b>FinSight Watchlist</b>\n\nNo saved watchlist names yet.'

    lines = [f"<b>FinSight Watchlist - {snapshot.get('as_of_date') or 'n/a'}</b>", '']
    for item in items[:8]:
        change = item.get('daily_pct_change')
        change_text = f" | {change:+.2f}%" if change is not None else ''
        lines.append(
            f"- <b>{escape(item['symbol'])}</b> - ${item['current_price']:.2f}{change_text}\n"
            f"  {escape(item.get('company_name') or 'Tracked name')}"
        )
    return '\n'.join(lines)


def format_watchlist_alerts_response(data: dict) -> str:
    alerts = (data.get('grouped_alerts') or {}).get('watchlist') or []
    if not alerts:
        return '<b>FinSight Watchlist Alerts</b>\n\nNo active watchlist alerts right now.'

    lines = [f"<b>FinSight Watchlist Alerts ({len(alerts)})</b>", '']
    for alert in alerts[:8]:
        symbol = f" [{escape(alert['symbol'])}]" if alert.get('symbol') else ''
        lines.append(f"- <b>{escape(alert['title'])}</b>{symbol}\n  {escape(alert['message'])}")
    return '\n'.join(lines)


def format_holding_update_response(data: dict, action: str, symbol: str) -> str:
    portfolio = data.get('portfolio', {}) or {}
    positions = portfolio.get('positions', []) or []
    position_count = len(positions)
    total_value = portfolio.get('total_value', 0)
    total_pnl = portfolio.get('total_pnl', 0)
    return (
        f"<b>Portfolio updated</b>\n\n"
        f"{action} <b>{escape(symbol)}</b> in your tracked portfolio.\n\n"
        f"Positions: {position_count}\n"
        f"Value: ${total_value:,.2f}\n"
        f"Unrealized P&L: {total_pnl:+,.2f}"
    )


def format_portfolio_response(data: dict) -> str:
    if not data.get('positions'):
        return '<b>FinSight Portfolio</b>\n\nNo saved holdings yet.'

    lines = [
        f"<b>FinSight Portfolio - {data.get('as_of_date') or 'n/a'}</b>",
        '',
        f"Value: ${data['total_value']:,.2f}",
        f"Unrealized P&L: {data['total_pnl']:+,.2f} ({data['total_pnl_pct']:+.2f}%)",
        '',
        '<b>Top holdings:</b>',
    ]
    for position in data.get('positions', [])[:5]:
        lines.append(
            f"- {escape(position['symbol'])}: ${position['current_price']:.2f} | "
            f"{position['shares']:.2f} shares | {position['pnl_pct']:+.2f}%"
        )
    return '\n'.join(lines)


def format_notes_response(data: dict, symbol: str | None = None) -> str:
    notes = data.get('notes', []) or []
    header_symbol = symbol or data.get('symbol')
    if not notes:
        if header_symbol:
            return f"<b>FinSight Notes - {escape(header_symbol)}</b>\n\nNo saved notes yet for this ticker."
        return '<b>FinSight Notes</b>\n\nNo saved notes yet.'

    title = f"<b>FinSight Notes - {escape(header_symbol)}</b>" if header_symbol else '<b>FinSight Notes</b>'
    lines = [title, '']
    for note in notes[:8]:
        lines.append(
            f"- <b>{escape(note['symbol'])}</b>: {escape(note['note_text'])}"
        )
    return '\n'.join(lines)


def format_query_response(data: dict) -> str:
    commentary = escape(data.get('commentary') or 'No commentary available.')
    path = escape(data.get('path', 'n/a').upper())
    return f"<b>FinSight Analyst</b>\n<i>Route: {path}</i>\n\n{commentary}"


def help_text() -> str:
    return (
        "<b>FinSight Telegram Commands</b>\n\n"
        "/brief - portfolio daily brief\n"
        "/alerts - current portfolio alerts\n"
        "/portfolio - holdings snapshot\n"
        "/addholding [ticker] [shares] [avg_cost] - update a tracked holding\n"
        "/removeholding [ticker] - remove a tracked holding\n"
        "/notes [ticker] - show saved notes for a ticker\n"
        "/note [ticker] [text] - save a ticker note\n"
        "/watchlist - tracked names snapshot\n"
        "/watchalerts - current watchlist alerts\n"
        "/watchadd [ticker] - add a ticker to your watchlist\n"
        "/watchremove [ticker] - remove a ticker from your watchlist\n"
        "/ask [question] - ask the analyst\n"
        "\n<b>Plain English works too</b>\n"
        "show my watchlist\n"
        "any watchlist alerts\n"
        "add NVDA to my watchlist\n"
        "remove TSLA from my watchlist\n"
        "add 10 shares of AAPL at 150 to my portfolio\n"
        "remove NVDA from my portfolio\n"
        "note on NVDA: trim if concentration stays too high\n"
        "how is my portfolio\n"
        "do you think tesla will go up tomorrow\n"
    )


def small_talk_response(text: str) -> str | None:
    normalized = ' '.join(text.lower().strip().split())
    if normalized not in SMALL_TALK_INPUTS:
        return None

    if normalized in {'thanks', 'thank you'}:
        return "Anytime. Ask me about your portfolio, watchlist, alerts, live prices, or tomorrow's setup."

    if normalized in {'how are you', 'how r you'}:
        return "Running well. Ask me about your portfolio, watchlist, alerts, live prices, or a stock you're watching."

    return (
        "Hey - I'm FinSight.\n\n"
        "Try:\n"
        "/brief\n"
        "/addholding NVDA 5 120\n"
        "/watchlist\n"
        "show my watchlist\n"
        "add NVDA to my watchlist\n"
        "how is my portfolio"
    )


def _extract_symbol(text: str) -> str | None:
    lowered = text.lower()
    for alias, symbol in COMPANY_ALIASES.items():
        if alias in lowered:
            return symbol

    tokens = [token.strip(" ?!.,:;'\"()[]{}").upper() for token in text.split()]
    ignored = {
        'ADD', 'REMOVE', 'DELETE', 'DROP', 'WATCHLIST', 'WATCH', 'MY', 'SHOW', 'ANY',
        'ALERTS', 'ON', 'TO', 'FROM', 'TRACK', 'TRACKING', 'SHARES', 'SHARE',
        'PORTFOLIO', 'AT', 'OF', 'HAD', 'I', 'HAVE',
    }
    for token in tokens:
        if token in TRACKED_SYMBOLS:
            return token
    return None


def _extract_holding_update(text: str) -> dict | None:
    normalized = ' '.join(text.lower().strip().split())
    tokens = [token.strip(" ?!.,:;'\"()[]{}") for token in text.split()]
    mentions_portfolio = 'portfolio' in normalized or 'holding' in normalized or 'position' in normalized

    symbol = _extract_symbol(text)
    numbers = []
    for token in tokens:
        try:
            numbers.append(float(token.replace('$', '')))
        except ValueError:
            continue

    if (
        normalized.startswith(('addholding ', 'setholding ', 'buy '))
        or 'add ' in normalized
        or 'buy ' in normalized
        or (mentions_portfolio and symbol and len(numbers) >= 2 and 'remove' not in normalized and 'delete' not in normalized and 'drop' not in normalized)
    ):
        if symbol and len(numbers) >= 2:
            return {
                'action': 'add',
                'symbol': symbol,
                'shares': numbers[0],
                'avg_cost': numbers[1],
            }

    if normalized.startswith(('removeholding ', 'sell ')) or any(phrase in normalized for phrase in ['remove ', 'delete ', 'drop ']):
        if symbol and 'watchlist' not in normalized:
            return {
                'action': 'remove',
                'symbol': symbol,
            }

    return None


def handle_watchlist_message(chat_id: int | str, text: str) -> bool:
    normalized = ' '.join(text.lower().strip().split())

    if normalized in {'show my watchlist', 'my watchlist', 'watchlist', 'show watchlist'}:
        send_message(chat_id, format_watchlist_response(api_get('/portfolio/watchlist')))
        return True

    if normalized in {'any watchlist alerts', 'watchlist alerts', 'show watchlist alerts', 'alerts on my watchlist'}:
        send_message(chat_id, format_watchlist_alerts_response(api_get('/portfolio/alerts?refresh=true')))
        return True

    symbol = _extract_symbol(text)
    if symbol and 'watchlist' in normalized:
        if any(word in normalized for word in {'remove', 'delete', 'drop'}):
            payload = api_delete(f'/portfolio/watchlist/{symbol}')
            send_message(
                chat_id,
                f"<b>Watchlist updated</b>\n\nRemoved <b>{escape(symbol)}</b> from your tracked names.\n\n{format_watchlist_response(payload)}",
            )
            return True

        if any(word in normalized for word in {'add', 'track', 'watch'}):
            payload = api_put('/portfolio/watchlist', {'symbol': symbol})
            send_message(
                chat_id,
                f"<b>Watchlist updated</b>\n\nAdded <b>{escape(symbol)}</b> to your tracked names.\n\n{format_watchlist_response(payload)}",
            )
            return True

    return False


def handle_note_message(chat_id: int | str, text: str) -> bool:
    normalized = ' '.join(text.lower().strip().split())

    if normalized.startswith('note on ') and ':' in text:
        before, note_text = text.split(':', 1)
        symbol = _extract_symbol(before)
        if symbol and note_text.strip():
            payload = api_put('/notes', {'symbol': symbol, 'note_text': note_text.strip()})
            send_message(
                chat_id,
                f"<b>Research note saved</b>\n\nSaved a note for <b>{escape(symbol)}</b>.\n\n{format_notes_response(payload, symbol)}",
            )
            return True

    if normalized.startswith('show notes on ') or normalized.startswith('show notes for '):
        symbol = _extract_symbol(text)
        if symbol:
            send_message(chat_id, format_notes_response(api_get(f'/notes?symbol={symbol}'), symbol))
            return True

    return False


def handle_command(chat_id: int | str, text: str) -> None:
    command = text.strip()
    lowered = command.lower()
    command_name = lowered.split()[0] if lowered else ''
    command_root = command_name.split('@')[0] if command_name else ''

    try:
        if command_root == '/start':
            send_message(chat_id, help_text())
            return

        if command_root == '/brief':
            send_message(chat_id, format_brief_response(api_get('/portfolio/brief')))
            return

        if command_root == '/alerts':
            send_message(chat_id, format_alerts_response(api_get('/portfolio/alerts?refresh=true')))
            return

        if command_root == '/portfolio':
            send_message(chat_id, format_portfolio_response(api_get('/portfolio')))
            return

        if command_root == '/addholding':
            parts = command.split()
            if len(parts) < 4:
                send_message(chat_id, 'Use /addholding SYMBOL SHARES AVG_COST, for example: /addholding NVDA 5 120')
                return
            symbol = _extract_symbol(parts[1]) or parts[1].upper()
            shares = float(parts[2])
            avg_cost = float(parts[3])
            payload = api_put('/portfolio/holdings', {'symbol': symbol, 'shares': shares, 'avg_cost': avg_cost})
            send_message(chat_id, format_holding_update_response(payload, 'Updated', symbol))
            return

        if command_root == '/removeholding':
            parts = command.split()
            if len(parts) < 2:
                send_message(chat_id, 'Use /removeholding SYMBOL, for example: /removeholding TSLA')
                return
            symbol = _extract_symbol(parts[1]) or parts[1].upper()
            payload = api_delete(f'/portfolio/holdings/{symbol}')
            send_message(chat_id, format_holding_update_response(payload, 'Removed', symbol))
            return

        if command_root == '/notes':
            parts = command.split(maxsplit=1)
            if len(parts) == 1:
                send_message(chat_id, format_notes_response(api_get('/notes')))
                return
            symbol = _extract_symbol(parts[1]) or parts[1].strip().upper()
            send_message(chat_id, format_notes_response(api_get(f'/notes?symbol={symbol}'), symbol))
            return

        if command_root == '/note':
            parts = command.split(maxsplit=2)
            if len(parts) < 3:
                send_message(chat_id, 'Use /note SYMBOL your note text, for example: /note NVDA trim if concentration stays too high')
                return
            symbol = _extract_symbol(parts[1]) or parts[1].strip().upper()
            payload = api_put('/notes', {'symbol': symbol, 'note_text': parts[2].strip()})
            send_message(
                chat_id,
                f"<b>Research note saved</b>\n\nSaved a note for <b>{escape(symbol)}</b>.\n\n{format_notes_response(payload, symbol)}",
            )
            return

        if command_root == '/watchlist':
            send_message(chat_id, format_watchlist_response(api_get('/portfolio/watchlist')))
            return

        if command_root == '/watchalerts':
            send_message(chat_id, format_watchlist_alerts_response(api_get('/portfolio/alerts?refresh=true')))
            return

        if command_root == '/watchadd':
            symbol = _extract_symbol(command[len(command.split()[0]):].strip())
            if not symbol:
                send_message(chat_id, 'Use /watchadd followed by a ticker, for example: /watchadd NVDA')
                return
            payload = api_put('/portfolio/watchlist', {'symbol': symbol})
            send_message(
                chat_id,
                f"<b>Watchlist updated</b>\n\nAdded <b>{escape(symbol)}</b> to your tracked names.\n\n{format_watchlist_response(payload)}",
            )
            return

        if command_root == '/watchremove':
            symbol = _extract_symbol(command[len(command.split()[0]):].strip())
            if not symbol:
                send_message(chat_id, 'Use /watchremove followed by a ticker, for example: /watchremove TSLA')
                return
            payload = api_delete(f'/portfolio/watchlist/{symbol}')
            send_message(
                chat_id,
                f"<b>Watchlist updated</b>\n\nRemoved <b>{escape(symbol)}</b> from your tracked names.\n\n{format_watchlist_response(payload)}",
            )
            return

        if command_root == '/ask':
            question = command[len(command.split()[0]):].strip()
            if not question:
                send_message(chat_id, 'Use /ask followed by a question, for example: /ask is NVDA bullish right now')
                return
            send_message(chat_id, format_query_response(api_post('/query', {'question': question})))
            return

        if command.startswith('/'):
            send_message(chat_id, help_text())
            return

        chat_reply = small_talk_response(command)
        if chat_reply:
            send_message(chat_id, chat_reply)
            return

        holding_update = _extract_holding_update(command)
        if holding_update:
            if holding_update['action'] == 'add':
                payload = api_put(
                    '/portfolio/holdings',
                    {
                        'symbol': holding_update['symbol'],
                        'shares': holding_update['shares'],
                        'avg_cost': holding_update['avg_cost'],
                    },
                )
                send_message(chat_id, format_holding_update_response(payload, 'Updated', holding_update['symbol']))
                return
            if holding_update['action'] == 'remove':
                payload = api_delete(f"/portfolio/holdings/{holding_update['symbol']}")
                send_message(chat_id, format_holding_update_response(payload, 'Removed', holding_update['symbol']))
                return

        if handle_watchlist_message(chat_id, command):
            return

        if handle_note_message(chat_id, command):
            return

        send_message(chat_id, format_query_response(api_post('/query', {'question': command})))
    except requests.RequestException as exc:
        print(f'[telegram_bot] Backend/request error for "{text}": {exc}')
        send_message(chat_id, f'FinSight could not complete that command right now: {escape(str(exc))}')
    except Exception as exc:
        print(f'[telegram_bot] Command failed for "{text}": {exc}')
        send_message(chat_id, f'FinSight command failed: {escape(str(exc))}')


def maybe_send_scheduled_brief(last_schedule_tick: str | None) -> str | None:
    if not DAILY_BRIEF_SCHEDULE_ENABLED:
        return last_schedule_tick

    now_ct = datetime.now(_CENTRAL_TZ)
    tick = now_ct.strftime('%Y-%m-%d %H:%M')
    if tick == last_schedule_tick:
        return last_schedule_tick

    scheduled_time_reached = (
        now_ct.hour > DAILY_BRIEF_HOUR_CT or
        (now_ct.hour == DAILY_BRIEF_HOUR_CT and now_ct.minute >= DAILY_BRIEF_MINUTE_CT)
    )
    if not scheduled_time_reached:
        return last_schedule_tick

    try:
        payload = api_post('/portfolio/brief/send-telegram?scheduled=true')
        if payload.get('sent'):
            print(
                '[telegram_bot] Scheduled daily brief sent '
                f"for {payload.get('send_date')} with {payload.get('alert_count', 0)} alerts."
            )
        elif payload.get('reason') not in {'already_sent_today', 'disabled_in_preferences'}:
            print(f'[telegram_bot] Scheduled daily brief skipped: {payload}')
    except Exception as exc:
        print(f'[telegram_bot] Scheduled brief error: {exc}')

    return tick


def main() -> None:
    if not BOT_TOKEN:
        print('[telegram_bot] TELEGRAM_BOT_TOKEN not configured; exiting.')
        return

    offset = None
    last_schedule_tick = None
    print('[telegram_bot] Polling Telegram for commands...')
    while True:
        try:
            last_schedule_tick = maybe_send_scheduled_brief(last_schedule_tick)
            payload = {'timeout': POLL_TIMEOUT_SECONDS}
            if offset is not None:
                payload['offset'] = offset
            data = telegram_api('getUpdates', **payload)
            for update in data.get('result', []):
                offset = update['update_id'] + 1
                message = update.get('message') or {}
                text = (message.get('text') or '').strip()
                chat = message.get('chat') or {}
                chat_id = chat.get('id')
                if chat_id and text:
                    handle_command(chat_id, text)
        except Exception as exc:
            print(f'[telegram_bot] Polling error: {exc}')
            time.sleep(5)


if __name__ == '__main__':
    main()
