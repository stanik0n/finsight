import os
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


AUTH_ENABLED = _truthy(os.environ.get('FINSIGHT_AUTH_ENABLED')) or bool(
    os.environ.get('CLERK_JWT_PUBLIC_KEY', '').strip()
)
CLERK_JWT_PUBLIC_KEY = os.environ.get('CLERK_JWT_PUBLIC_KEY', '').strip()
INTERNAL_API_KEY = os.environ.get('FINSIGHT_INTERNAL_API_KEY', '').strip()


@lru_cache(maxsize=1)
def _jwt_public_key() -> str:
    key = CLERK_JWT_PUBLIC_KEY
    if not key:
        raise HTTPException(status_code=500, detail='CLERK_JWT_PUBLIC_KEY is not configured.')
    return key.replace('\\n', '\n')


def _decode_clerk_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _jwt_public_key(),
            algorithms=['RS256'],
            options={'verify_aud': False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail='Invalid authentication token.') from exc


def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_finsight_service_key: str | None = Header(default=None),
    x_telegram_chat_id: str | None = Header(default=None),
) -> str | None:
    if INTERNAL_API_KEY and x_finsight_service_key == INTERNAL_API_KEY:
        if x_telegram_chat_id:
            from portfolio import resolve_user_id_for_telegram_chat

            user_id = resolve_user_id_for_telegram_chat(str(x_telegram_chat_id))
            if not user_id:
                raise HTTPException(status_code=401, detail='Telegram chat is not linked to a FinSight account.')
            return user_id
        return None

    if not AUTH_ENABLED:
        return None

    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Authentication required.')

    token = authorization.split(' ', 1)[1].strip()
    claims = _decode_clerk_token(token)
    user_id = str(claims.get('sub') or '').strip()
    if not user_id:
        raise HTTPException(status_code=401, detail='Authenticated user is missing a subject claim.')
    return user_id
