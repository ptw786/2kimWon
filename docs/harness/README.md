# 안심온 하네스 — 폴더 구조와 모듈 책임

"하네스"는 코드가 올라갈 틀이다. 어디에 무엇을 두는지, 모듈끼리 어떻게 말하는지를 먼저 고정하고 그 안에서만 기능을 채운다.
기능 목록은 [기능-명세.md](기능-명세.md), 규약은 [코딩-규약.md](코딩-규약.md), 일정은 [구현-계획.md](구현-계획.md), 사람·AI 역할은 [AI-개발-분배.md](AI-개발-분배.md).

## 1. 한 장 구조

```
2팀/  (GitHub ptw786/2kimWon)
├── apps/
│   ├── api/              FastAPI + SQLite + Ollama        :8010  서버·판정·대화 엔진
│   ├── web/              React + Vite + TS                :5180  소개 + 생활지원사 웹
│   └── app/              React + Vite + TS + PWA          :5181  어르신 앱
├── packages/
│   ├── contracts/        CONTRACT.md — 웹·앱·서버 공통 API 약속 (바꿀 때 여기부터)
│   └── design/           tokens.css(색·글꼴·간격 단 하나의 원본) · preview-v3.html(승인 시안)
├── docs/
│   ├── harness/          이 문서 묶음 (구조 · 기능 명세 · 규약 · 계획 · AI 분배)
│   ├── adr/              결정 기록 ADR-NNNN-제목.md
│   ├── 판정규칙.md        판정 규칙 r2 (사람이 읽는 원본 — 값은 rules.yaml)
│   ├── 디자인.md          디자인 규칙과 패턴 출처
│   └── 평가/              날짜를 붙인 평가 결과 (.md + .json 쌍)
├── scripts/              dev-up.sh(세 서버 실행) · test-all.sh(전체 검사)
├── .claude/agents/       역할별 AI 에이전트 정의 (api · ai · web · app · 디자인 · 평가 · 제안서)
├── (minse 브랜치) ansimon-fullstack/   이전 버전 (팀원 통합본, 참고용 — main에는 없음)
├── AI혁신_경진대회_이김WON.hwp   제안서
├── CLAUDE.md = AGENTS.md  꼭 지킬 것 요약 (사람·AI 공통)
└── README.md
```

경계 규칙 네 가지.
1. **`apps/api/app/domain/`은 순수 함수만.** 네트워크·DB·파일·현재 시각 금지(시각은 인자로 받는다). 판정 규칙·대화 상태 기계가 모두 여기 있다.
2. **외부 호출은 `apps/api/app/services/` 어댑터로만.** 지금은 Ollama(`llm.py`) 하나. 복지서비스 데이터(F11)도 `services/welfare.py`로 들어온다.
3. **웹·앱은 서로 import하지 않는다.** 공유하는 것은 `packages/contracts`(약속)와 `packages/design/tokens.css`(디자인)뿐이다. 서버와는 `/api`로만 말한다.
4. **LLM은 DB 쓰기 트랜잭션 밖에서만 부른다.** 읽기 → 판단·AI → 짧은 쓰기 순서(`calls.py`).

## 2. apps/api

```
apps/api/app/
├── main.py            앱 조립, 라우터 등록, 스케줄러·모델 예열 시작
├── config.py          환경변수 (ANSIMON_DB · OLLAMA_HOST · ANSIMON_MODEL · ANSIMON_LLM · ANSIMON_SCHEDULER · ANSIMON_DEMO)
├── db.py              SQLite 연결·스키마·쓰기 트랜잭션 표시(in_write_tx)
├── seed.py            가상 어르신 6명 + 지난 6일 기록 (F0)
├── calls.py           통화 진행 오케스트레이션 — 발신·응답·턴·종료·요약·스케줄러 (F1·F3·F6)
├── routers/           HTTP. 얇게: 검증 → calls/domain 호출 → 응답
│   ├── staff.py       /api/staff/*  (웹)
│   ├── elder.py       /api/elder/*  (앱)
│   └── system.py      /api/health
├── domain/            순수 로직 — 아래 §4 "규칙의 집"
└── services/
    ├── llm.py         LLMClient · OllamaClient · RuleOnly · FakeLLM
    └── prompts/       extract.md · empathy.md · summary.md (프롬프트 원문)
```

## 3. apps/web · apps/app (화면)

두 앱 모두 같은 틀을 쓴다.

```
src/
├── app/          진입점 · 라우트 · 레이아웃 · 전역 스타일
├── features/     화면(기능) 단위 폴더. 폴더 이름 = 기능-명세의 화면
├── shared/       api 클라이언트 · 타입(CONTRACT.md 그대로) · 상태 라벨 · 공용 컴포넌트
└── mock/         VITE_MOCK=1 일 때 쓰는 가짜 API (서버 없이 화면 개발)
```

| 앱 | features/ | 기능 ID |
|---|---|---|
| web | `landing` | F10 |
| web | `queue`(오늘 확인 순서) · `call-detail` · `residents` · `calls` · `rules` | F7 |
| web | `live`(실시간 통화 · QR) | F8 |
| app | `identity`(QR로 열기 · 어르신 선택) | F8 |
| app | `call`(벨 · 통화 · 음성 · 벨소리) | F1 · F2 |
| app | `home` · `records` · `settings` | F9 |

## 4. 규칙의 집 — 표 하나 = 함수 하나 = 테스트 하나

| 판정규칙.md 표 | domain 함수 | 테스트 |
|---|---|---|
| §2 항목별 상태 (양호·주의·위험·미확인) | `keywords.extract(topic, text)` · LLM은 `services/llm.extract` | `test_rules.py` 상태·부정 표현·짧은 대답 |
| §3 안전 신호 5분류 | `safety.detect(text)` | `test_rules.py` 16가지 |
| §4 A 오늘 통화 · B 추세 · C 연락 | `scoring.assess(...)` · `trend_streak` · `contact_reasons` | `test_rules.py` 점수 구성·상한 |
| §5 단계 | `scoring.assess` → grade | `test_rules.py` 경계값 |
| 대화 다음 행동 (다음·반복·다시 묻기·안전·끝) | `dialogue.decide(state, ...)` | `test_regressions.py` |
| AI 결과와 규칙 결과 합치기 | `dialogue.combine_extractions(...)` | `test_llm_fallback.py` |
| §7 가설 검증 | — | `test_rules_sensitivity.py` → `docs/평가/` |

값(점수·기준선·라벨)은 `domain/rules.yaml` 한 곳에만 있다. 바꾸면 `판정규칙.md`와 `rule_version`을 같이 고친다.

## 5. 실행

```bash
scripts/dev-up.sh        # WSL: api(8010) · web(5180) · app(5181) 동시 실행, Ctrl+C로 함께 종료
scripts/test-all.sh      # pytest · web build · app build+test
```
Windows PowerShell 명령과 환경변수는 각 앱 README에 있다. Ollama는 Windows에서 돌고, WSL에서는 기본 게이트웨이:11434로 접속한다(`OLLAMA_HOST`가 있으면 그 값).

| 주소 | 화면 |
|---|---|
| http://127.0.0.1:5180 | 소개 |
| http://127.0.0.1:5180/staff | 생활지원사 웹 |
| http://127.0.0.1:5181/r/KY-01 | 김영자 어르신 앱 |
| http://127.0.0.1:8010/docs | API 문서 |

포트 5173·5174·5175·8787·4173은 이 컴퓨터의 다른 프로젝트가 쓰므로 피했다.
