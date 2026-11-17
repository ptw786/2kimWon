#!/usr/bin/env bash
# 안심온 전체 검사: 서버 테스트 · 웹 빌드 · 앱 빌드+테스트. 하나라도 실패하면 실패.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ANSIMON_PYTHON:-python3}"
fail=0
step() { echo; echo "━━ $1"; }

step "API pytest"
(cd "$ROOT/apps/api" && ANSIMON_LLM=off ANSIMON_SCHEDULER=0 "$PY" -m pytest -q -p no:cacheprovider) || fail=1
step "웹 빌드"
(cd "$ROOT/apps/web" && npm run build --silent) || fail=1
step "앱 빌드"
(cd "$ROOT/apps/app" && npm run build --silent) || fail=1
step "앱 테스트"
(cd "$ROOT/apps/app" && npm test --silent) || fail=1

echo
if [ $fail -eq 0 ]; then echo "✅ 전체 통과"; else echo "❌ 실패한 단계가 있어요"; fi
exit $fail
