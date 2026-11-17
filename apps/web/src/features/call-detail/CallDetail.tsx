// ③ 통화 상세 — TTA 3단: 오늘 통화 큐 · 세로 타임라인(질문마다 판정 칩) · 속성 패널(점수 구성 · AI 실행 기록)
import { useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { CheckModal } from '../../shared/CheckModal';
import { useStaff } from '../../shared/StaffLayout';
import { CallBadge, Empty, GradeBadge, ItemBadge, Loading, NeedChip, uniqNeeds } from '../../shared/ui';
import { WelfarePanel } from '../../shared/WelfarePanel';
import { api } from '../../shared/api';
import { AI_STEP, GRADE, ORIGIN_TAG, TOPICS, TOPIC_LABEL, isLive } from '../../shared/status';
import { duration, hhmm, kstDate, monthDay, msLabel } from '../../shared/time';
import { usePoll } from '../../shared/usePoll';
import type { AiRun, CallDetail, CallSummary, ItemStatus, Need, Origin, Topic, Turn } from '../../shared/types';

type StepView = {
  topic: Topic;
  status: ItemStatus | null; // null = 이 질문까지 가지 못함
  origin: Origin;
  quote: string | null;
  said: string[];
  retries: number;
  reply: string | null;
  run: AiRun | null;
  needs: Need[];
};

function buildSteps(c: CallDetail): StepView[] {
  return TOPICS.map((topic) => {
    const idx = c.turns.map((t, i) => [t, i] as const).filter(([t]) => t.role === 'elder' && t.topic === topic);
    const asks = c.turns.filter((t) => t.role === 'ai' && t.topic === topic).length;
    const lastIdx = idx.length ? idx[idx.length - 1][1] : -1;
    const lastElder: Turn | undefined = idx.length ? idx[idx.length - 1][0] : undefined;
    const reply = lastIdx >= 0 ? c.turns.slice(lastIdx + 1).find((t) => t.role === 'ai')?.text ?? null : null;
    const judged = lastElder?.judged?.find((j) => j.topic === topic);
    const item = c.assessment?.items[topic];
    const run = lastElder
      ? c.ai_runs.find((r) => r.step === 'extract' && new Date(r.at).getTime() >= new Date(lastElder.at).getTime() - 1000 && new Date(r.at).getTime() - new Date(lastElder.at).getTime() < 15000) ?? null
      : null;
    return {
      topic,
      status: item?.status ?? judged?.status ?? (idx.length ? 'unknown' : null),
      origin: item?.origin ?? judged?.origin ?? 'none',
      quote: item?.quote ?? null,
      said: idx.map(([t]) => t.text),
      retries: Math.max(0, asks - 1),
      reply,
      run,
      needs: uniqNeeds(idx.flatMap(([t]) => t.needs ?? [])),
    };
  });
}

function Highlight({ text, quote }: { text: string; quote: string | null }) {
  const i = quote ? text.indexOf(quote) : -1;
  // 답 전체가 인용이면 칠하지 않는다(어느 부분이 근거인지 보여 줄 때만 강조)
  if (!quote || i < 0 || quote.trim() === text.trim()) return <>{text}</>;
  return <>{text.slice(0, i)}<mark>{quote}</mark>{text.slice(i + quote.length)}</>;
}

const DOT: Record<ItemStatus, string> = { good: 'ok', caution: '', risk: 'risk', unknown: '' };

/** AI 응답에서 다음 질문(마지막 물음 문장)을 떼고 공감 부분만 남긴다 */
function empathyOnly(text: string): string {
  const parts = text.split(/(?<=[.!?])\s+/);
  return parts.length > 1 && parts[parts.length - 1].endsWith('?') ? parts.slice(0, -1).join(' ') : text;
}

function headline(c: CallDetail): string {
  if (c.summary) return c.summary;
  switch (c.status) {
    case 'missed': return '전화를 받지 않으셨어요. 대화 기록이 없어요.';
    case 'declined': return '전화를 거절하셨어요.';
    case 'ringing': return '지금 어르신 앱에서 벨이 울리고 있어요.';
    case 'in_progress': return '지금 통화 중이에요. 답이 들어오는 대로 아래에 쌓여요.';
    case 'interrupted': return '통화가 중간에 끊겼어요. 들은 답까지만 판정했어요.';
    default: return '통화 요약이 아직 없어요.';
  }
}

export function CallDetailPage() {
  const { id } = useParams();
  const { toast, dash } = useStaff();
  const call = usePoll(() => api.get<CallDetail>(`/staff/calls/${id}`), 5000, id);
  const c = call.data;
  const date = c ? kstDate(new Date(c.created_at)) : kstDate();
  const inbox = usePoll(() => api.get<CallSummary[]>(`/staff/calls?date=${date}&limit=50`), 10000, date);
  const [checking, setChecking] = useState(false);
  const isToday = date === kstDate();
  const nav = useNavigate();

  return (
    <div className="three">
      <nav className="inbox" aria-label={isToday ? '오늘 통화' : `${monthDay(date)} 통화`}>
        <h4>{isToday ? '오늘 통화' : `${monthDay(date)} 통화`} <span className="count">{inbox.data?.length ?? '–'}건</span></h4>
        {/* 좁은 화면: 가로로 밀리는 카드 대신 고르기 하나 */}
        <label className="field other-call">
          다른 통화 보기
          <select value={id} onChange={(e) => nav(`/staff/calls/${e.target.value}`)} disabled={!inbox.data?.length}>
            {!inbox.data?.some((x) => String(x.id) === id) && <option value={id}>통화 #{id}</option>}
            {inbox.data?.map((x) => <option key={x.id} value={x.id}>{hhmm(x.started_at ?? x.created_at)} · {x.resident_name} · {x.assessment && x.status === 'completed' ? x.assessment.grade_label : x.status_label}</option>)}
          </select>
        </label>
        <div className="list">
          {inbox.data?.map((x) => {
            const dur = duration(x.started_at, x.ended_at);
            return (
              <Link key={x.id} to={`/staff/calls/${x.id}`} className={`ii${String(x.id) === id ? ' on' : ''}`} aria-current={String(x.id) === id ? 'page' : undefined}>
                <span className="nm"><b>{x.resident_name}</b>{x.assessment && x.status === 'completed' ? <GradeBadge grade={x.assessment.grade} label={x.assessment.grade_label} /> : <CallBadge status={x.status} />}</span>
                <small>{hhmm(x.started_at ?? x.created_at)}{dur ? ` · ${dur}` : ''} · {x.status_label}</small>
              </Link>
            );
          })}
          {inbox.data?.length === 0 && <div style={{ padding: '0 18px 16px' }}><Empty title="이 날 통화가 없어요" /></div>}
        </div>
      </nav>

      <section className="mid" aria-live="polite">
        {!c && call.loading && <Loading rows={3} />}
        {!c && call.error && (
          <Empty icon="⚠" title="통화를 불러오지 못했어요" reason={call.error} action={<Link to="/staff/calls" className="btn o">통화 기록으로</Link>} />
        )}
        {c && <Timeline c={c} />}
        {c?.welfare && <div className="mid-welfare"><WelfarePanel matches={c.welfare} /></div>}
      </section>

      <aside className="props" aria-label="판정과 기록">
        {c ? (
          <Props c={c} onCheck={() => setChecking(true)} />
        ) : (
          <Empty title="통화를 고르면 판정이 보여요" />
        )}
      </aside>

      {checking && c && (
        <CheckModal
          callId={c.id}
          name={c.resident_name}
          onClose={() => setChecking(false)}
          onSaved={() => {
            setChecking(false);
            toast('확인 기록을 남겼어요.');
            void call.refresh();
            void dash.refresh();
          }}
        />
      )}
    </div>
  );
}

function Timeline({ c }: { c: CallDetail }) {
  const steps = buildSteps(c);
  const retries = steps.reduce((s, x) => s + x.retries, 0);
  const done = c.status === 'completed' ? c.step.total : Math.max(0, c.step.index - (isLive(c.status) ? 1 : 0));
  const pct = Math.round((done / c.step.total) * 100);
  const live = isLive(c.status);
  const noTalk = c.turns.length === 0;

  return (
    <>
      <div className="eyebrow">통화 #{c.id} · {monthDay(c.created_at)} {hhmm(c.started_at ?? c.created_at)}</div>
      <h2>{c.resident_name} 어르신 안부전화</h2>
      <div style={{ color: 'var(--ink-subtle)', fontSize: 17 }}>{headline(c)}</div>
      {live && <Link to={`/staff/live?call=${c.id}`} className="btn g" style={{ marginTop: 10 }}>● 실시간으로 보기 ›</Link>}
      <div className="prog" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={c.step.total} aria-label="질문 진행"><i style={{ width: `${pct}%` }} /></div>
      <div style={{ fontSize: 16, color: 'var(--ink-subtle)' }}>{done} / {c.step.total} 질문{retries ? ` · 다시 여쭤봄 ${retries}회` : ''}</div>

      {noTalk ? (
        <div style={{ marginTop: 16 }}>
          <Empty icon="☎" title="대화 기록이 없어요" reason={c.status === 'missed' ? '어르신이 30초 안에 전화를 받지 않으셨어요.' : c.status === 'ringing' ? '어르신이 전화를 받으면 여기에 대화가 쌓여요.' : '이 통화는 대화 원문을 남기지 않았어요.'} />
        </div>
      ) : (
        <ol className="tl" style={{ listStyle: 'none', paddingLeft: 0 }}>
          {c.assessment?.safety.map((s, i) => (
            <li key={`s${i}`} className="st safe">
              <div className="hd"><b>⚠ 안전 신호 · {s.category}</b><GradeBadge grade="urgent" /></div>
              <p>“<mark>{s.quote}</mark>”</p>
              <div className="meta"><span className="tag t-said">어르신 말씀</span><span className="tag t-rule">규칙 판정</span>정해진 표현을 규칙으로 잡았어요 · AI가 이 판정을 끄지 못해요</div>
            </li>
          ))}
          {steps.map((s, i) => <StepItem key={s.topic} s={s} n={i + 1} />)}
        </ol>
      )}
    </>
  );
}

function StepItem({ s, n }: { s: StepView; n: number }) {
  const saidText = s.said.filter((t) => t.trim());
  let note: ReactNode = null;
  if (s.status === null) note = '이 질문까지 가지 못했어요';
  else if (s.status === 'unknown') note = s.said.length ? '답을 듣지 못해 0점 · 확인 필요로 남김' : null;
  else if (s.origin === 'rule') note = s.run?.outcome === 'fallback' ? `AI ${s.run.note ?? '실패'} → 키워드 규칙으로 대신 판정` : '키워드 규칙으로 판정';
  else if (s.origin === 'llm' && s.run) note = `${s.run.model?.split(':')[0] ?? 'AI'} · ${msLabel(s.run.ms)}`;

  return (
    <li className={`st ${s.status ? DOT[s.status] : ''}`}>
      <div className="hd">
        <b>{n} · {TOPIC_LABEL[s.topic]}</b>
        {s.status ? <ItemBadge status={s.status} /> : <span className="badge b-m"><span aria-hidden>…</span>묻기 전</span>}
      </div>
      {s.said.length > 0 && (
        <p>
          {s.said.map((t, i) => (
            <span key={i}>
              {i > 0 && <span className="subtle"> → 다시 여쭘 → </span>}
              {t.trim() ? <>“{i === s.said.length - 1 ? <Highlight text={t} quote={s.quote} /> : t}”</> : <span className="subtle">(대답 없음)</span>}
            </span>
          ))}
        </p>
      )}
      <div className="meta">
        {saidText.length > 0 && <span className="tag t-said">어르신 말씀</span>}
        {(s.origin === 'llm' || s.origin === 'rule') && <span className={`tag ${ORIGIN_TAG[s.origin].cls}`}>{ORIGIN_TAG[s.origin].label}</span>}
        {s.retries > 0 && <span className="tag t-rule">재질문 {s.retries}회</span>}
        {note}
      </div>
      {s.needs.length > 0 && (
        <div className="needs" aria-label="이 답에서 찾은 어려움">
          {s.needs.map((x) => <NeedChip key={x.type} need={x} />)}
          <span className="subtle">어려움 유형 · 점수에는 넣지 않아요</span>
        </div>
      )}
      {s.reply && s.status === 'risk' && <div className="meta">AI 응답: “{empathyOnly(s.reply)}”</div>}
    </li>
  );
}

function Props({ c, onCheck }: { c: CallDetail; onCheck: () => void }) {
  const a = c.assessment;
  const dur = duration(c.started_at, c.ended_at);
  const [runsOpen, setRunsOpen] = useState(false);
  const runs = c.ai_runs;
  const timed = runs.filter((r) => r.ms != null);
  const avg = timed.length ? Math.round(timed.reduce((t, r) => t + (r.ms ?? 0), 0) / timed.length) : null;
  const fallback = runs.filter((r) => r.outcome === 'fallback').length;
  const scoreEmpty = !!a && a.score === 0 && a.reasons.length === 0 && a.needs_check.length === 0;
  const checked = c.staff_check?.checked;
  return (
    <>
      <h5>판정</h5>
      <div className="kv">
        <span>단계</span>
        <b>{a ? <GradeBadge grade={a.grade} label={a.grade_label} /> : <span className="subtle">통화가 끝나면 계산해요</span>}</b>
        <span>점수</span>
        <b>{a ? `${a.score} / 100` : '—'}</b>
        <span>규칙 버전</span>
        <span className="mono">{a?.rule_version ?? '—'}</span>
        <span>통화</span>
        <span><CallBadge status={c.status} /></span>
        {dur && (<><span>통화 시간</span><span>{dur}</span></>)}
      </div>

      <h5>점수 구성</h5>
      {a && !scoreEmpty ? (
        <div className="sc">
          {a.reasons.map((r, i) => (
            <div key={i}><span>{r.chip}</span><b>{r.kind === 'safety' ? `${GRADE.urgent.label} · 점수와 별도` : `+${r.points}`}</b></div>
          ))}
          {a.needs_check.map((t) => (
            <div key={t}><span>{TOPIC_LABEL[t]} 미확인</span><b>0 · 확인 필요</b></div>
          ))}
          <div className="total"><span>합계</span><b>{a.score}</b></div>
        </div>
      ) : (
        <p className="prop-line">{a ? '더한 점수가 없어요 · 합계 0점' : '아직 점수가 없어요.'}</p>
      )}

      <h5>AI 실행 기록</h5>
      {runs.length ? (
        <>
          <button type="button" className="run-sum" aria-expanded={runsOpen} aria-controls="runlog" onClick={() => setRunsOpen((v) => !v)}>
            <span>AI {runs.length}회 · 평균 {msLabel(avg)} · 규칙 대체 {fallback}회</span>
            <span aria-hidden className="chev">{runsOpen ? '▴' : '▾'}</span>
            <span className="sr">{runsOpen ? '접기' : '펼치기'}</span>
          </button>
          {runsOpen && (
            <div className="runlog" id="runlog">
              {runs.map((r, i) => (
                <div key={i}>
                  {r.outcome === 'fallback' ? <span className="tag t-rule">규칙 대체</span> : <span className="tag t-ai">{AI_STEP[r.step]}</span>}
                  <span className="md">{r.outcome === 'fallback' ? r.note ?? 'AI 실패' : r.model ?? '규칙만 사용'}</span>
                  <span className="ms">{msLabel(r.ms)}</span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="prop-line">이 통화에서는 AI를 부르지 않았어요.</p>
      )}

      <div className="h5row">
        <h5>생활지원사 확인</h5>
        {!checked && <button type="button" className="btn g sm" onClick={onCheck} disabled={!a} title={a ? undefined : '통화가 끝나야 기록할 수 있어요'}>✎ 확인 기록 남기기</button>}
      </div>
      {checked ? (
        <div className="checkbox">
          <b>✓ 확인함 · {monthDay(c.staff_check!.at)} {hhmm(c.staff_check!.at)}</b>
          {c.staff_check!.note || '메모 없이 확인만 남겼어요.'}
        </div>
      ) : (
        <p className="prop-line">{a ? '아직 확인 기록이 없어요. 전화나 방문으로 확인한 내용을 남겨 주세요.' : '통화가 끝나야 기록할 수 있어요.'}</p>
      )}
    </>
  );
}
