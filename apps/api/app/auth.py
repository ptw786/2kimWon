"""생활지원사 웹 인증 (PIN → 토큰). 시연용 최소 장치지만 기본으로 켜져 있다.

- ANSIMON_STAFF_PIN=1234 처럼 정하면 그 PIN. 정하지 않으면 서버를 켤 때마다 6자리를 새로 만들고 로그에 한 번 보여 준다.
- ANSIMON_STAFF_PIN=off 는 인증을 끈다 (자동 테스트용). 실제 어르신 정보를 넣을 때는 쓰지 않는다.
- 토큰 = HMAC(PIN) 이라 같은 PIN이면 서버를 다시 켜도 그대로 쓸 수 있고, PIN을 바꾸면 모두 다시 로그인한다.
- 틀린 PIN은 주소마다 5분에 5번까지.
"""
import hashlib
import hmac
import secrets
import threading
import time

from fastapi import HTTPException, Request

MAX_FAILS = 5
WINDOW = 300
_fails: dict[str, list[float]] = {}
_lock = threading.Lock()


def resolve_pin(env_value: str | None) -> tuple[str | None, bool]:
    """(PIN 또는 None=인증 끔, 새로 만든 PIN인지)."""
    v = (env_value or '').strip()
    if v.lower() in ('off', '0', 'false', 'no'):
        return None, False
    if v:
        return v, False
    return f'{secrets.randbelow(10 ** 6):06d}', True


def token_for(pin: str) -> str:
    return hmac.new(pin.encode(), b'ansimon-staff-v1', hashlib.sha256).hexdigest()[:40]


def check_login(request: Request, pin: str) -> str:
    expected = request.app.state.staff_pin
    if expected is None:
        return 'off'
    who = request.client.host if request.client else '?'
    now = time.monotonic()
    with _lock:
        recent = [t for t in _fails.get(who, []) if now - t < WINDOW]
        if len(recent) >= MAX_FAILS:
            raise HTTPException(429, '비밀번호를 여러 번 틀렸어요. 5분 뒤에 다시 해 주세요.')
        if not hmac.compare_digest(pin.strip(), expected):
            _fails[who] = recent + [now]
            raise HTTPException(401, f'비밀번호가 맞지 않아요. ({MAX_FAILS - len(recent) - 1}번 더 할 수 있어요)')
        _fails.pop(who, None)
    return token_for(expected)


def require_staff(request: Request) -> None:
    pin = request.app.state.staff_pin
    if pin is None:
        return
    header = request.headers.get('authorization', '')
    token = header[7:] if header.lower().startswith('bearer ') else ''
    if not (token and hmac.compare_digest(token, token_for(pin))):
        raise HTTPException(401, '생활지원사 로그인이 필요해요.')
