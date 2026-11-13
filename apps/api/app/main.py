"""FastAPI 앱. 실행: python -m uvicorn app.main:app --port 8010 (apps/api 폴더에서)."""
import asyncio
import contextlib
import logging
import threading

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import calls, db
from .config import load_settings, resolve_ollama_host
from .routers import elder, staff, system
from .services.llm import OllamaClient, RuleOnly

log = logging.getLogger('ansimon')
SCHEDULER_SECONDS = 20

_FIELD_KO = {'name': '이름', 'age': '나이', 'region': '지역', 'neighborhood': '동네', 'call_time': '전화 시각', 'memo': '메모',
             'text': '답변', 'source': '입력 방식', 'client_turn_id': '턴 번호', 'note': '확인 메모'}


def build_llm(settings):
    if not settings.llm_enabled:
        return RuleOnly()
    return OllamaClient(resolve_ollama_host(), settings.model)


async def _scheduler_loop(app: FastAPI):
    while True:
        try:
            await asyncio.to_thread(_scheduler_once, app.state.settings.db_path)
        except Exception:  # noqa: BLE001 — 스케줄러가 죽으면 안 된다
            log.exception('scheduler tick failed')
        await asyncio.sleep(SCHEDULER_SECONDS)


def _scheduler_once(path: str):
    conn = db.connect(path)
    try:
        calls.scheduler_tick(conn)
    finally:
        conn.close()


def create_app() -> FastAPI:
    settings = load_settings()
    db.init_db(settings.db_path, model_name=settings.model)
    llm = build_llm(settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        threading.Thread(target=app.state.llm.warm, daemon=True).start()   # 첫 통화가 느리지 않게
        task = asyncio.create_task(_scheduler_loop(app)) if settings.scheduler else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title='안심온 API v2', version='2.0', lifespan=lifespan)
    app.state.settings = settings
    app.state.llm = llm
    app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError):
        fields = []
        for e in exc.errors():
            loc = [str(x) for x in e.get('loc', []) if x not in ('body', 'query', 'path')]
            if loc:
                fields.append(_FIELD_KO.get(loc[-1], loc[-1]))
        msg = '입력값을 확인해 주세요' + (f": {', '.join(dict.fromkeys(fields))}" if fields else '') + '.'
        return JSONResponse({'detail': msg}, status_code=422)

    app.include_router(system.router, prefix='/api')
    app.include_router(staff.router, prefix='/api/staff')
    app.include_router(elder.router, prefix='/api/elder')
    return app


app = create_app()
