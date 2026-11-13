# 안심온 API v2 (`apps/api`)

FastAPI + SQLite + Ollama. 생활지원사 웹(`apps/web`)과 어르신 앱(`apps/app`)이 같이 쓰는 서버. 포트 **8010**.
API 약속은 `packages/contracts/CONTRACT.md`, 판정 규칙은 `docs/판정규칙.md`(값 원본: `app/domain/rules.yaml`).

## 실행

### Windows PowerShell

```powershell
cd apps\api
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8010
# 문서: http://127.0.0.1:8010/docs
```

### WSL (Ubuntu)

이 폴더는 Windows 디스크에 있으므로 **가상환경은 저장소 밖에** 만든다 (안에 만들면 Windows 쪽 `.venv`와 섞인다).

```bash
cd apps/api
python3 -m venv ~/.venvs/ansimon
source ~/.venvs/ansimon/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### 테스트

```bash
cd apps/api
python -m pytest -p no:cacheprovider
```

테스트는 임시 DB · `ANSIMON_LLM=off` · 스케줄러 끔으로 돈다(실제 DB·Ollama를 건드리지 않음).
`tests/test_rules_sensitivity.py`는 결과를 `docs/평가/<날짜>_rules_sensitivity.md`·`.json`에 쓴다.

처음 실행하면 DB(`apps/api/ansimon.db`)가 만들어지고 **시드 데이터가 자동으로** 들어간다. 시연 중 되돌리기: `POST /api/staff/demo/reset`.

## 환경변수

| 이름 | 기본값 | 설명 |
|---|---|---|
| `ANSIMON_DB` | `apps/api/ansimon.db` | SQLite 파일 경로 |
| `ANSIMON_LLM` | `on` | `off`면 AI를 부르지 않고 규칙만 씀 |
| `ANSIMON_MODEL` | `ax4-light:q4_K_M` | Ollama 모델 이름 |
| `OLLAMA_HOST` | (없음) | Ollama 주소. `http://` · `:11434`는 생략 가능 |
| `ANSIMON_SCHEDULER` | `1` | `0`이면 '정해진 시간에 전화'(20초마다 확인)를 끔 |
| `ANSIMON_DEMO` | `1` | `0`이면 `POST /staff/demo/reset`이 403 |

## Ollama 연결

- `OLLAMA_HOST`가 있으면 그 주소.
- 없으면 `ip route`의 `default via X` → `http://X:11434`. WSL에서는 이게 **Windows 호스트**다 (WSL 안의 `127.0.0.1`은 Windows의 Ollama에 닿지 않는다). 이 IP는 재부팅하면 바뀔 수 있어서 매번 새로 찾는다.
- `ip` 명령이 없으면(Windows에서 직접 실행) `http://127.0.0.1:11434`.
- WSL에서 연결이 안 되면 Windows 쪽 Ollama가 `127.0.0.1`에만 열려 있는 것이다 → Windows 환경변수 `OLLAMA_HOST=0.0.0.0`을 넣고 Ollama를 다시 켠다.
- 상태 확인: `GET /api/health` → `llm.reachable`.
- 서버가 켜질 때 백그라운드로 짧은 요청을 한 번 보내 모델을 올려 둔다(`keep_alive 30m`).
- 시간 제한: 항목 추출 4초 · 공감 3초 · 요약 8초. 시간 초과·연결 실패·형식 오류는 모두 **규칙이 대신**하고 `ai_runs`에 `fallback`과 이유를 남긴다. Ollama가 아예 없어도 통화는 끝까지 된다.

## 구조

```
app/
  main.py      앱·라우터·스케줄러·검증 오류(한국어)
  config.py    환경변수, Ollama 주소 찾기
  db.py        SQLite 연결·스키마·시간(UTC 저장, KST 응답)·tx()
  calls.py     통화 진행: 읽기 → 판단(domain)+LLM → 짧은 쓰기 트랜잭션
  seed.py      가상 어르신 6명 + 7일 통화 (실제 대화 흐름을 그대로 돌려 만듦)
  routers/     staff.py · elder.py · system.py · deps.py(연결 + 시간 지난 통화 정리)
  domain/      I/O 없는 순수 함수 — rules.yaml · safety.py · keywords.py · dialogue.py · scoring.py · questions.py · textutil.py
  services/    llm.py(LLMClient · OllamaClient · RuleOnly · FakeLLM) · prompts/*.md
```

`calls.py`는 `docs/구조.md`에 없는 파일이다. 라우터 두 곳(웹·앱)과 시드가 같은 통화 진행 코드를 써야 해서 따로 뺐다.

### 한 턴에서 지키는 것

1. 안전 신호 정규식(`safety.py`) → 걸리면 기록 + 고정 안내 + **다음 질문으로 진행**(확인 질문으로 붙잡지 않음).
2. 항목 추출: Ollama(JSON 스키마) + 키워드 규칙을 **둘 다** 보고 주제마다 더 나쁜 쪽을 쓴다. AI 인용(quote)이 답변 원문에 없으면 버린다.
3. 다음 행동은 코드(`dialogue.py`)가 정한다. 질문 문장은 언제나 상태 하나(`step_index`)에서만 나온다.
4. **LLM은 쓰기 트랜잭션 밖에서만** 부른다. 다 끝난 뒤 짧게 저장. 같은 `client_turn_id`는 저장된 결과를 그대로 돌려준다.
5. 시간 지난 통화: 벨 30초 → `missed`, 통화 중 10분 무응답 → `interrupted`. 모든 요청 앞과 스케줄러에서 정리한다.

## 계약 해석

CONTRACT.md와 판정규칙.md만으로 정해지지 않은 부분을 이렇게 읽었다. 응답 모양은 계약 그대로다.

1. **추세(B)**: 오늘부터 거슬러 '주의 이상'이 이어진 날 수. 답을 들은 통화가 없던 날(미응답·통화 없음)은 **건너뛰고**(끊지 않음), 양호인 날에서 끊는다. 그래서 "주의 → 주의 → (미응답) → 위험"은 3일 연속.
2. **연락(C)**: §6 예시("어제 미응답 +10")에 맞춰, 오늘 받은 통화라도 **바로 앞 통화가 어제·오늘 미응답이면** +10(앞에 연속 2회 이상이면 +20). 미응답 통화 자체는 "오늘 미응답 +10", 앞까지 이어지면 "연속 미응답 n회 +20". 상한 20.
3. **미응답·거절 통화도 assessment를 만든다**(항목은 모두 미확인 → 미확인 2개 이상이라 '관찰'). 대시보드가 "오늘 마지막으로 끝난 통화 기준"이라서.
4. 한 통화에서 같은 주제가 여러 번 나오면 **더 나쁜 상태**를 쓴다. 지금 묻지 않은 주제는 **주의·위험만** 기록한다(양호는 그 질문을 할 때 듣는다). AI가 규칙의 주의·위험을 내리지 못한다(원칙 1을 항목에도 적용).
5. 이유(reasons): 안전 신호는 `kind:'safety'`, 0점. 미확인이 2개 이상이면 0점짜리 이유 "미확인 n개 (…)"를 붙인다(단계 근거). 상한에 걸리면 넘는 만큼 뒤쪽 이유 점수를 깎아 **이유 점수의 합 = 점수**.
6. 안전 신호가 나온 질문은 넘어간다. 그 답으로 그 주제를 판정하지 못했으면 '미확인'. 마지막 질문에서 나오면 `action:'safety'`, `finished:true`.
7. `repeat_request`는 주제마다 3번까지 받아 준다(같은 질문 그대로, 진행 안 함). 그 뒤에는 '알아듣기 어려움'으로 본다(무한 반복 방지). 답이 섞여 있어도 반복하며, 섞인 답은 **물었던 주제로** 저장된다.
8. 다시 물을 때(`reask`) 다른 주제 신호가 있었으면 그 공감 문장 + 쉬운 말 질문(예: 식사 질문에 "외로워요" → 외로움 공감 + "오늘 밥은 드셨어요?"). 두 번째 재질문엔 버튼 문구 힌트를 붙인다.
9. `source:'option'`(버튼)은 문구가 정해져 있어 AI 추출을 부르지 않는다(공감 문장은 AI 시도).
10. `answer`를 두 번 보내면 첫 답변 전까지는 같은 인사 결과, 그 뒤엔 409. 벨이 울리는 중 `hangup` = `declined`.
11. `GET /elder/calls/{id}`에 `topic`, `options`를 더 넣었다(이어가기 화면용, 추가 필드).
12. `GET /elder/{id}/records`: 오늘부터 14일 **매일 한 줄**(최신 → 과거). 통화 없던 날은 `status_label:'전화가 없던 날'`, `chips:[]`. 칩은 항목별 쉬운 말(양호 `ok`, 주의·위험 `watch`), 안전 신호가 있었으면 "생활지원사님께 알렸어요".
13. `home.week_count` = 최근 7일(오늘 포함) 중 통화를 끝까지 마친 날 수.
14. `step.index`: 벨 울림·미응답·거절 0, 통화 중·중단은 지금(그때) 질문 번호, 완료 5.
15. 생활지원사 확인(`check`)은 통화마다 저장. `ResidentRow.staff_check` = 오늘 통화 중 마지막 확인.
16. 대시보드 정렬: 단계(긴급→오늘 확인→관찰→양호) → 점수 높은 순 → 오늘 assessment가 없는 어르신은 맨 뒤(id 순). `counts.missed`·`not_called`는 오늘 마지막 통화 상태 기준.
17. AI를 끈 경우(`ANSIMON_LLM=off`)에도 `ai_runs`에 `model:null, ms:null, outcome:'fallback', note:'AI 꺼짐 · 규칙 사용'`을 남긴다.
18. 통화 요약: 끝나는 순간 규칙 요약을 저장하고, 응답을 보낸 뒤 백그라운드에서 AI 요약으로 덮어쓴다(실패하면 규칙 요약 유지). 10분 무응답으로 닫힌 통화는 규칙 요약만.
19. 입력 검증 오류(422)도 `detail`은 한국어 문장 하나(예: "입력값을 확인해 주세요: 전화 시각.").
20. 새로 등록한 어르신은 `is_virtual:false`, 코드는 `KY-07`부터 자동.
21. 질문은 모두 "네 = 양호"가 되게 만들었다(예: "오늘 기분은 좀 괜찮으세요?") — 짧은 대답 "응/어/네/아니"를 지금 질문 기준으로 판정하기 위해.

## 아직 가짜인 부분

- **전화가 아니다.** 앱이 2초마다 `incoming`을 물어보는 방식. 실제 전화망·푸시 알림 없음.
- 음성 인식(STT)·읽어 주기(TTS)는 앱(브라우저) 쪽 몫. 서버는 글자만 받는다.
- 시드 어르신 6명과 지난 통화는 **가상 데이터**. 시드의 `ai_runs`(모델 이름·ms)는 실제 호출이 아니라 키워드 판정으로 만든 값이고 `note:'시드 데이터'`로 표시된다.
- 가중치·기준선은 현장 검증 전 **가설**(`docs/평가/` 민감도 결과도 가상 데이터 기준).
- 로그인·권한 없음. 생활지원사·어르신 구분은 화면(경로)뿐.
- 긴급이어도 문자·119 자동 연락은 하지 않는다(판정규칙 원칙 5). 대시보드 표시뿐.
- 스케줄러는 서버 프로세스 하나 안에서만 돈다(여러 개 띄우면 중복 전화 가능).
