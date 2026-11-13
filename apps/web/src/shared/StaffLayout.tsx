// 생활지원사 화면 공통 셸: 240px 사이드바(그룹 라벨) + 하단 AI 연결 카드 + 상단 상태칩·리셋·다크 토글 (함께반·TTA 패턴)
import { useCallback, useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import { ApiError, api, errMsg, useApiDown } from './api';
import { IS_MOCK } from './config';
import { Icon } from './icons';
import { nowHeadline } from './time';
import { usePoll, type Poll } from './usePoll';
import type { CallSummary, Dashboard, Health } from './types';

export type StaffCtx = {
  dash: Poll<Dashboard>;
  health: Health | null;
  toast: (msg: string) => void;
  callResident: (id: number, name: string) => Promise<void>;
};
export const useStaff = () => useOutletContext<StaffCtx>();

const CRUMB: [RegExp, string, string][] = [
  [/^\/staff\/?$/, '오늘', '오늘 확인 순서'],
  [/^\/staff\/live/, '오늘', '실시간 통화'],
  [/^\/staff\/residents/, '어르신', '어르신 목록'],
  [/^\/staff\/calls\/\d+/, '어르신', '통화 상세'],
  [/^\/staff\/calls/, '어르신', '통화 기록'],
  [/^\/staff\/rules/, '근거', '판정 기준'],
  [/^\/staff\/principles/, '근거', '데이터 원칙'],
];

function readTheme(): 'light' | 'dark' {
  try {
    return localStorage.getItem('ansimon-theme') === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(readTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem('ansimon-theme', theme);
    } catch {
      /* 저장소를 못 쓰면 이번 화면에서만 적용 */
    }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))] as const;
}

export function StaffLayout() {
  const loc = useLocation();
  const nav = useNavigate();
  const down = useApiDown();
  const [theme, toggleTheme] = useTheme();
  const dash = usePoll(() => api.get<Dashboard>('/staff/dashboard'), 5000);
  const healthPoll = usePoll(() => api.get<Health>('/health'), 15000);
  const health = healthPoll.data;
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [more, setMore] = useState(false);
  useEffect(() => setMore(false), [loc.pathname]);
  useEffect(() => {
    if (!more) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMore(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [more]);

  const toast = useCallback((m: string) => setToastMsg(m), []);
  useEffect(() => {
    if (!toastMsg) return;
    const t = window.setTimeout(() => setToastMsg(null), 3200);
    return () => window.clearTimeout(t);
  }, [toastMsg]);

  const callResident = useCallback(
    async (id: number, name: string) => {
      try {
        const c = await api.post<CallSummary>(`/staff/residents/${id}/call`);
        toast(`${name} 어르신께 전화를 걸었어요. 앱에서 벨이 울려요.`);
        void dash.refresh();
        nav(`/staff/live?call=${c.id}`);
      } catch (e) {
        toast(errMsg(e));
        if (e instanceof ApiError && e.status === 409) nav('/staff/live');
      }
    },
    [dash, nav, toast],
  );

  async function reset() {
    setMore(false);
    if (!window.confirm('시연 데이터를 처음 상태로 되돌릴까요?\n오늘 통화와 확인 기록이 모두 시드 데이터로 바뀌어요.')) return;
    try {
      await api.post('/staff/demo/reset');
      toast('시연 데이터를 처음 상태로 되돌렸어요.');
      void dash.refresh();
    } catch (e) {
      toast(errMsg(e));
    }
  }

  const crumb = CRUMB.find(([re]) => re.test(loc.pathname)) ?? CRUMB[0];
  const counts = dash.data?.counts;
  const badge = counts ? counts.urgent + counts.today : 0;
  const virtual = dash.data?.residents.some((r) => r.is_virtual) ?? false;
  const llm = health?.llm;
  const aiOn = !!llm && llm.mode === 'ollama' && llm.reachable;
  const modelShort = llm?.model?.split(':')[0] ?? '';
  const done = dash.data?.residents.filter((r) => r.today.status === 'completed').length ?? 0;

  const chips = (
    <>
      {IS_MOCK && <span className="pill p-rule">예시 화면(목업)</span>}
      {virtual && <span className="pill p-virt">가상 데이터</span>}
      {health && (aiOn ? <span className="pill p-ai"><i className="dot" />AI 판정 켜짐</span> : <span className="pill p-rule"><i className="dot" />규칙 판정 모드</span>)}
    </>
  );
  const aiCard = !health && healthPoll.error ? (
    <><b className="off"><i className="dot" />AI 상태를 알 수 없어요</b>서버에 연결되면 다시 보여 드려요.</>
  ) : !health ? (
    <><b className="off"><i className="dot" />AI 상태 확인 중</b>서버에 물어보고 있어요.</>
  ) : aiOn ? (
    <><b><i className="dot" />로컬 AI 연결됨 · {modelShort}</b>{llm?.model} · Ollama<br />연결이 끊기면 규칙 판정으로 자동 전환돼요.</>
  ) : (
    <><b className="rule"><i className="dot" />규칙 판정 모드</b>로컬 AI(Ollama)에 연결되지 않아 키워드 규칙으로 판정해요.</>
  );
  const moreOn = /^\/staff\/(rules|principles)/.test(loc.pathname);

  return (
    <div className="shell">
      <aside className="side">
        <Link to="/" className="logo" aria-label="안심온 소개로"><i aria-hidden>♥</i>안심온</Link>
        <nav aria-label="생활지원사 메뉴">
          <h6>오늘</h6>
          <NavLink to="/staff" end><Icon name="today" />오늘 확인 순서{badge > 0 && <span className={`n${counts?.urgent ? ' u' : ''}`} aria-label={`즉시 확인과 우선 확인 ${badge}명`}>{badge}</span>}</NavLink>
          <NavLink to="/staff/live"><Icon name="live" />실시간 통화</NavLink>
          <h6>어르신</h6>
          <NavLink to="/staff/residents"><Icon name="people" />어르신 목록</NavLink>
          <NavLink to="/staff/calls"><Icon name="list" />통화 기록</NavLink>
          <h6>근거</h6>
          <NavLink to="/staff/rules"><Icon name="rules" />판정 기준</NavLink>
          <NavLink to="/staff/principles"><Icon name="shield" />데이터 원칙</NavLink>
        </nav>
        <div className="side-today" aria-label="오늘 요약">
          <small>{nowHeadline().split(' · ')[0]}</small>
          {counts ? (
            <>
              <div className="st-row"><span>통화 완료</span><b>{done}<em>/{counts.total}</em></b></div>
              <div className="st-row"><span>먼저 챙길 분</span><b>{badge}<em>명</em></b></div>
            </>
          ) : (
            <div className="st-row"><span>불러오는 중</span></div>
          )}
        </div>
        <div className="foot">{aiCard}</div>
      </aside>

      <div className="main">
        <div className="top">
          <Link to="/" className="logo m-logo" aria-label="안심온 소개로"><i aria-hidden>♥</i>안심온</Link>
          <span className="crumb">{crumb[1]} › <b>{crumb[2]}</b></span>
          <span className="m-title">{crumb[2]}</span>
          <div className="r">
            <span className="chips">{chips}</span>
            <button type="button" className="icon-btn d-only" onClick={reset} title="데모 리셋" aria-label="데모 리셋">↺</button>
            <button type="button" className="icon-btn" onClick={toggleTheme} title={theme === 'dark' ? '밝은 화면' : '어두운 화면'} aria-label={theme === 'dark' ? '밝은 화면으로' : '어두운 화면으로'}>{theme === 'dark' ? '☀' : '☾'}</button>
          </div>
        </div>
        {down && (
          <div className="banner" role="alert"><span aria-hidden>⚠</span>서버에 연결할 수 없어요. 127.0.0.1:8010에서 API가 켜져 있는지 확인해 주세요.</div>
        )}
        <Outlet context={{ dash, health, toast, callResident } satisfies StaffCtx} />
        <div className="foot-note">이 화면의 어르신·통화는 모두 가상 데이터예요. 점수는 확인 순서를 돕는 참고값이며 의료 판단이 아니에요. 나이·성별은 점수에 넣지 않아요.</div>
      </div>
      {/* 좁은 화면: 아래 탭 막대(오늘·실시간·어르신·기록·더보기) — 모든 메뉴가 한 번에 닿는다 */}
      <nav className="tabbar" aria-label="생활지원사 메뉴(아래)">
        <NavLink to="/staff" end><Icon name="today" />오늘{badge > 0 && <span className={`n${counts?.urgent ? ' u' : ''}`}>{badge}</span>}</NavLink>
        <NavLink to="/staff/live"><Icon name="live" />실시간</NavLink>
        <NavLink to="/staff/residents"><Icon name="people" />어르신</NavLink>
        <NavLink to="/staff/calls"><Icon name="list" />기록</NavLink>
        <button type="button" className={moreOn || more ? 'active' : ''} aria-expanded={more} aria-controls="more-sheet" onClick={() => setMore((v) => !v)}><Icon name="more" />더보기</button>
      </nav>
      {more && (
        <div className="sheet-bg" onClick={() => setMore(false)}>
          <div className="sheet" id="more-sheet" role="dialog" aria-label="더보기" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-h"><b>더보기</b><button type="button" className="icon-btn" aria-label="닫기" onClick={() => setMore(false)}>✕</button></div>
            <Link to="/staff/rules" className="sheet-link"><Icon name="rules" />판정 기준<span aria-hidden>›</span></Link>
            <Link to="/staff/principles" className="sheet-link"><Icon name="shield" />데이터 원칙<span aria-hidden>›</span></Link>
            <div className="sheet-chips">{chips}</div>
            <div className="sheet-ai">{aiCard}</div>
            <button type="button" className="btn o block" onClick={reset}>↺ 데모 리셋</button>
          </div>
        </div>
      )}
      {toastMsg && <div className="toast" role="status">{toastMsg}</div>}
    </div>
  );
}
