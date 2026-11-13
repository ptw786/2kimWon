#!/usr/bin/env bash
# 안심온 개발 서버 세 개를 함께 띄운다 (WSL/Linux). Ctrl+C로 함께 종료.
# 파이썬: ANSIMON_PYTHON(가상환경 python 경로)이 있으면 그것을, 없으면 python3를 쓴다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ANSIMON_PYTHON:-python3}"
pids=()
cleanup() { echo; echo "[dev-up] 종료합니다"; for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

for port in 8010 5180 5181; do
  if ss -ltn 2>/dev/null | grep -q ":$port\b"; then echo "[dev-up] 포트 $port 가 이미 쓰이고 있어요. 먼저 끄고 다시 실행하세요."; exit 1; fi
done

(cd "$ROOT/apps/api" && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8010) & pids+=($!)
(cd "$ROOT/apps/web" && exec npm run dev) & pids+=($!)
(cd "$ROOT/apps/app" && exec npm run dev) & pids+=($!)

echo "[dev-up] API  http://127.0.0.1:8010/docs"
echo "[dev-up] 웹   http://127.0.0.1:5180  (생활지원사: /staff)"
echo "[dev-up] 앱   http://127.0.0.1:5181/r/KY-01"
wait
