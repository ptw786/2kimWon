# 검증한 GitHub 참고 프로젝트

아래 자료는 **기능과 아키텍처를 참고**한 프로젝트입니다. 저장소의 원본 소스 코드를 복사해 넣지는 않았습니다. 앱의 React 화면, Web Speech API 연결, FastAPI·SQLite 코드는 이 프로젝트용으로 새로 작성했습니다.

1. **React Twilio Phone** — https://github.com/philnash/react-twilio-phone
   - 기능: React에서 수신·거절·종료, 통화 중 제어.
   - 안심온 적용: `frontend/src/App.jsx`의 전화 수신·거절·통화 중·종료 상태 UX.
   - 차이점: Twilio 통신 API 연동을 가져오지 않았고 실제 전화번호 통화는 지원하지 않습니다.
   - 라이선스: MIT. 원본 코드 재사용 시 라이선스 고지 유지 필요.

2. **react-speech-recognition** — https://github.com/JamesBrill/react-speech-recognition
   - 기능: React에서 브라우저 음성인식의 시작, 종료, 텍스트 변환 관리.
   - 안심온 적용: `frontend/src/App.jsx`의 음성인식 시작/종료/오류 시 입력창 폴백 흐름.
   - 차이점: 패키지를 직접 설치하지 않고 표준 Web Speech API를 직접 호출해 의존성을 줄임.
   - 라이선스: MIT. 라이브러리 소스를 직접 재사용할 경우 고지 유지 필요.

3. **Full Stack FastAPI Template** — https://github.com/fastapi/full-stack-fastapi-template
   - 기능: FastAPI 백엔드 / React+Vite 프론트 / DB / REST 인터페이스의 풀스택 구조.
   - 안심온 적용: `backend/` 및 `frontend/` 폴더 분리, REST API와 테스트 구성.
   - 차이점: 원본 PostgreSQL/SQLModel/Docker/JWT 대신 초보자가 쉽게 시작하도록 표준 sqlite3를 활용.
   - 라이선스: MIT. 원본 코드를 재사용하면 고지 유지 필요.

**중요:** 위 세 프로젝트는 유효한 기술적 영감과 설계 참고 사례이며, 실제 코드를 복제하지 않았습니다. 자체 구현을 그 프로젝트의 공식 배포판이라고 주장하지 않습니다.
