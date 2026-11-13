"""환경변수 (README.md 의 표 참고)."""
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = 'ax4-light:q4_K_M'


@dataclass(frozen=True)
class Settings:
    db_path: str
    llm_enabled: bool
    model: str
    scheduler: bool
    demo: bool


def _flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() not in ('0', 'off', 'false', 'no', '')


def load_settings() -> Settings:
    return Settings(
        db_path=os.environ.get('ANSIMON_DB') or str(API_DIR / 'ansimon.db'),
        llm_enabled=_flag('ANSIMON_LLM', 'on'),
        model=os.environ.get('ANSIMON_MODEL') or DEFAULT_MODEL,
        scheduler=_flag('ANSIMON_SCHEDULER', '1'),
        demo=_flag('ANSIMON_DEMO', '1'),
    )


def _normalize_host(h: str) -> str:
    h = h.strip().rstrip('/')
    if not re.match(r'^https?://', h):
        h = 'http://' + h
    if h.startswith('http://0.0.0.0'):
        h = h.replace('0.0.0.0', '127.0.0.1', 1)
    if not re.search(r':\d+$', h):
        h += ':11434'
    return h


def resolve_ollama_host() -> str:
    """OLLAMA_HOST → 없으면 WSL 기본 게이트웨이(Windows 쪽 Ollama) → 없으면 127.0.0.1."""
    env = os.environ.get('OLLAMA_HOST')
    if env:
        return _normalize_host(env)
    try:
        out = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=2).stdout
        m = re.search(r'^default via (\S+)', out, re.M)
        if m:
            return f'http://{m.group(1)}:11434'
    except (OSError, subprocess.SubprocessError):
        pass
    return 'http://127.0.0.1:11434'
