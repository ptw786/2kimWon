"""라우터 공용 의존성: 요청마다 DB 연결 + 시간 지난 통화 정리(missed·interrupted)."""
from fastapi import Request

from .. import calls, db


def get_conn(request: Request):
    conn = db.connect(request.app.state.settings.db_path)
    try:
        calls.apply_timeouts(conn)
        yield conn
    finally:
        conn.close()


def get_llm(request: Request):
    return request.app.state.llm
