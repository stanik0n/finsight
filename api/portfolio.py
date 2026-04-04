"""
Portfolio storage and calculation helpers.

Provides:
- persistent saved holdings in DuckDB
- persistent saved watchlist symbols
- persistent ticker notes and thesis snippets
- CRUD helpers for holdings
- portfolio valuation against the latest Gold warehouse prices
- generated portfolio alerts and brief summaries
"""

import json
import os
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import duckdb

DUCKDB_PATH = os.environ.get('DUCKDB_PATH', '/data/finsight.duckdb')
DEFAULT_ALERT_PREFERENCES = {
    'concentration_alerts_enabled': True,
    'concentration_threshold_pct': 40.0,
    'rsi_alerts_enabled': True,
    'overbought_rsi_threshold': 70.0,
    'oversold_rsi_threshold': 30.0,
    'daily_move_alerts_enabled': True,
    'daily_move_threshold_pct': 3.0,
    'telegram_daily_brief_enabled': True,
    'telegram_alerts_enabled': True,
}
_CENTRAL_TZ = ZoneInfo('America/Chicago')
_DEFAULT_PROFILE_ID = 1
_TELEGRAM_LINK_CODE_TTL_MINUTES = int(os.environ.get('TELEGRAM_LINK_CODE_TTL_MINUTES', '15'))


def _normalize_user_id(user_id: str | None) -> str | None:
    cleaned = (user_id or '').strip()
    return cleaned or None


def _using_user_scope(user_id: str | None) -> bool:
    return _normalize_user_id(user_id) is not None


def _connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DUCKDB_PATH, read_only=read_only)


def ensure_portfolio_tables() -> None:
    conn = _connect()
    try:
        conn.execute("CREATE SCHEMA IF NOT EXISTS app")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.portfolio_holdings (
                symbol TEXT PRIMARY KEY,
                shares DOUBLE NOT NULL,
                avg_cost DOUBLE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.portfolio_watchlist (
                symbol TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.portfolio_alerts (
                alert_id TEXT PRIMARY KEY,
                symbol TEXT,
                source_scope TEXT DEFAULT 'portfolio',
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                payload_json TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                sent_to_telegram_at TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.portfolio_alert_preferences (
                profile_id INTEGER PRIMARY KEY,
                concentration_alerts_enabled BOOLEAN NOT NULL,
                concentration_threshold_pct DOUBLE NOT NULL,
                rsi_alerts_enabled BOOLEAN NOT NULL,
                overbought_rsi_threshold DOUBLE NOT NULL,
                oversold_rsi_threshold DOUBLE NOT NULL,
                daily_move_alerts_enabled BOOLEAN NOT NULL,
                daily_move_threshold_pct DOUBLE NOT NULL,
                telegram_daily_brief_enabled BOOLEAN NOT NULL,
                telegram_alerts_enabled BOOLEAN NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.portfolio_delivery_state (
                delivery_key TEXT PRIMARY KEY,
                last_sent_date TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.ticker_notes (
                note_id BIGINT PRIMARY KEY,
                symbol TEXT NOT NULL,
                note_type TEXT DEFAULT 'note',
                note_title TEXT,
                note_text TEXT NOT NULL,
                review_date DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.user_portfolio_holdings (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                shares DOUBLE NOT NULL,
                avg_cost DOUBLE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, symbol)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.user_portfolio_watchlist (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, symbol)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.user_portfolio_alerts (
                user_id TEXT NOT NULL,
                alert_id TEXT NOT NULL,
                symbol TEXT,
                source_scope TEXT DEFAULT 'portfolio',
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                payload_json TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                sent_to_telegram_at TIMESTAMP,
                PRIMARY KEY (user_id, alert_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.user_portfolio_alert_preferences (
                user_id TEXT PRIMARY KEY,
                concentration_alerts_enabled BOOLEAN NOT NULL,
                concentration_threshold_pct DOUBLE NOT NULL,
                rsi_alerts_enabled BOOLEAN NOT NULL,
                overbought_rsi_threshold DOUBLE NOT NULL,
                oversold_rsi_threshold DOUBLE NOT NULL,
                daily_move_alerts_enabled BOOLEAN NOT NULL,
                daily_move_threshold_pct DOUBLE NOT NULL,
                telegram_daily_brief_enabled BOOLEAN NOT NULL,
                telegram_alerts_enabled BOOLEAN NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.user_portfolio_delivery_state (
                user_id TEXT NOT NULL,
                delivery_key TEXT NOT NULL,
                last_sent_date TEXT,
                updated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, delivery_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.user_ticker_notes (
                user_id TEXT NOT NULL,
                note_id BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                note_type TEXT DEFAULT 'note',
                note_title TEXT,
                note_text TEXT NOT NULL,
                review_date DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, note_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.telegram_chat_links (
                user_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL UNIQUE,
                telegram_username TEXT,
                linked_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app.telegram_link_codes (
                code TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        conn.execute("ALTER TABLE app.portfolio_alerts ADD COLUMN IF NOT EXISTS source_scope TEXT DEFAULT 'portfolio'")
        conn.execute("ALTER TABLE app.ticker_notes ADD COLUMN IF NOT EXISTS note_type TEXT DEFAULT 'note'")
        conn.execute("ALTER TABLE app.ticker_notes ADD COLUMN IF NOT EXISTS note_title TEXT")
        conn.execute("ALTER TABLE app.ticker_notes ADD COLUMN IF NOT EXISTS review_date DATE")
        conn.execute("ALTER TABLE app.user_portfolio_holdings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_portfolio_holdings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_portfolio_watchlist ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_portfolio_watchlist ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_portfolio_alerts ADD COLUMN IF NOT EXISTS source_scope TEXT DEFAULT 'portfolio'")
        conn.execute("ALTER TABLE app.user_portfolio_alert_preferences ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_portfolio_delivery_state ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_ticker_notes ADD COLUMN IF NOT EXISTS note_type TEXT DEFAULT 'note'")
        conn.execute("ALTER TABLE app.user_ticker_notes ADD COLUMN IF NOT EXISTS note_title TEXT")
        conn.execute("ALTER TABLE app.user_ticker_notes ADD COLUMN IF NOT EXISTS review_date DATE")
        conn.execute("ALTER TABLE app.user_ticker_notes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")
        conn.execute("ALTER TABLE app.user_ticker_notes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
        conn.execute(
            """
            INSERT INTO app.portfolio_alert_preferences (
                profile_id,
                concentration_alerts_enabled,
                concentration_threshold_pct,
                rsi_alerts_enabled,
                overbought_rsi_threshold,
                oversold_rsi_threshold,
                daily_move_alerts_enabled,
                daily_move_threshold_pct,
                telegram_daily_brief_enabled,
                telegram_alerts_enabled,
                updated_at
            )
            SELECT 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM app.portfolio_alert_preferences WHERE profile_id = ?
            )
            """,
            [
                DEFAULT_ALERT_PREFERENCES['concentration_alerts_enabled'],
                DEFAULT_ALERT_PREFERENCES['concentration_threshold_pct'],
                DEFAULT_ALERT_PREFERENCES['rsi_alerts_enabled'],
                DEFAULT_ALERT_PREFERENCES['overbought_rsi_threshold'],
                DEFAULT_ALERT_PREFERENCES['oversold_rsi_threshold'],
                DEFAULT_ALERT_PREFERENCES['daily_move_alerts_enabled'],
                DEFAULT_ALERT_PREFERENCES['daily_move_threshold_pct'],
                DEFAULT_ALERT_PREFERENCES['telegram_daily_brief_enabled'],
                DEFAULT_ALERT_PREFERENCES['telegram_alerts_enabled'],
                _DEFAULT_PROFILE_ID,
            ],
        )
    finally:
        conn.close()


def _cleanup_expired_telegram_link_codes(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("DELETE FROM app.telegram_link_codes WHERE expires_at <= CAST(NOW() AS TIMESTAMP)")


def _telegram_bot_username() -> str | None:
    username = (os.environ.get('TELEGRAM_BOT_USERNAME') or '').strip().lstrip('@')
    return username or None


def _telegram_connect_url(code: str | None) -> str | None:
    bot_username = _telegram_bot_username()
    normalized_code = (code or '').strip()
    if not bot_username or not normalized_code:
        return None
    return f'https://t.me/{bot_username}?start={normalized_code}'


def _ensure_user_alert_preferences(conn: duckdb.DuckDBPyConnection, user_id: str) -> None:
    conn.execute(
        """
        INSERT INTO app.user_portfolio_alert_preferences (
            user_id,
            concentration_alerts_enabled,
            concentration_threshold_pct,
            rsi_alerts_enabled,
            overbought_rsi_threshold,
            oversold_rsi_threshold,
            daily_move_alerts_enabled,
            daily_move_threshold_pct,
            telegram_daily_brief_enabled,
            telegram_alerts_enabled,
            updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM app.user_portfolio_alert_preferences WHERE user_id = ?
        )
        """,
        [
            user_id,
            DEFAULT_ALERT_PREFERENCES['concentration_alerts_enabled'],
            DEFAULT_ALERT_PREFERENCES['concentration_threshold_pct'],
            DEFAULT_ALERT_PREFERENCES['rsi_alerts_enabled'],
            DEFAULT_ALERT_PREFERENCES['overbought_rsi_threshold'],
            DEFAULT_ALERT_PREFERENCES['oversold_rsi_threshold'],
            DEFAULT_ALERT_PREFERENCES['daily_move_alerts_enabled'],
            DEFAULT_ALERT_PREFERENCES['daily_move_threshold_pct'],
            DEFAULT_ALERT_PREFERENCES['telegram_daily_brief_enabled'],
            DEFAULT_ALERT_PREFERENCES['telegram_alerts_enabled'],
            user_id,
        ],
    )


def _next_note_id(conn: duckdb.DuckDBPyConnection, user_id: str | None = None) -> int:
    if _using_user_scope(user_id):
        row = conn.execute(
            "SELECT COALESCE(MAX(note_id), 0) + 1 FROM app.user_ticker_notes WHERE user_id = ?",
            [_normalize_user_id(user_id)],
        ).fetchone()
    else:
        row = conn.execute("SELECT COALESCE(MAX(note_id), 0) + 1 FROM app.ticker_notes").fetchone()
    return int(row[0]) if row and row[0] is not None else 1


def get_telegram_link_status(user_id: str) -> dict:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return {'linked': False}

    conn = _connect()
    try:
        _cleanup_expired_telegram_link_codes(conn)
        link_row = conn.execute(
            """
            SELECT chat_id, telegram_username, linked_at, updated_at
            FROM app.telegram_chat_links
            WHERE user_id = ?
            """,
            [normalized_user_id],
        ).fetchone()
        code_row = conn.execute(
            """
            SELECT code, expires_at, created_at
            FROM app.telegram_link_codes
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [normalized_user_id],
        ).fetchone()
        pending_code = code_row[0] if code_row else None
        return {
            'linked': bool(link_row),
            'chat_id': str(link_row[0]) if link_row else None,
            'telegram_username': link_row[1] if link_row else None,
            'linked_at': link_row[2].isoformat() if link_row and link_row[2] else None,
            'updated_at': link_row[3].isoformat() if link_row and link_row[3] else None,
            'pending_code': pending_code,
            'pending_code_expires_at': code_row[1].isoformat() if code_row and code_row[1] else None,
            'pending_code_created_at': code_row[2].isoformat() if code_row and code_row[2] else None,
            'telegram_bot_username': _telegram_bot_username(),
            'telegram_connect_url': _telegram_connect_url(pending_code),
        }
    finally:
        conn.close()


def create_telegram_link_code(user_id: str) -> dict:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        raise ValueError('A signed-in user is required to generate a Telegram link code.')

    conn = _connect()
    try:
        _cleanup_expired_telegram_link_codes(conn)
        conn.execute("DELETE FROM app.telegram_link_codes WHERE user_id = ?", [normalized_user_id])
        code = ''
        for _ in range(5):
            candidate = f"FS-{secrets.token_hex(3).upper()}"
            exists = conn.execute(
                "SELECT 1 FROM app.telegram_link_codes WHERE code = ?",
                [candidate],
            ).fetchone()
            if not exists:
                code = candidate
                break
        if not code:
            raise RuntimeError('Unable to generate a unique Telegram link code right now.')

        conn.execute(
            f"""
            INSERT INTO app.telegram_link_codes (code, user_id, expires_at, created_at)
            VALUES (?, ?, CAST(NOW() AS TIMESTAMP) + INTERVAL '{_TELEGRAM_LINK_CODE_TTL_MINUTES} minutes', CAST(NOW() AS TIMESTAMP))
            """,
            [code, normalized_user_id],
        )
        return get_telegram_link_status(normalized_user_id)
    finally:
        conn.close()


def complete_telegram_link(code: str, chat_id: str | int, telegram_username: str | None = None) -> dict:
    ensure_portfolio_tables()
    normalized_code = (code or '').strip().upper()
    normalized_chat_id = str(chat_id).strip()
    if not normalized_code or not normalized_chat_id:
        raise ValueError('Both a Telegram link code and chat id are required.')

    username = (telegram_username or '').strip() or None
    conn = _connect()
    try:
        _cleanup_expired_telegram_link_codes(conn)
        row = conn.execute(
            """
            SELECT user_id
            FROM app.telegram_link_codes
            WHERE code = ? AND expires_at > CAST(NOW() AS TIMESTAMP)
            """,
            [normalized_code],
        ).fetchone()
        if not row:
            raise ValueError('That Telegram link code is invalid or has expired.')

        user_id = row[0]
        conn.execute(
            "DELETE FROM app.telegram_chat_links WHERE user_id = ? OR chat_id = ?",
            [user_id, normalized_chat_id],
        )
        conn.execute(
            """
            INSERT INTO app.telegram_chat_links (user_id, chat_id, telegram_username, linked_at, updated_at)
            VALUES (?, ?, ?, NOW(), NOW())
            """,
            [user_id, normalized_chat_id, username],
        )
        conn.execute("DELETE FROM app.telegram_link_codes WHERE user_id = ?", [user_id])
        return get_telegram_link_status(user_id)
    finally:
        conn.close()


def unlink_telegram_chat_for_user(user_id: str) -> bool:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    if not normalized_user_id:
        return False

    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT 1 FROM app.telegram_chat_links WHERE user_id = ?",
            [normalized_user_id],
        ).fetchone()
        conn.execute("DELETE FROM app.telegram_chat_links WHERE user_id = ?", [normalized_user_id])
        conn.execute("DELETE FROM app.telegram_link_codes WHERE user_id = ?", [normalized_user_id])
        return bool(existing)
    finally:
        conn.close()


def resolve_user_id_for_telegram_chat(chat_id: str | int) -> str | None:
    ensure_portfolio_tables()
    normalized_chat_id = str(chat_id).strip()
    if not normalized_chat_id:
        return None

    conn = _connect(read_only=True)
    try:
        row = conn.execute(
            "SELECT user_id FROM app.telegram_chat_links WHERE chat_id = ?",
            [normalized_chat_id],
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def list_telegram_chat_links() -> list[dict]:
    ensure_portfolio_tables()
    conn = _connect()
    try:
        _cleanup_expired_telegram_link_codes(conn)
        rows = conn.execute(
            """
            SELECT user_id, chat_id, telegram_username, linked_at, updated_at
            FROM app.telegram_chat_links
            ORDER BY updated_at DESC
            """
        ).fetchall()
        return [
            {
                'user_id': row[0],
                'chat_id': str(row[1]),
                'telegram_username': row[2],
                'linked_at': row[3].isoformat() if row[3] else None,
                'updated_at': row[4].isoformat() if row[4] else None,
            }
            for row in rows
        ]
    finally:
        conn.close()


def list_holdings(user_id: str | None = None) -> list[dict]:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect(read_only=True)
    try:
        if normalized_user_id:
            rows = conn.execute(
                """
                SELECT symbol, shares, avg_cost, created_at, updated_at
                FROM app.user_portfolio_holdings
                WHERE user_id = ?
                ORDER BY symbol
                """,
                [normalized_user_id],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT symbol, shares, avg_cost, created_at, updated_at
                FROM app.portfolio_holdings
                ORDER BY symbol
                """
            ).fetchall()
    finally:
        conn.close()

    return [
        {
            'symbol': row[0],
            'shares': float(row[1]),
            'avg_cost': float(row[2]),
            'created_at': str(row[3]) if row[3] is not None else None,
            'updated_at': str(row[4]) if row[4] is not None else None,
        }
        for row in rows
    ]


def list_watchlist(user_id: str | None = None) -> list[dict]:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect(read_only=True)
    try:
        if normalized_user_id:
            rows = conn.execute(
                """
                SELECT symbol, created_at, updated_at
                FROM app.user_portfolio_watchlist
                WHERE user_id = ?
                ORDER BY symbol
                """,
                [normalized_user_id],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT symbol, created_at, updated_at
                FROM app.portfolio_watchlist
                ORDER BY symbol
                """
            ).fetchall()
    finally:
        conn.close()

    return [
        {
            'symbol': row[0],
            'created_at': str(row[1]) if row[1] is not None else None,
            'updated_at': str(row[2]) if row[2] is not None else None,
        }
        for row in rows
    ]


def list_ticker_notes(symbol: str | None = None, user_id: str | None = None) -> list[dict]:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect(read_only=True)
    try:
        if normalized_user_id and symbol:
            rows = conn.execute(
                """
                SELECT note_id, symbol, COALESCE(note_type, 'note'), note_title, note_text, review_date, created_at, updated_at
                FROM app.user_ticker_notes
                WHERE user_id = ? AND symbol = ?
                ORDER BY updated_at DESC, note_id DESC
                """,
                [normalized_user_id, symbol.upper().strip()],
            ).fetchall()
        elif normalized_user_id:
            rows = conn.execute(
                """
                SELECT note_id, symbol, COALESCE(note_type, 'note'), note_title, note_text, review_date, created_at, updated_at
                FROM app.user_ticker_notes
                WHERE user_id = ?
                ORDER BY updated_at DESC, note_id DESC
                """,
                [normalized_user_id],
            ).fetchall()
        elif symbol:
            rows = conn.execute(
                """
                SELECT note_id, symbol, COALESCE(note_type, 'note'), note_title, note_text, review_date, created_at, updated_at
                FROM app.ticker_notes
                WHERE symbol = ?
                ORDER BY updated_at DESC, note_id DESC
                """,
                [symbol.upper().strip()],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT note_id, symbol, COALESCE(note_type, 'note'), note_title, note_text, review_date, created_at, updated_at
                FROM app.ticker_notes
                ORDER BY updated_at DESC, note_id DESC
                """
            ).fetchall()
    finally:
        conn.close()

    return [
        {
            'note_id': int(row[0]),
            'symbol': row[1],
            'note_type': row[2],
            'note_title': row[3],
            'note_text': row[4],
            'review_date': str(row[5]) if row[5] is not None else None,
            'created_at': str(row[6]) if row[6] is not None else None,
            'updated_at': str(row[7]) if row[7] is not None else None,
        }
        for row in rows
    ]


def upsert_holding(symbol: str, shares: float, avg_cost: float, user_id: str | None = None) -> dict:
    ensure_portfolio_tables()
    symbol = symbol.upper().strip()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect()
    try:
        if normalized_user_id:
            conn.execute(
                """
                INSERT INTO app.user_portfolio_holdings (user_id, symbol, shares, avg_cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, NOW(), NOW())
                ON CONFLICT(user_id, symbol) DO UPDATE
                SET shares = excluded.shares,
                    avg_cost = excluded.avg_cost,
                    updated_at = NOW()
                """,
                [normalized_user_id, symbol, shares, avg_cost],
            )
        else:
            conn.execute(
                """
                INSERT INTO app.portfolio_holdings (symbol, shares, avg_cost, created_at, updated_at)
                VALUES (?, ?, ?, NOW(), NOW())
                ON CONFLICT(symbol) DO UPDATE
                SET shares = excluded.shares,
                    avg_cost = excluded.avg_cost,
                    updated_at = NOW()
                """,
                [symbol, shares, avg_cost],
            )
    finally:
        conn.close()

    for holding in list_holdings(user_id=normalized_user_id):
        if holding['symbol'] == symbol:
            return holding
    return {'symbol': symbol, 'shares': shares, 'avg_cost': avg_cost}


def delete_holding(symbol: str, user_id: str | None = None) -> bool:
    ensure_portfolio_tables()
    normalized = symbol.upper().strip()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect()
    try:
        if normalized_user_id:
            existing = conn.execute(
                "SELECT 1 FROM app.user_portfolio_holdings WHERE user_id = ? AND symbol = ?",
                [normalized_user_id, normalized],
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT 1 FROM app.portfolio_holdings WHERE symbol = ?",
                [normalized],
            ).fetchone()
        if not existing:
            return False
        if normalized_user_id:
            conn.execute(
                "DELETE FROM app.user_portfolio_holdings WHERE user_id = ? AND symbol = ?",
                [normalized_user_id, normalized],
            )
        else:
            conn.execute(
                "DELETE FROM app.portfolio_holdings WHERE symbol = ?",
                [normalized],
            )
    finally:
        conn.close()
    return True


def upsert_watchlist_symbol(symbol: str, user_id: str | None = None) -> dict:
    ensure_portfolio_tables()
    symbol = symbol.upper().strip()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect()
    try:
        if normalized_user_id:
            conn.execute(
                """
                INSERT INTO app.user_portfolio_watchlist (user_id, symbol, created_at, updated_at)
                VALUES (?, ?, NOW(), NOW())
                ON CONFLICT(user_id, symbol) DO UPDATE
                SET updated_at = NOW()
                """,
                [normalized_user_id, symbol],
            )
        else:
            conn.execute(
                """
                INSERT INTO app.portfolio_watchlist (symbol, created_at, updated_at)
                VALUES (?, NOW(), NOW())
                ON CONFLICT(symbol) DO UPDATE
                SET updated_at = NOW()
                """,
                [symbol],
            )
    finally:
        conn.close()

    for row in list_watchlist(user_id=normalized_user_id):
        if row['symbol'] == symbol:
            return row
    return {'symbol': symbol}


def delete_watchlist_symbol(symbol: str, user_id: str | None = None) -> bool:
    ensure_portfolio_tables()
    normalized = symbol.upper().strip()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect()
    try:
        if normalized_user_id:
            existing = conn.execute(
                "SELECT 1 FROM app.user_portfolio_watchlist WHERE user_id = ? AND symbol = ?",
                [normalized_user_id, normalized],
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT 1 FROM app.portfolio_watchlist WHERE symbol = ?",
                [normalized],
            ).fetchone()
        if not existing:
            return False
        if normalized_user_id:
            conn.execute(
                "DELETE FROM app.user_portfolio_watchlist WHERE user_id = ? AND symbol = ?",
                [normalized_user_id, normalized],
            )
        else:
            conn.execute(
                "DELETE FROM app.portfolio_watchlist WHERE symbol = ?",
                [normalized],
            )
    finally:
        conn.close()
    return True


def upsert_ticker_note(
    symbol: str,
    note_text: str,
    note_id: int | None = None,
    note_type: str = 'note',
    note_title: str | None = None,
    review_date: str | None = None,
    user_id: str | None = None,
) -> dict:
    ensure_portfolio_tables()
    normalized_symbol = symbol.upper().strip()
    normalized_user_id = _normalize_user_id(user_id)
    cleaned_text = note_text.strip()
    cleaned_type = (note_type or 'note').strip().lower()
    cleaned_title = note_title.strip() if note_title and note_title.strip() else None
    cleaned_review_date = review_date.strip() if isinstance(review_date, str) and review_date.strip() else None
    conn = _connect()
    try:
        target_note_id = int(note_id) if note_id is not None else _next_note_id(conn, normalized_user_id)
        if normalized_user_id:
            conn.execute(
                """
                INSERT INTO app.user_ticker_notes (
                    user_id, note_id, symbol, note_type, note_title, note_text, review_date, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
                ON CONFLICT(user_id, note_id) DO UPDATE
                SET symbol = excluded.symbol,
                    note_type = excluded.note_type,
                    note_title = excluded.note_title,
                    note_text = excluded.note_text,
                    review_date = excluded.review_date,
                    updated_at = NOW()
                """,
                [
                    normalized_user_id,
                    target_note_id,
                    normalized_symbol,
                    cleaned_type,
                    cleaned_title,
                    cleaned_text,
                    cleaned_review_date,
                ],
            )
        else:
            conn.execute(
                """
                INSERT INTO app.ticker_notes (note_id, symbol, note_type, note_title, note_text, review_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NOW(), NOW())
                ON CONFLICT(note_id) DO UPDATE
                SET symbol = excluded.symbol,
                    note_type = excluded.note_type,
                    note_title = excluded.note_title,
                    note_text = excluded.note_text,
                    review_date = excluded.review_date,
                    updated_at = NOW()
                """,
                [target_note_id, normalized_symbol, cleaned_type, cleaned_title, cleaned_text, cleaned_review_date],
            )
    finally:
        conn.close()

    for note in list_ticker_notes(normalized_symbol, user_id=normalized_user_id):
        if note['note_id'] == target_note_id:
            return note

    return {
        'note_id': target_note_id,
        'symbol': normalized_symbol,
        'note_type': cleaned_type,
        'note_title': cleaned_title,
        'note_text': cleaned_text,
        'review_date': cleaned_review_date,
        'created_at': None,
        'updated_at': None,
    }


def delete_ticker_note(note_id: int, user_id: str | None = None) -> bool:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect()
    try:
        if normalized_user_id:
            existing = conn.execute(
                "SELECT 1 FROM app.user_ticker_notes WHERE user_id = ? AND note_id = ?",
                [normalized_user_id, int(note_id)],
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT 1 FROM app.ticker_notes WHERE note_id = ?",
                [int(note_id)],
            ).fetchone()
        if not existing:
            return False
        if normalized_user_id:
            conn.execute(
                "DELETE FROM app.user_ticker_notes WHERE user_id = ? AND note_id = ?",
                [normalized_user_id, int(note_id)],
            )
        else:
            conn.execute(
                "DELETE FROM app.ticker_notes WHERE note_id = ?",
                [int(note_id)],
            )
    finally:
        conn.close()
    return True


def _load_latest_market_rows(symbols: list[str]) -> tuple[dict[str, dict], str | None]:
    if not symbols:
        return {}, None

    placeholders = ', '.join('?' for _ in symbols)
    conn = _connect(read_only=True)
    try:
        rows = conn.execute(
            f"""
            SELECT symbol, company_name, sector, close, date, pct_change, rsi_14
            FROM main_gold.mart_query_context
            WHERE date = (SELECT max(date) FROM main_gold.mart_query_context)
              AND symbol IN ({placeholders})
            """,
            symbols,
        ).fetchall()
    finally:
        conn.close()

    return {
        row[0]: {
            'company_name': row[1],
            'sector': row[2],
            'close': float(row[3]) if row[3] is not None else None,
            'date': str(row[4]) if row[4] is not None else None,
            'pct_change': float(row[5]) if row[5] is not None else None,
            'rsi_14': float(row[6]) if row[6] is not None else None,
        }
        for row in rows
    }, (str(rows[0][4]) if rows else None)


def _load_recent_close_series(symbols: list[str], periods: int = 8) -> dict[str, list[float]]:
    if not symbols:
        return {}

    placeholders = ', '.join('?' for _ in symbols)
    conn = _connect(read_only=True)
    try:
        rows = conn.execute(
            f"""
            WITH ranked AS (
              SELECT
                symbol,
                close,
                date,
                row_number() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
              FROM main_gold.mart_query_context
              WHERE symbol IN ({placeholders})
            )
            SELECT symbol, close, date
            FROM ranked
            WHERE rn <= ?
            ORDER BY symbol, date ASC
            """,
            [*symbols, periods],
        ).fetchall()
    finally:
        conn.close()

    series: dict[str, list[float]] = {}
    for symbol, close, _date in rows:
        if close is None:
            continue
        series.setdefault(symbol, []).append(float(close))

    return series


def calculate_portfolio(holdings: list[dict]) -> dict:
    if not holdings:
        return {
            'as_of_date': None,
            'total_value': 0,
            'total_cost': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'holdings': [],
            'positions': [],
            'sector_exposure': [],
            'missing_symbols': [],
            'portfolio_insights': {
                'top_position': None,
                'top_gainer': None,
                'top_loser': None,
                'concentration': {
                    'level': 'Balanced',
                    'top_position_weight_pct': 0,
                },
            },
        }

    symbols = [h['symbol'].upper() for h in holdings]
    prices, as_of_date = _load_latest_market_rows(symbols)
    missing_symbols = []
    positions = []

    for holding in holdings:
        symbol = holding['symbol'].upper()
        price_row = prices.get(symbol)
        if not price_row or price_row['close'] is None:
            missing_symbols.append(symbol)
            continue

        shares = float(holding['shares'])
        avg_cost = float(holding['avg_cost'])
        current_price = float(price_row['close'])
        value = current_price * shares
        cost = avg_cost * shares
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        positions.append(
            {
                'symbol': symbol,
                'company_name': price_row['company_name'],
                'sector': price_row['sector'],
                'shares': shares,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'daily_pct_change': price_row['pct_change'],
                'rsi_14': price_row['rsi_14'],
                'value': round(value, 2),
                'cost_basis': round(cost, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
            }
        )

    positions.sort(key=lambda row: row['value'], reverse=True)

    total_value = sum(position['value'] for position in positions)
    total_cost = sum(position['cost_basis'] for position in positions)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    sector_totals: dict[str, float] = {}
    for position in positions:
        sector_totals[position['sector']] = sector_totals.get(position['sector'], 0) + position['value']

    sector_exposure = [
        {
            'sector': sector,
            'value': round(value, 2),
            'pct': round(value / total_value * 100, 1) if total_value else 0,
        }
        for sector, value in sorted(sector_totals.items(), key=lambda item: -item[1])
    ]

    top_position = positions[0] if positions else None
    top_gainer = max(positions, key=lambda row: row['pnl_pct']) if positions else None
    top_loser = min(positions, key=lambda row: row['pnl_pct']) if positions else None
    concentration_pct = round((top_position['value'] / total_value) * 100, 1) if top_position and total_value else 0
    weighted_daily_change_pct = round(
        sum((position['value'] / total_value) * (position['daily_pct_change'] or 0) for position in positions),
        2,
    ) if total_value else 0

    if concentration_pct >= 40:
        concentration_level = 'High'
    elif concentration_pct >= 25:
        concentration_level = 'Moderate'
    else:
        concentration_level = 'Balanced'

    return {
        'as_of_date': as_of_date,
        'total_value': round(total_value, 2),
        'total_cost': round(total_cost, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl_pct, 2),
        'holdings': [{'symbol': h['symbol'].upper(), 'shares': float(h['shares']), 'avg_cost': float(h['avg_cost'])} for h in holdings],
        'positions': positions,
        'sector_exposure': sector_exposure,
        'missing_symbols': missing_symbols,
        'portfolio_insights': {
            'top_position': {
                'symbol': top_position['symbol'],
                'company_name': top_position['company_name'],
                'value': top_position['value'],
                'weight_pct': concentration_pct,
            } if top_position else None,
            'top_gainer': {
                'symbol': top_gainer['symbol'],
                'company_name': top_gainer['company_name'],
                'pnl_pct': top_gainer['pnl_pct'],
                'pnl': top_gainer['pnl'],
            } if top_gainer else None,
            'top_loser': {
                'symbol': top_loser['symbol'],
                'company_name': top_loser['company_name'],
                'pnl_pct': top_loser['pnl_pct'],
                'pnl': top_loser['pnl'],
            } if top_loser else None,
            'concentration': {
                'level': concentration_level,
                'top_position_weight_pct': concentration_pct,
            },
            'weighted_daily_change_pct': weighted_daily_change_pct,
        },
    }


def calculate_saved_portfolio(user_id: str | None = None) -> dict:
    return calculate_portfolio(list_holdings(user_id=user_id))


def calculate_watchlist_snapshot(user_id: str | None = None) -> dict:
    watchlist = list_watchlist(user_id=user_id)
    if not watchlist:
        return {
            'as_of_date': None,
            'symbols': [],
            'items': [],
            'missing_symbols': [],
            'summary': {
                'count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'top_mover': None,
            },
        }

    symbols = [item['symbol'].upper() for item in watchlist]
    prices, as_of_date = _load_latest_market_rows(symbols)
    trend_series = _load_recent_close_series(symbols)
    items = []
    missing_symbols = []

    for symbol in symbols:
        row = prices.get(symbol)
        if not row or row['close'] is None:
            missing_symbols.append(symbol)
            continue
        items.append(
            {
                'symbol': symbol,
                'company_name': row['company_name'],
                'sector': row['sector'],
                'current_price': row['close'],
                'daily_pct_change': row['pct_change'],
                'rsi_14': row['rsi_14'],
                'trend_points': trend_series.get(symbol, []),
            }
        )

    items.sort(key=lambda item: abs(item.get('daily_pct_change') or 0), reverse=True)
    positive_count = sum(1 for item in items if (item.get('daily_pct_change') or 0) > 0)
    negative_count = sum(1 for item in items if (item.get('daily_pct_change') or 0) < 0)

    return {
        'as_of_date': as_of_date,
        'symbols': symbols,
        'items': items,
        'missing_symbols': missing_symbols,
        'summary': {
            'count': len(items),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'top_mover': items[0] if items else None,
        },
    }


def get_alert_preferences(user_id: str | None = None) -> dict:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect(read_only=True)
    try:
        if normalized_user_id:
            row = conn.execute(
                """
                SELECT
                    concentration_alerts_enabled,
                    concentration_threshold_pct,
                    rsi_alerts_enabled,
                    overbought_rsi_threshold,
                    oversold_rsi_threshold,
                    daily_move_alerts_enabled,
                    daily_move_threshold_pct,
                    telegram_daily_brief_enabled,
                    telegram_alerts_enabled,
                    updated_at
                FROM app.user_portfolio_alert_preferences
                WHERE user_id = ?
                """,
                [normalized_user_id],
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT
                    concentration_alerts_enabled,
                    concentration_threshold_pct,
                    rsi_alerts_enabled,
                    overbought_rsi_threshold,
                    oversold_rsi_threshold,
                    daily_move_alerts_enabled,
                    daily_move_threshold_pct,
                    telegram_daily_brief_enabled,
                    telegram_alerts_enabled,
                    updated_at
                FROM app.portfolio_alert_preferences
                WHERE profile_id = ?
                """,
                [_DEFAULT_PROFILE_ID],
            ).fetchone()
    finally:
        conn.close()

    if not row:
        if normalized_user_id:
            conn = _connect()
            try:
                _ensure_user_alert_preferences(conn, normalized_user_id)
            finally:
                conn.close()
            return get_alert_preferences(user_id=normalized_user_id)
        return {**DEFAULT_ALERT_PREFERENCES, 'updated_at': None}

    return {
        'concentration_alerts_enabled': bool(row[0]),
        'concentration_threshold_pct': float(row[1]),
        'rsi_alerts_enabled': bool(row[2]),
        'overbought_rsi_threshold': float(row[3]),
        'oversold_rsi_threshold': float(row[4]),
        'daily_move_alerts_enabled': bool(row[5]),
        'daily_move_threshold_pct': float(row[6]),
        'telegram_daily_brief_enabled': bool(row[7]),
        'telegram_alerts_enabled': bool(row[8]),
        'updated_at': str(row[9]) if row[9] is not None else None,
    }


def update_alert_preferences(updates: dict, user_id: str | None = None) -> dict:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    current = get_alert_preferences(user_id=normalized_user_id)
    merged = {**current, **updates}
    conn = _connect()
    try:
        if normalized_user_id:
            _ensure_user_alert_preferences(conn, normalized_user_id)
            conn.execute(
                """
                UPDATE app.user_portfolio_alert_preferences
                SET concentration_alerts_enabled = ?,
                    concentration_threshold_pct = ?,
                    rsi_alerts_enabled = ?,
                    overbought_rsi_threshold = ?,
                    oversold_rsi_threshold = ?,
                    daily_move_alerts_enabled = ?,
                    daily_move_threshold_pct = ?,
                    telegram_daily_brief_enabled = ?,
                    telegram_alerts_enabled = ?,
                    updated_at = NOW()
                WHERE user_id = ?
                """,
                [
                    merged['concentration_alerts_enabled'],
                    merged['concentration_threshold_pct'],
                    merged['rsi_alerts_enabled'],
                    merged['overbought_rsi_threshold'],
                    merged['oversold_rsi_threshold'],
                    merged['daily_move_alerts_enabled'],
                    merged['daily_move_threshold_pct'],
                    merged['telegram_daily_brief_enabled'],
                    merged['telegram_alerts_enabled'],
                    normalized_user_id,
                ],
            )
        else:
            conn.execute(
                """
                UPDATE app.portfolio_alert_preferences
                SET concentration_alerts_enabled = ?,
                    concentration_threshold_pct = ?,
                    rsi_alerts_enabled = ?,
                    overbought_rsi_threshold = ?,
                    oversold_rsi_threshold = ?,
                    daily_move_alerts_enabled = ?,
                    daily_move_threshold_pct = ?,
                    telegram_daily_brief_enabled = ?,
                    telegram_alerts_enabled = ?,
                    updated_at = NOW()
                WHERE profile_id = ?
                """,
                [
                    merged['concentration_alerts_enabled'],
                    merged['concentration_threshold_pct'],
                    merged['rsi_alerts_enabled'],
                    merged['overbought_rsi_threshold'],
                    merged['oversold_rsi_threshold'],
                    merged['daily_move_alerts_enabled'],
                    merged['daily_move_threshold_pct'],
                    merged['telegram_daily_brief_enabled'],
                    merged['telegram_alerts_enabled'],
                    _DEFAULT_PROFILE_ID,
                ],
            )
    finally:
        conn.close()

    return get_alert_preferences(user_id=normalized_user_id)


def _serialize_alert_payload(payload: dict | None) -> str | None:
    if not payload:
        return None
    return json.dumps(payload)


def _build_portfolio_alerts(portfolio: dict, preferences: dict | None = None) -> list[dict]:
    preferences = preferences or get_alert_preferences()
    alerts: list[dict] = []
    positions = portfolio.get('positions', [])
    insights = portfolio.get('portfolio_insights', {})
    top_position = insights.get('top_position')
    concentration = insights.get('concentration', {})
    as_of_date = portfolio.get('as_of_date')

    if (
        top_position
        and preferences.get('concentration_alerts_enabled', True)
        and float(top_position.get('weight_pct') or 0) >= float(preferences.get('concentration_threshold_pct', 40.0))
    ):
        alerts.append(
            {
                'alert_id': f"concentration:{top_position['symbol']}",
                'symbol': top_position['symbol'],
                'source_scope': 'portfolio',
                'alert_type': 'concentration',
                'severity': 'high',
                'title': 'Concentration risk is elevated',
                'message': (
                    f"{top_position['symbol']} represents {top_position['weight_pct']:.1f}% of portfolio value "
                    f"as of {as_of_date}."
                ),
                'payload': top_position,
            }
        )

    for position in positions:
        symbol = position['symbol']
        rsi = position.get('rsi_14')
        daily_change = position.get('daily_pct_change')

        if (
            preferences.get('rsi_alerts_enabled', True)
            and rsi is not None
            and rsi >= float(preferences.get('overbought_rsi_threshold', 70.0))
        ):
            alerts.append(
                {
                    'alert_id': f"rsi-overbought:{symbol}",
                    'symbol': symbol,
                    'source_scope': 'portfolio',
                    'alert_type': 'rsi_overbought',
                    'severity': 'medium',
                    'title': f'{symbol} is overbought',
                    'message': f"{symbol} has RSI {rsi:.1f}, which suggests stretched momentum.",
                    'payload': {'symbol': symbol, 'rsi_14': rsi},
                }
            )
        elif (
            preferences.get('rsi_alerts_enabled', True)
            and rsi is not None
            and rsi <= float(preferences.get('oversold_rsi_threshold', 30.0))
        ):
            alerts.append(
                {
                    'alert_id': f"rsi-oversold:{symbol}",
                    'symbol': symbol,
                    'source_scope': 'portfolio',
                    'alert_type': 'rsi_oversold',
                    'severity': 'medium',
                    'title': f'{symbol} is oversold',
                    'message': f"{symbol} has RSI {rsi:.1f}, which suggests weak momentum or reversal risk.",
                    'payload': {'symbol': symbol, 'rsi_14': rsi},
                }
            )

        if (
            preferences.get('daily_move_alerts_enabled', True)
            and daily_change is not None
            and abs(daily_change) >= float(preferences.get('daily_move_threshold_pct', 3.0))
        ):
            direction = 'up' if daily_change > 0 else 'down'
            alerts.append(
                {
                    'alert_id': f"daily-move:{symbol}",
                    'symbol': symbol,
                    'source_scope': 'portfolio',
                    'alert_type': 'daily_move',
                    'severity': 'medium' if abs(daily_change) < 5 else 'high',
                    'title': f'{symbol} made a notable move',
                    'message': f"{symbol} closed {direction} {daily_change:+.2f}% on the latest warehouse date.",
                    'payload': {'symbol': symbol, 'daily_pct_change': daily_change},
                }
            )

    for symbol in portfolio.get('missing_symbols', []):
        alerts.append(
            {
                'alert_id': f"missing-price:{symbol}",
                'symbol': symbol,
                'source_scope': 'portfolio',
                'alert_type': 'missing_price',
                'severity': 'low',
                'title': f'{symbol} could not be priced',
                'message': f'{symbol} is saved in holdings but has no warehouse price in the latest snapshot.',
                'payload': {'symbol': symbol},
            }
        )

    return alerts


def _build_watchlist_alerts(watchlist: dict, preferences: dict | None = None) -> list[dict]:
    preferences = preferences or get_alert_preferences()
    alerts: list[dict] = []

    for item in watchlist.get('items', []):
        symbol = item['symbol']
        rsi = item.get('rsi_14')
        daily_change = item.get('daily_pct_change')

        if (
            preferences.get('rsi_alerts_enabled', True)
            and rsi is not None
            and rsi >= float(preferences.get('overbought_rsi_threshold', 70.0))
        ):
            alerts.append(
                {
                    'alert_id': f"watchlist-rsi-overbought:{symbol}",
                    'symbol': symbol,
                    'source_scope': 'watchlist',
                    'alert_type': 'rsi_overbought',
                    'severity': 'low',
                    'title': f'{symbol} watchlist momentum is stretched',
                    'message': f"{symbol} is on your watchlist and has RSI {rsi:.1f}.",
                    'payload': {'symbol': symbol, 'rsi_14': rsi},
                }
            )
        elif (
            preferences.get('rsi_alerts_enabled', True)
            and rsi is not None
            and rsi <= float(preferences.get('oversold_rsi_threshold', 30.0))
        ):
            alerts.append(
                {
                    'alert_id': f"watchlist-rsi-oversold:{symbol}",
                    'symbol': symbol,
                    'source_scope': 'watchlist',
                    'alert_type': 'rsi_oversold',
                    'severity': 'low',
                    'title': f'{symbol} watchlist momentum is washed out',
                    'message': f"{symbol} is on your watchlist and has RSI {rsi:.1f}.",
                    'payload': {'symbol': symbol, 'rsi_14': rsi},
                }
            )

        if (
            preferences.get('daily_move_alerts_enabled', True)
            and daily_change is not None
            and abs(daily_change) >= float(preferences.get('daily_move_threshold_pct', 3.0))
        ):
            direction = 'up' if daily_change > 0 else 'down'
            alerts.append(
                {
                    'alert_id': f"watchlist-daily-move:{symbol}",
                    'symbol': symbol,
                    'source_scope': 'watchlist',
                    'alert_type': 'daily_move',
                    'severity': 'low',
                    'title': f'{symbol} moved on your watchlist',
                    'message': f"{symbol} closed {direction} {daily_change:+.2f}% on the latest warehouse date.",
                    'payload': {'symbol': symbol, 'daily_pct_change': daily_change},
                }
            )

    for symbol in watchlist.get('missing_symbols', []):
        alerts.append(
            {
                'alert_id': f"watchlist-missing-price:{symbol}",
                'symbol': symbol,
                'source_scope': 'watchlist',
                'alert_type': 'missing_price',
                'severity': 'low',
                'title': f'{symbol} watchlist price is unavailable',
                'message': f'{symbol} is saved in your watchlist but has no warehouse price in the latest snapshot.',
                'payload': {'symbol': symbol},
            }
        )

    return alerts


def refresh_portfolio_alerts(user_id: str | None = None) -> list[dict]:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    portfolio = calculate_saved_portfolio(user_id=normalized_user_id)
    watchlist = calculate_watchlist_snapshot(user_id=normalized_user_id)
    preferences = get_alert_preferences(user_id=normalized_user_id)
    alerts = _build_portfolio_alerts(portfolio, preferences) + _build_watchlist_alerts(watchlist, preferences)

    conn = _connect()
    try:
        if normalized_user_id:
            conn.execute("DELETE FROM app.user_portfolio_alerts WHERE user_id = ?", [normalized_user_id])
            for alert in alerts:
                conn.execute(
                    """
                    INSERT INTO app.user_portfolio_alerts (
                        user_id, alert_id, symbol, source_scope, alert_type, severity, title, message, status,
                        payload_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, NOW(), NOW())
                    """,
                    [
                        normalized_user_id,
                        alert['alert_id'],
                        alert.get('symbol'),
                        alert.get('source_scope', 'portfolio'),
                        alert['alert_type'],
                        alert['severity'],
                        alert['title'],
                        alert['message'],
                        _serialize_alert_payload(alert.get('payload')),
                    ],
                )
        else:
            conn.execute("DELETE FROM app.portfolio_alerts")
            for alert in alerts:
                conn.execute(
                    """
                    INSERT INTO app.portfolio_alerts (
                        alert_id, symbol, source_scope, alert_type, severity, title, message, status,
                        payload_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, NOW(), NOW())
                    """,
                    [
                        alert['alert_id'],
                        alert.get('symbol'),
                        alert.get('source_scope', 'portfolio'),
                        alert['alert_type'],
                        alert['severity'],
                        alert['title'],
                        alert['message'],
                        _serialize_alert_payload(alert.get('payload')),
                    ],
                )
    finally:
        conn.close()

    return list_portfolio_alerts(user_id=normalized_user_id)


def list_portfolio_alerts(status: str | None = None, user_id: str | None = None) -> list[dict]:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect(read_only=True)
    try:
        if normalized_user_id and status:
            rows = conn.execute(
                """
                SELECT alert_id, symbol, alert_type, severity, title, message, status,
                       payload_json, created_at, updated_at, sent_to_telegram_at, source_scope
                FROM app.user_portfolio_alerts
                WHERE user_id = ? AND status = ?
                ORDER BY
                  CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                  END,
                  created_at DESC
                """,
                [normalized_user_id, status],
            ).fetchall()
        elif normalized_user_id:
            rows = conn.execute(
                """
                SELECT alert_id, symbol, alert_type, severity, title, message, status,
                       payload_json, created_at, updated_at, sent_to_telegram_at, source_scope
                FROM app.user_portfolio_alerts
                WHERE user_id = ?
                ORDER BY
                  CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                  END,
                  created_at DESC
                """,
                [normalized_user_id],
            ).fetchall()
        elif status:
            rows = conn.execute(
                """
                SELECT alert_id, symbol, alert_type, severity, title, message, status,
                       payload_json, created_at, updated_at, sent_to_telegram_at, source_scope
                FROM app.portfolio_alerts
                WHERE status = ?
                ORDER BY
                  CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                  END,
                  created_at DESC
                """,
                [status],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT alert_id, symbol, alert_type, severity, title, message, status,
                       payload_json, created_at, updated_at, sent_to_telegram_at, source_scope
                FROM app.portfolio_alerts
                ORDER BY
                  CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                  END,
                  created_at DESC
                """
            ).fetchall()
    finally:
        conn.close()

    return [
        {
            'alert_id': row[0],
            'symbol': row[1],
            'alert_type': row[2],
            'severity': row[3],
            'title': row[4],
            'message': row[5],
            'status': row[6],
            'payload': json.loads(row[7]) if row[7] else None,
            'created_at': str(row[8]) if row[8] is not None else None,
            'updated_at': str(row[9]) if row[9] is not None else None,
            'sent_to_telegram_at': str(row[10]) if row[10] is not None else None,
            'source_scope': row[11] if len(row) > 11 else 'portfolio',
        }
        for row in rows
    ]


def mark_alerts_sent(alert_ids: list[str], user_id: str | None = None) -> None:
    if not alert_ids:
        return
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    placeholders = ', '.join('?' for _ in alert_ids)
    conn = _connect()
    try:
        if normalized_user_id:
            conn.execute(
                f"""
                UPDATE app.user_portfolio_alerts
                SET sent_to_telegram_at = NOW(),
                    updated_at = NOW()
                WHERE user_id = ?
                  AND alert_id IN ({placeholders})
                """,
                [normalized_user_id, *alert_ids],
            )
        else:
            conn.execute(
                f"""
                UPDATE app.portfolio_alerts
                SET sent_to_telegram_at = NOW(),
                    updated_at = NOW()
                WHERE alert_id IN ({placeholders})
                """,
                alert_ids,
            )
    finally:
        conn.close()


def build_portfolio_brief(user_id: str | None = None) -> dict:
    portfolio = calculate_saved_portfolio(user_id=user_id)
    watchlist = calculate_watchlist_snapshot(user_id=user_id)
    preferences = get_alert_preferences(user_id=user_id)
    alerts = refresh_portfolio_alerts(user_id=user_id)
    insights = portfolio.get('portfolio_insights', {})
    top_position = insights.get('top_position')
    top_gainer = insights.get('top_gainer')
    top_loser = insights.get('top_loser')

    if not portfolio.get('positions'):
        summary = 'Your saved portfolio is empty. Add positions first to receive daily briefs and Telegram alerts.'
        return {
            'as_of_date': None,
            'summary': summary,
            'portfolio': portfolio,
            'watchlist': watchlist,
            'alerts': alerts,
            'preferences': preferences,
        }

    summary_parts = [
        (
            f"Portfolio value is ${portfolio['total_value']:,.2f} with unrealized P&L of "
            f"{portfolio['total_pnl']:+,.2f} ({portfolio['total_pnl_pct']:+.2f}%)."
        ),
        (
            f"Largest position is {top_position['symbol']} at {top_position['weight_pct']:.1f}% of portfolio value."
            if top_position else ''
        ),
        (
            f"Top winner is {top_gainer['symbol']} at {top_gainer['pnl_pct']:+.2f}%."
            if top_gainer else ''
        ),
        (
            f"Top laggard is {top_loser['symbol']} at {top_loser['pnl_pct']:+.2f}%."
            if top_loser else ''
        ),
    ]
    summary = ' '.join(part for part in summary_parts if part)

    return {
        'as_of_date': portfolio.get('as_of_date'),
        'summary': summary,
        'portfolio': portfolio,
        'watchlist': watchlist,
        'alerts': alerts,
        'preferences': preferences,
    }


def current_central_date() -> str:
    return datetime.now(_CENTRAL_TZ).date().isoformat()


def get_delivery_state(delivery_key: str, user_id: str | None = None) -> dict | None:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    conn = _connect(read_only=True)
    try:
        if normalized_user_id:
            row = conn.execute(
                """
                SELECT delivery_key, last_sent_date, updated_at
                FROM app.user_portfolio_delivery_state
                WHERE user_id = ? AND delivery_key = ?
                """,
                [normalized_user_id, delivery_key],
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT delivery_key, last_sent_date, updated_at
                FROM app.portfolio_delivery_state
                WHERE delivery_key = ?
                """,
                [delivery_key],
            ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return {
        'delivery_key': row[0],
        'last_sent_date': row[1],
        'updated_at': str(row[2]) if row[2] is not None else None,
    }


def should_send_delivery(delivery_key: str, target_date: str | None = None, user_id: str | None = None) -> bool:
    target_date = target_date or current_central_date()
    state = get_delivery_state(delivery_key, user_id=user_id)
    return not state or state.get('last_sent_date') != target_date


def mark_delivery_sent(delivery_key: str, sent_date: str | None = None, user_id: str | None = None) -> dict:
    ensure_portfolio_tables()
    normalized_user_id = _normalize_user_id(user_id)
    sent_date = sent_date or current_central_date()
    conn = _connect()
    try:
        if normalized_user_id:
            conn.execute(
                """
                INSERT INTO app.user_portfolio_delivery_state (user_id, delivery_key, last_sent_date, updated_at)
                VALUES (?, ?, ?, NOW())
                ON CONFLICT(user_id, delivery_key) DO UPDATE
                SET last_sent_date = excluded.last_sent_date,
                    updated_at = NOW()
                """,
                [normalized_user_id, delivery_key, sent_date],
            )
        else:
            conn.execute(
                """
                INSERT INTO app.portfolio_delivery_state (delivery_key, last_sent_date, updated_at)
                VALUES (?, ?, NOW())
                ON CONFLICT(delivery_key) DO UPDATE
                SET last_sent_date = excluded.last_sent_date,
                    updated_at = NOW()
                """,
                [delivery_key, sent_date],
            )
    finally:
        conn.close()

    return get_delivery_state(delivery_key, user_id=user_id) or {
        'delivery_key': delivery_key,
        'last_sent_date': sent_date,
        'updated_at': None,
    }
