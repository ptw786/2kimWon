// ① 소개 — 왼쪽 메시지(7) + 오른쪽 실제로 작동하는 폰(5, 실시간 통화 화면과 같은 프레임) · 1→4 흐름 카드·QR 카드(함께반)
// 아래: 통화 한 번의 다섯 질문 타임라인 + 절제된 숫자 세 개(Pudding·NYT 편집형 숫자, Linear 여백)
import { Link } from 'react-router-dom';
import { Icon, type IconName } from '../../shared/icons';
import { PhoneFrame } from '../../shared/PhoneFrame';
import { QrCode } from '../../shared/QrCode';
import { ItemBadge, NeedChip } from '../../shared/ui';
import { elderUrl } from '../../shared/config';
import { TOPIC_LABEL } from '../../shared/status';
import { useAppReachable } from '../../shared/useAppReachable';
import type { ItemStatus, Topic } from '../../shared/types';

const DEMO_CODE = 'KY-01';
const FLOW: [string, string][] = [
  ['안부전화', '정해진 시간에 벨이 울려요'],
  ['대화', '다섯 가지를 쉬운 말로 여쭤요'],
  ['AI 판정', '말씀을 인용해 상태를 정리해요'],
  ['확인', '생활지원사가 순서대로 챙겨요'],
];

// 질문 문구는 apps/api/app/domain/questions.py QUESTIONS 그대로, 점수는 docs/판정규칙.md(주의 5 · 위험 10)
const ASK: { topic: Topic; icon: IconName; q: string; a: string; st: ItemStatus; pts: number; need?: boolean }[] = [
  { topic: 'body', icon: 'body', q: '오늘 몸은 좀 어떠세요?', a: '허리가 좀 쑤셔', st: 'caution', pts: 5 },
  { topic: 'meal', icon: 'meal', q: '오늘 식사는 챙겨 드셨어요?', a: '이틀째 못 먹었어', st: 'risk', pts: 10 },
  { topic: 'sleep', icon: 'sleep', q: '어젯밤에는 잠을 잘 주무셨어요?', a: '잘 잤어요', st: 'good', pts: 0 },
  { topic: 'med', icon: 'med', q: '드시는 약은 오늘 챙겨 드셨어요?', a: '네, 먹었어요', st: 'good', pts: 0 },
  { topic: 'mood', icon: 'mood', q: '오늘 기분은 좀 괜찮으세요?', a: '아무도 안 와서 외로워', st: 'risk', pts: 10, need: true },
];

function RingingScreen() {
  return (
    <div className="ring">
      <small>전화가 왔어요</small>
      <h3>안심온 돌봄전화</h3>
      <p>김영자 어르신,<br />오늘도 안녕하세요</p>
      <div className="pulse" aria-hidden>♥</div>
      <div className="acts" aria-hidden>
        <div className="act"><div className="circle no">✕</div>안 받기</div>
        <div className="act"><div className="circle yes">☎</div>받기</div>
      </div>
    </div>
  );
}

export function LandingPage() {
  const app = useAppReachable();
  const url = elderUrl(DEMO_CODE);

  return (
    <div className="landing">
      <section className="hero">
        <div className="hin">
          <nav className="hnav" aria-label="소개 메뉴">
            <span className="logo"><i aria-hidden>♥</i>안심온</span>
            <span className="links">
              <a href="#how">작동 방식</a>
              <Link to="/staff">생활지원사 화면</Link>
              <Link to="/staff/principles">근거와 원칙</Link>
            </span>
            <Link to="/staff" className="cta">생활지원사 화면 열기</Link>
          </nav>
          <div className="hgrid">
            <div className="hcopy">
              <span className="pill">독거 어르신 AI 안부전화 · 노인맞춤돌봄 지원</span>
              <h1 className="serif">전화 한 통으로<br />시작하는 <em>매일의 안심</em></h1>
              <p className="sub">어르신은 전화를 받기만 하면 됩니다. AI가 식사·수면·몸 상태를 여쭙고,{' '}<br />생활지원사는 오늘 먼저 챙길 분을 한눈에 봅니다.</p>
              <ol className="flowd">
                {FLOW.map(([h, d], i) => <li key={h}><b><i>{i + 1}</i>{h}</b><small>{d}</small></li>)}
              </ol>
              <div className="qrcard">
                <QrCode value={url} size={96} label={`어르신 앱 QR (${DEMO_CODE})`} />
                <div>
                  <b>내 폰으로 전화 받아 보기</b>
                  <span>QR을 찍고 홈 화면에 추가하면 앱처럼 열려요</span>
                  <div className="code">{DEMO_CODE}</div>
                </div>
              </div>
            </div>
            <div className="stage">
              <PhoneFrame width={300} src={app === 'up' ? `${url}?device=1` : null} title="어르신 앱 (실제 작동 화면)" fallback={<RingingScreen />} />
              <span className="note">{app === 'up' ? '지금 실제로 작동하는 화면이에요 · 그대로 눌러 보세요' : app === 'down' ? '어르신 앱(5181)이 꺼져 있어 예시 화면이에요' : '어르신 앱에 연결하는 중이에요…'}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="how" id="how">
        <div className="how-in">
          <div className="how-hd">
            <span className="eyebrow">통화 한 번 · 약 3분</span>
            <h2 className="serif">다섯 가지를 여쭙고, 말씀 그대로 남겨요</h2>
            <p className="d">어르신이 듣는 질문과 대답 예시예요. 대답마다 상태와 점수를 정하고, 근거로 그 말씀을 붙여요.</p>
          </div>
          <ol className="ask">
            {ASK.map((s, i) => (
              <li key={s.topic}>
                <div className="ask-node"><i aria-hidden><Icon name={s.icon} size={24} /></i><span>{String(i + 1).padStart(2, '0')} · {TOPIC_LABEL[s.topic]}</span></div>
                <p className="ask-q">“{s.q}”</p>
                <p className="ask-a"><span className="sr">대답 예시: </span>{s.a}</p>
                <div className="ask-j">
                  <ItemBadge status={s.st} />
                  <span className="subtle">{s.pts ? `+${s.pts}점` : '0점'}</span>
                  {s.need && <NeedChip need={{ type: 'loneliness', label: '외로움' }} />}
                </div>
              </li>
            ))}
          </ol>
          <p className="ask-sum">이 통화는 <b>25점 · 우선 확인</b>이 돼요. 답을 못 들으면 두 번까지 다시 여쭙고, 그래도 어려우면 ‘미확인’으로 남겨 생활지원사가 직접 확인해요.</p>

          <dl className="facts">
            <div><dt>약 <b>1</b>초</dt><dd>대답을 판정하고 공감 한마디를 만드는 시간<br /><span className="subtle">로컬 AI 실측(2026-11-14) · 실패하면 규칙이 대신해요</span></dd></div>
            <div><dt><b>0</b>회</dt><dd>어르신이 할 설치·로그인<br /><span className="subtle">초록 버튼만 누르시면 돼요</span></dd></div>
            <div><dt><b>7</b>일</dt><dd>추세로 판단하는 기간<br /><span className="subtle">사흘째 식사를 거르시면 점수를 올려요</span></dd></div>
          </dl>
        </div>
      </section>
      <footer className="lfoot">가상 데이터로 만든 시연이에요. 대화는 이 컴퓨터의 로컬 AI(Ollama)에서만 처리하고, 모든 판정에 어르신 말씀을 그대로 붙여요. 점수는 확인 순서를 돕는 참고값이며 의료 판단이 아니에요.</footer>
    </div>
  );
}
