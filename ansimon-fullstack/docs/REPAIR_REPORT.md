# 안심온 오류 수정 보고서

검증일: 2026-11-09 (한국 시간)

## 작업 범위와 데이터 보존

업로드된 `ansimon-fullstack.zip`의 기존 파일을 추출해 수정했다. 로컬 VS Code 세션이나 사용자 PC의 실행 로그·DB에는 접근하지 못했다. ZIP에 들어 있는 README의 설명은 참고 자료로 취급했고, 사용자의 오류 수정 요청을 작업 범위로 삼았다. 기존 화면·스타일·통화 질문·FastAPI/SQLite 구조를 유지했다.

원본 ZIP에는 13개 파일이 있으며 `.db`, `.db-wal`, `.db-shm` 파일은 없다. 따라서 사용자 PC의 기존 DB를 직접 백업했다고 주장할 수 없다. 수정 서버는 기존 DB가 있으면 SQLite `backup()`으로 `DB파일명.backup-UTC시각` 스냅샷을 만든 뒤 초기화를 수행한다. 백업에는 커밋된 WAL 데이터도 포함된다. 기존 데이터 삭제나 DB 교체는 하지 않는다. 기존 스키마에 `calls.request_key`와 유니크 인덱스만 추가하며, 기존 스키마와 기록 보존을 자동 테스트했다.

가상 어르신 4명을 넣는 원본의 빈 DB 초기화 동작은 유지했다. API 오류를 성공으로 바꾸거나 가짜 목록·통화 결과로 대체하지 않았다. 검증은 임시 DB를 사용했고 테스트 데이터는 배포 ZIP에 포함하지 않았다.

## 구조와 요청 흐름

```text
ansimon-fullstack/
├── backend/
│   ├── main.py                 FastAPI, SQLite, 통화 로직
│   ├── requirements.txt
│   └── tests/                  원래 테스트 + 회귀 테스트
├── frontend/
│   ├── package.json, package-lock.json
│   ├── vite.config.js          /api → http://127.0.0.1:8000
│   ├── src/App.jsx             대시보드, 기록, 전화 체험
│   ├── src/api.js              fetch, 오류 처리
│   ├── src/main.jsx, styles.css
│   └── tests/e2e.py            실제 서버·Chromium 자동 검증
├── docs/REFERENCES.md          기존 자료 유지
├── docs/REPAIR_REPORT.md
└── README.md
```

프론트엔드는 같은 출처의 `/api/...`를 호출한다. 개발 서버 포트는 5173, FastAPI 포트는 8000이다. 브라우저는 Vite 프록시를 통해 API에 접근하므로 일반 개발 흐름에서는 교차 출처 요청이 아니다. 백엔드 직접 접근에 필요한 `localhost:5173`, `127.0.0.1:5173` CORS 허용 설정도 확인했다. 중복 방지 헤더를 preflight 허용 목록에 추가했고 두 출처를 테스트했다. 포트가 차면 Vite가 다른 포트로 조용히 바뀌지 않도록 `strictPort`를 적용했다.

DB 경로는 기본 `backend/ansimon.db`의 절대 경로이고 `ANSIMON_DB`로 변경 가능하다. `residents`, `calls`, `turns` 테이블 생성, 외래 키 활성화, 쓰기 트랜잭션 커밋·롤백을 확인했다.

## 확인한 오류와 추정 구분

| 항목 | 확인 근거 | 수정 |
|---|---|---|
| 시간대 DB가 없으면 대시보드 500 | 원본을 `PYTHONTZPATH=''`, `tzdata` 없는 Python 환경에서 실행. 어르신 API 200, 대시보드 500. 실제 예외는 `ZoneInfoNotFoundError: No time zone found with key Asia/Seoul` | 현대 한국 서비스 날짜를 UTC+09:00으로 계산하여 OS IANA DB 의존 제거 |
| 대시보드 실패가 어르신·통화 목록 표시도 막음 | 원본 `Promise.all`에서 어느 한 요청만 실패해도 모든 상태 갱신을 건너뜀 | `/residents`, `/dashboard`, `/calls`를 각각 조회·갱신. 실패한 API 오류는 계속 표시 |
| 재시도 버튼 동작 | 원본도 `onClick={load}`로 두 API를 재호출함. 서버 측 오류 자체는 재호출로 해결되지 않음 | 실제 네트워크 재호출 검증. 로딩 상태 갱신·중복 클릭 제한 |
| 새로고침·화면 이동 후 통화 진행 상태 소실 | 원본은 통화 ID를 React ref에만 보관. DB는 `in_progress` 유지, 다음 시작은 409 | 같은 어르신의 체험 화면을 열면 저장된 진행 중 통화·답변·다음 질문 복원 |
| 종료 실패 후 완료 저장 재시도 경로 부족 | 원본은 마지막 답변 뒤 자동 finish 실패 시 완료를 다시 저장하는 UI가 없고 중단만 가능 | 5개 답변 저장 후 기존 종료 버튼을 `완료 저장`으로 동작시킴 |
| 재전송·동시 요청의 중복 저장 가능 | 원본 답변은 현재 COUNT로 다음 질문을 결정. 동일 답변 재전송을 다음 질문으로 저장할 수 있음. 시작의 조회→삽입도 분리된 상태 | 쓰기 `BEGIN IMMEDIATE`, 시작·거절 요청 키, 답변 순번 재전송 검증, 동일 상태 종료 재시도 허용 |
| 오류 정보 부족 | 원본은 비 JSON 오류를 `{}`로 바꾸고 `요청 실패 (500)`만 표시 | API 경로·HTTP 코드·서버 detail·검증 오류 표시. 잘못된 JSON도 오류. DB 오류는 JSON 안내 + 서버 로그에 실제 예외 |
| 백엔드 미실행 시 프록시 연결 실패 | 수정 후 실제 백엔드를 끈 상태에서 요청하여 확인 | Vite가 설명 있는 JSON 502 응답. 백엔드 실행 후 화면의 재시도로 복구 확인 |

**사용자 PC에서 발생한 500이 시간대 누락 때문이라고 확정할 수는 없다.** 이 원인은 업로드 원본에서 조건을 맞춰 실제 재현하고 수정했다. 사용자 PC의 DB 스키마 불일치, 권한, 다른 포트의 서버 등은 로그·DB가 없어 미확인이다. 기존 통화 저장 코드가 항상 실패했던 것도 아니다. 정상 Linux 환경에서 원본 테스트 2개는 통과했다. 목록 조회가 대시보드 실패와 묶여 저장된 기록까지 가리는 구조적 오류를 확인했다.

## API·요청/응답 확인

독립된 “통화 기록 저장 API”는 원래 없다. 시작·답변·종료 API가 각각 DB에 저장한다. 새 저장 API를 만들지 않고 이 흐름을 검증했다.

| 메서드·경로 | 요청 | 주요 응답/DB 동작 |
|---|---|---|
| GET `/api/health` | 없음 | `{ok, mode}` |
| GET `/api/questions` | 없음 | `[{topic,text}]`, 5문항 |
| GET `/api/residents` | 없음 | `[{id,name,age,neighborhood,call_time}]` |
| GET `/api/dashboard` | 없음 | `{date,total,completed,pending,interrupted,declined,in_progress,residents}` |
| POST `/api/residents/{id}/calls` | JSON 본문 불필요. 선택 `Idempotency-Key` 헤더 | 201 `{id,resident_id,status,question,topic}`. calls 삽입 |
| POST `/api/residents/{id}/decline` | JSON 본문 불필요. 선택 `Idempotency-Key` 헤더 | 201 `{id,status}`. 거절 기록 저장 |
| POST `/api/calls/{id}/turns` | `{answer: string, index?: 0..4}`. 답변 1~500자, 공백만 허용 안 함 | 201 `{count,reply,finished,next_question}`. turns 삽입 |
| POST `/api/calls/{id}/finish` | `{status: "completed" 또는 "interrupted"}` | 200 `{id,status,summary,answered}`. 종료 시각·상태·요약 UPDATE |
| GET `/api/calls` | 선택 `resident_id`, `limit`(기본 100, 최대 500) | 어르신 이름을 포함하는 통화 배열 |
| GET `/api/calls/{id}` | 없음 | 통화 필드 + `turns` 배열 |

프론트엔드는 시작·거절 재시도에 같은 키를 사용하며, 새 체험에는 새 키를 사용한다. 답변에는 질문 순번 `index`를 보낸다. 같은 순번·답변 재전송은 기존 결과를 반환하고 다른 답변은 409로 거절한다. 종료는 이미 같은 상태로 저장되어 있으면 기존 결과를 반환하고 다른 상태로 바꾸려면 409를 반환한다. 구형 클라이언트의 헤더·index 없는 요청도 호환되지만, 답변 재전송 식별과 거절 중복 방지는 새 프로토콜을 사용하는 클라이언트에 적용된다. 오류 코드는 404(없음), 409(충돌), 422(입력/질문 미완료), DB 오류 500이다.

## 수정 파일

| 파일 | 변경 |
|---|---|
| `backend/main.py` | 시간대, 백업·비파괴 스키마 추가, 쓰기 직렬화, 재전송 중복 방지, DB 오류 응답 |
| `backend/tests/test_api.py` | 기존 테스트 유지, DB 설정은 공통 fixture로 이동 |
| `frontend/src/App.jsx` | 독립 데이터 갱신, 재시도 상태, 진행 중 통화 복원, 답변 순번, 완료 저장 재시도 |
| `frontend/src/api.js` | API 오류·JSON 파싱 오류 안내, 재전송 키 전달 |
| `frontend/vite.config.js` | 실제 프록시 연결 실패 JSON 502, 고정 포트 |
| `.gitignore` | DB 백업 파일 제외 |
| `README.md` | DB 삭제 안내 제거, 보존·복원·테스트 방법 갱신 |

추가 파일: `backend/tests/conftest.py`, `backend/tests/test_regressions.py`, `frontend/tests/e2e.py`, `frontend/package-lock.json`, 이 보고서와 `docs/verification/`의 실행 로그. 기존 원본 파일은 삭제하지 않았다. 의존성·가상환경·테스트 DB는 ZIP에서 제외했다.

## 자동 테스트 결과

| 요청한 검증 | 결과 | 증거 |
|---|---|---|
| 백엔드 실행 | 통과 | 실제 Uvicorn subprocess 시작 후 HTTP health 200, 재시작 |
| 어르신 목록 API | 통과 | TestClient 및 Vite 프록시·Chromium에서 4개 표시 |
| 통화 시작 API | 통과 | 실제 브라우저에서 시작, 동시 동일 키 4개 요청은 단일 ID |
| 답변 제출 API | 통과 | 실제 5문항, 순번 재전송·동시 전송 중복 없음 |
| 통화 종료 API | 통과 | 완료·중단, 5문항 미완료 422, 같은 종료 재시도 |
| 통화 기록 저장 | 통과 | 상세 응답에 5개 답변·완료 상태·요약. 종료 커밋 후 응답 유실 재현 |
| 통화 기록 조회 API | 통과 | 목록·상세 및 화면에서 확인 |
| 새로고침 후 유지 | 통과 | 브라우저 reload·진행 복원, 별도 Python 프로세스 및 Uvicorn 재시작 후 상세 동일 |
| React 빌드 | 통과 | `npm run build`, Vite 6.4.5, 모듈 1580개, 1.87초 |

- `python -m pytest -q backend/tests`: **8 passed**, 1.87초.
- `frontend/tests/e2e.py`: 실제 Uvicorn + Vite + Chromium, **5개 시나리오 묶음 통과**. 브라우저 JavaScript 오류 없음.
- 시간대 DB 없는 환경의 500 회귀, 기존 DB 백업·마이그레이션 보존, CORS 두 출처, 입력 검증, DB 오류 500을 포함했다.
- 대시보드 단독 장애는 브라우저 route로 500을 주입한 테스트다. 백엔드 미실행·통화·저장·재시작은 실제 서버를 사용했다. 종료 응답 유실은 서버의 실제 finish를 수행한 다음 브라우저 응답을 끊어 검증했다.
- pytest에 Starlette TestClient의 `httpx` 관련 deprecation warning 1개가 있다. 테스트 실패는 아니다. 이를 숨기지 않았다.

검증 환경: Linux, Python 3.12.14, Node.js 24.22.1, React 19 계열, FastAPI 0.162.2. 프론트엔드는 이번 설치 버전을 lockfile로 고정했다. 전체 로그는 `docs/verification/`에 포함했다.

## 남아 있는 확인 사항

- 로컬 VS Code 폴더에 자동 적용된 것은 아니다. 수정 ZIP의 소스 파일을 기존 프로젝트에 반영해야 한다. 사용자 PC의 기존 DB는 삭제·덮어쓰기하지 말고 유지해야 한다.
- 사용자 PC의 실제 DB·로그·Windows 런타임은 미확인이다. 제공된 원본 스키마의 보존·마이그레이션은 검증했으나 임의로 다른 스키마나 손상된 DB를 자동 복구하지 않는다. 부적합한 DB 오류를 가짜 성공으로 처리하지 않는다.
- 실제 마이크 입력·한국어 TTS·외부 음성 인식은 자동 검증 범위에 포함하지 않았다. 텍스트 답변으로 기존 통화 기능 전체를 검증했다.
- `vite preview`/정적 배포를 위한 API 라우팅은 기존 범위 밖이다. 이번 실행 검증은 README의 Vite 개발 서버와 FastAPI 구성 기준이다.
- 원래 통화 목록은 기본 최근 100개이며, API 최대 500개 제한은 유지했다. 페이지네이션 등 새 기능은 추가하지 않았다.

## 산출물 위치

이 클라우드 환경의 작업본은 `/workspace/work/ansimon/ansimon-fullstack`이다. 수정 ZIP은 `/workspace/work/ansimon-fullstack-fixed.zip`, 기존 파일 변경 비교는 `/workspace/work/ansimon-fixes.diff`에 있다. 지정된 `/codex/browser/projectless/0001-files-mentioned-by-the-user-uploaded-file-pointe/output`은 환경의 OS 쓰기 권한이 없어 생성할 수 없었다. 자동 승인 검토가 거절한 것이 아니라 파일시스템 권한 오류이며, 수정·테스트에는 영향이 없다.
