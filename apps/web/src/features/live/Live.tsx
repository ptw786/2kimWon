// ④ 실시간 통화 — 한 화면 시연: 왼쪽 실제 폰(어르신 앱 iframe) + 아래 전화 걸기·QR · 오른쪽 들어오는 대화 레인(함께반 질문함 패턴)
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Icon } from '../../shared/icons';
import { PhoneFrame, widthForHeight } from '../../shared/PhoneFrame';
import { QrCode } from '../../shared/QrCode';
import { useStaff } from '../../shared/StaffLayout';
import { Empty, ItemBadge } from '../../shared/ui';
import { api } from '../../shared/api';
import { APP_URL, appUrlIsLocal, elderUrl } from '../../shared/config';
import { SOURCE, TOPICS, TOPIC_LABEL, TOPIC_SHORT, isLive } from '../../shared/status';
import { hhmmss, msLabel } from '../../shared/time';
import { useAppReachable } from '../../shared/useAppReachable';
import { usePoll } from '../../shared/usePoll';
import type { CallDetail, LiveCall, Turn } from '../../shared/types';

/** 화면 높이에 맞춘 폰 폭: 폰 + 아래 '전화 걸기' 두 줄이 한 화면에 들어오게 */
function usePhoneWidth() {
  const calc = () => {
    if (window.innerWidth <= 820) return Math.min(300, window.innerWidth - 72);
    const h = Math.max(440, Math.min(700, window.innerHeight - 330));
    return widthForHeight(h);
  };
  const [w, setW] = useState(calc);
  useEffect(() => {
    const on = () => setW(calc());
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return w;
}

function PhoneWaiting({ state, name }: { state: 'checking' | 'up' | 'down'; name: string }) {
  return (
    <div className="pf-wait">
      <span className="ic" aria-hidden>☎</span>
      <b>{name ? `${name} 어르신 폰` : '어르신 폰'}</b>
      <span>{state === 'down' ? '어르신 앱(5181)이 꺼져 있어요. 앱을 켜면 여기서 직접 받아 볼 수 있어요.' : '어르신 앱을 여는 중이에요…'}</span>
    </div>
  );
}

export function LivePage() {
  const { dash, callResident } = useStaff();
  const [params, setParams] = useSearchParams();
  const live = usePoll(() => api.get<{ calls: LiveCall[] }>('/staff/live'), 2000);
  const calls = live.data?.calls ?? [];
  const paramId = Number(params.get('call')) || null;
  const lastId = useRef<number | null>(null);
  const callId = paramId ?? calls[0]?.id ?? lastId.current;
  useEffect(() => {
    if (callId) lastId.current = callId;
  }, [callId]);
  const detail = usePoll(callId ? () => api.get<CallDetail>(`/staff/calls/${callId}`) : null, 2000, callId);
  const c = detail.data;

  const rows = dash.data?.residents ?? [];
  const [pickId, setPickId] = useState<number | null>(null);
  // 통화가 진행 중이면 폰은 그 어르신 화면을 보여 준다
  const liveRid = c && isLive(c.status) ? c.resident_id : null;
  useEffect(() => {
    if (liveRid) setPickId(liveRid);
  }, [liveRid]);
  const pick = rows.find((r) => r.id === pickId) ?? rows.find((r) => r.today.status === 'not_called') ?? rows[0] ?? null;
  const pickLive = pick ? isLive(pick.today.status) : false;

  const app = useAppReachable();
  const phoneW = usePhoneWidth();
  const appSrc = pick && app === 'up' ? `${elderUrl(pick.code)}?device=1` : null;
  const openUrl = pick ? elderUrl(pick.code) : '';

  return (
    <div className="page live-page">
      <div className="ph compact">
        <h1>실시간 통화</h1>
        <p>왼쪽은 어르신 폰에 실제로 뜨는 앱이에요. 전화를 걸고 폰에서 답하면, 오가는 말이 2초마다 오른쪽에 들어와요.</p>
      </div>
      <div className="live">
        <section className="lv-left" aria-label="어르신 폰" style={{ '--lw': `${Math.max(320, phoneW + 64)}px` } as CSSProperties}>
          <div className="lv-stage">
            <PhoneFrame width={phoneW} src={appSrc} title={pick ? `${pick.name} 어르신 앱 (실제 작동 화면)` : '어르신 앱'} fallback={<PhoneWaiting state={app} name={pick?.name ?? ''} />} />
          </div>
          <div className="lv-ctrl">
            <label className="field">
              <span className="sr">전화 걸 어르신</span>
              <select value={pick?.id ?? ''} onChange={(e) => setPickId(Number(e.target.value))} aria-label="전화 걸 어르신" disabled={!rows.length}>
                {rows.map((r) => <option key={r.id} value={r.id}>{r.name} · {r.today.status_label}</option>)}
              </select>
            </label>
            <button type="button" className="btn p block" disabled={!pick || pickLive} onClick={() => pick && void callResident(pick.id, pick.name)}>
              {pick && pickLive ? `${pick.name} 어르신과 통화 중` : '☎ 이 어르신께 전화 걸기'}
            </button>
            {pick && (
              <div className="lv-qr">
                <QrCode value={openUrl} size={76} label={`${pick.name} 어르신 앱 QR (${pick.code})`} />
                <div>
                  <b>내 폰으로 열기</b>
                  <span className="subtle">폰 카메라로 찍으면 {pick.name} 어르신 앱이 열려요 · <span className="code">{pick.code}</span></span>
                  {appUrlIsLocal && (
                    <details>
                      <summary>폰에서 안 열리면?</summary>
                      <p>지금 주소({new URL(APP_URL).host})는 이 PC에서만 열려요. 같은 와이파이의 폰으로 찍으려면 웹을 켤 때 VITE_APP_PUBLIC_URL에 PC 주소(예: http://192.168.0.12:5181)를 넣어 주세요.</p>
                    </details>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>

        <div className="lane-slot">
          <section className="lane" aria-label="실시간 대화">
            {calls.length > 1 && (
              <div className="tabs" role="tablist" aria-label="진행 중인 통화">
                {calls.map((x) => (
                  <button key={x.id} type="button" role="tab" aria-selected={x.id === callId} className={`btn ${x.id === callId ? 'g' : 'o'}`} onClick={() => setParams({ call: String(x.id) })}>
                    {x.resident_name} · {x.status_label}
                  </button>
                ))}
              </div>
            )}
            {c ? (
              <Lane c={c} />
            ) : callId && detail.loading ? (
              <div className="lane-empty"><Empty icon="…" title="통화를 불러오는 중이에요" /></div>
            ) : callId && detail.error ? (
              <div className="lane-empty"><Empty icon="⚠" title="통화를 불러오지 못했어요" reason={detail.error} /></div>
            ) : (
              <LaneIdle />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function LaneIdle() {
  return (
    <div className="lane-idle" role="status">
      <span className="arrow" aria-hidden><Icon name="arrowLeft" size={28} /></span>
      <b>왼쪽 폰으로 전화를 걸어 보세요</b>
      <p>‘이 어르신께 전화 걸기’를 누르면 폰에서 벨이 울려요. 폰에서 받아 답하면 대화가 여기에 실시간으로 쌓여요.</p>
      <ol className="idle-steps">
        <li><i>1</i>전화 걸기</li>
        <li><i>2</i>폰에서 받기</li>
        <li><i>3</i>대화가 여기로</li>
      </ol>
    </div>
  );
}

function Lane({ c }: { c: CallDetail }) {
  const seen = useRef<{ id: number; n: number } | null>(null);
  const body = useRef<HTMLDivElement>(null);
  const [fresh, setFresh] = useState<Set<number>>(new Set());
  useEffect(() => {
    const prev = seen.current;
    const n = c.turns.length;
    const from = prev && prev.id === c.id ? prev.n : Math.max(0, n - 1);
    seen.current = { id: c.id, n };
    const el = body.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: prev ? 'smooth' : 'auto' });
    if (n <= from) return;
    const add = new Set(Array.from({ length: n - from }, (_, i) => from + i));
    setFresh(add);
    const t = window.setTimeout(() => setFresh(new Set()), 2500);
    return () => window.clearTimeout(t);
  }, [c.id, c.turns.length]);

  const live = isLive(c.status);
  const stateText = c.status === 'ringing' ? '벨 울리는 중' : c.status === 'in_progress' ? '통화 중' : '통화 끝';
  // 진행 점: 끝난 질문은 채움, 지금 질문은 테두리
  const doneN = c.status === 'completed' ? c.step.total : Math.max(0, c.step.index - 1);

  return (
    <>
      <div className="lh">
        <b>{c.resident_name} 어르신 · {stateText}</b>
        {c.status === 'in_progress' && <span className="pill p-live"><i className="dot blink" />실시간 연결</span>}
        {c.status === 'ringing' && <span className="pill p-live"><span aria-hidden>♪</span>벨 울리는 중</span>}
        {!live && <span className="pill p-rule"><span aria-hidden>■</span>통화 끝 · {c.status_label}</span>}
      </div>
      <ol className="steps5" aria-label={`질문 ${doneN} / ${c.step.total} 완료`}>
        {TOPICS.map((t, i) => {
          const st = i < doneN ? 'done' : live && i === c.step.index - 1 ? 'now' : '';
          return <li key={t} className={st}><i aria-hidden>{st === 'done' ? '✓' : i + 1}</i>{TOPIC_SHORT[t]}{st === 'now' && <span className="sr"> (지금 묻는 중)</span>}</li>;
        })}
      </ol>
      <div className="lane-body" ref={body} aria-live="polite">
        {c.turns.length === 0 && (
          <div className="lane-empty">
            <Empty icon="♪" title={c.status === 'ringing' ? '어르신 폰에서 벨이 울리고 있어요' : '대화가 없어요'} reason={c.status === 'ringing' ? '왼쪽 폰에서 ‘받기’를 눌러 보세요. 30초 안에 받지 않으시면 미응답으로 기록돼요.' : c.status_label} />
          </div>
        )}
        {c.turns.map((t, i) => <Bubble key={i} t={t} fresh={fresh.has(i)} />)}
      </div>
      {!live && (
        <div className="lane-foot">
          <Link to={`/staff/calls/${c.id}`} className="btn p">통화 상세 보기 ›</Link>
          <Link to="/staff" className="btn o">오늘 확인 순서로</Link>
        </div>
      )}
    </>
  );
}

function Bubble({ t, fresh }: { t: Turn; fresh: boolean }) {
  const el = t.role === 'elder';
  // ai 턴의 ms: 이 응답을 만드는 데 든 AI 시간 합, null이면 규칙만 사용. 이전 서버(필드 없음)면 표시하지 않는다.
  const aiTime = !el && t.ms !== undefined ? (t.ms === null ? '규칙' : `AI ${msLabel(t.ms)}`) : null;
  const silent = el && !t.text.trim();
  return (
    <div className={`bub${el ? ' el' : ''}`}>
      <span className="who">{el ? '어르신' : '안심온'}</span>
      <div className="body">
        <div className={`tx${fresh ? ' arrive' : ''}${silent ? ' silent' : ''}`}>{silent ? '(대답 없음)' : t.text}</div>
        <div className="tm">
          {fresh ? '방금' : hhmmss(t.at)}
          {el && t.source && ` · ${SOURCE[t.source]}`}
          {aiTime && ` · ${aiTime}`}
          {t.topic && !el && <span className="subtle">· {TOPIC_LABEL[t.topic]}</span>}
          {t.judged?.map((j, k) => <ItemBadge key={k} status={j.status} topic={j.topic} />)}
        </div>
      </div>
    </div>
  );
}
