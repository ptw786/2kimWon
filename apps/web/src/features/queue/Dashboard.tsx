// ② 오늘 확인 순서 — 인사형 제목(원티드) · KPI가 필터(AI Platform) · 첫 행만 ★ 강조(TRITON) · 사유 칩 +N(이음등) · 3박스(맛대패스)
import { Fragment, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckModal } from '../../shared/CheckModal';
import { useStaff } from '../../shared/StaffLayout';
import { Empty, GradeBadge, Kpi, Loading, NeedChip, RowBadge, circled, uniqNeeds } from '../../shared/ui';
import { WelfarePanel } from '../../shared/WelfarePanel';
import { api } from '../../shared/api';
import { GRADE, ITEM, TOPICS, TOPIC_LABEL, TOPIC_SHORT, WEEK_CELL, contactLine, isLive } from '../../shared/status';
import { dayLabel, duration, hhmm, kstDate, nowHeadline } from '../../shared/time';
import { usePoll } from '../../shared/usePoll';
import type { ItemStatus, Need, ResidentDetail, ResidentRow } from '../../shared/types';

type Filter = 'urgent' | 'today' | 'missed' | 'watch' | 'completed' | null;
const MATCH: Record<Exclude<Filter, null>, (r: ResidentRow) => boolean> = {
  urgent: (r) => r.assessment?.grade === 'urgent',
  today: (r) => r.assessment?.grade === 'today',
  missed: (r) => r.today.status === 'missed',
  watch: (r) => r.assessment?.grade === 'watch',
  completed: (r) => r.today.status === 'completed',
};
const FILTER_LABEL: Record<Exclude<Filter, null>, string> = { urgent: GRADE.urgent.label, today: GRADE.today.label, missed: '미응답', watch: GRADE.watch.label, completed: '통화 완료' };

const dong = (n: string) => n.split(' ').pop() ?? n;

function useNarrow() {
  const q = '(max-width: 1280px)';
  const [narrow, setNarrow] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const on = () => setNarrow(m.matches);
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  return narrow;
}

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = window.setInterval(() => setNow(new Date()), 30000);
    return () => window.clearInterval(t);
  }, []);
  return now;
}

export function DashboardPage() {
  const { dash, callResident, toast } = useStaff();
  const nav = useNavigate();
  const now = useClock();
  const [filter, setFilter] = useState<Filter>(null);
  const [selId, setSelId] = useState<number | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const rows = dash.data?.residents ?? [];
  const shown = useMemo(() => (filter ? rows.filter(MATCH[filter]) : rows), [rows, filter]);
  const narrow = useNarrow();
  // 넓은 화면: 오른쪽 패널에 첫 분을 기본으로 · 좁은 화면: 누른 카드 바로 아래에 펼친다
  const sel = shown.find((r) => r.id === selId) ?? (narrow ? null : shown[0] ?? null);
  const c = dash.data?.counts;
  const completed = rows.filter((r) => r.today.status === 'completed').length;
  const remaining = rows.filter((r) => r.today.status === 'not_called');

  const toggle = (f: Exclude<Filter, null>) => setFilter((cur) => (cur === f ? null : f));

  async function bulkCall() {
    if (!remaining.length || !window.confirm(`아직 통화하지 않은 ${remaining.length}분께 전화를 걸까요?`)) return;
    setBulkBusy(true);
    let ok = 0;
    for (const r of remaining) {
      try {
        await api.post(`/staff/residents/${r.id}/call`);
        ok++;
      } catch {
        /* 이미 통화 중인 분은 건너뜀 */
      }
    }
    setBulkBusy(false);
    toast(`${ok}분께 전화를 걸었어요.`);
    void dash.refresh();
  }

  return (
    <div className="page">
      <div className="ph">
        <div>
          <div className="eyebrow">{nowHeadline(now)}</div>
          <h1>생활지원사님, 오늘 먼저 챙길 분이에요</h1>
          <p>통화가 끝난 순서가 아니라, 확인이 필요한 순서로 보여 드려요.</p>
        </div>
        <div className="act">
          <button type="button" className="btn o" onClick={() => nav('/staff/residents?new=1')}>어르신 추가</button>
          <button type="button" className="btn p" onClick={bulkCall} disabled={!remaining.length || bulkBusy}>
            {bulkBusy ? '거는 중…' : remaining.length ? `☎ 남은 ${remaining.length}분께 일괄 전화` : dash.data ? '☎ 남은 통화 없음' : '☎ 남은 분께 일괄 전화'}
          </button>
        </div>
      </div>

      <div className="kpis" role="group" aria-label="단계별 인원 · 눌러서 거르기">
        <Kpi label={GRADE.urgent.label} icon="⚠" value={c?.urgent ?? '–'} unit="명" foot="지금 바로 연락" alert={!!c?.urgent} on={filter === 'urgent'} onClick={() => toggle('urgent')} />
        <Kpi label={GRADE.today.label} value={c?.today ?? '–'} unit="명" foot="오늘 안에 전화·방문" on={filter === 'today'} onClick={() => toggle('today')} />
        <Kpi label="미응답" value={c?.missed ?? '–'} unit="명" foot="다시 걸어 보세요" on={filter === 'missed'} onClick={() => toggle('missed')} />
        <Kpi label={GRADE.watch.label} value={c?.watch ?? '–'} unit="명" foot="다음 통화 때 다시 보기" on={filter === 'watch'} onClick={() => toggle('watch')} />
        <Kpi label="통화 완료" value={c ? completed : '–'} unit={c ? `/${c.total}` : ''} foot={c ? `남은 통화 ${c.total - completed}건` : '불러오는 중'} on={filter === 'completed'} onClick={() => toggle('completed')} />
      </div>
      <div className="filter-note" role="status">
        {filter ? (
          <>
            <span><b>‘{FILTER_LABEL[filter]}’ {shown.length}명</b>만 보고 있어요</span>
            <button type="button" onClick={() => setFilter(null)}>모두 보기</button>
          </>
        ) : (
          <span>위 칸을 눌러서 걸러 보기 · 지금은 {rows.length ? `${rows.length}명 모두` : '모두'} 보고 있어요</span>
        )}
      </div>

      <div className="two">
        <div className="queue">
          {!dash.data && dash.loading && <Loading rows={4} />}
          {!dash.data && dash.error && (
            <Empty icon="⚠" title="오늘 순서를 불러오지 못했어요" reason={dash.error} action={<button type="button" className="btn o" onClick={() => void dash.refresh()}>다시 불러오기</button>} />
          )}
          {dash.data && rows.length === 0 && (
            <Empty icon="♡" title="아직 등록된 어르신이 없어요" reason="어르신을 추가하면 매일 정해진 시간에 안부전화를 걸어요." action={<button type="button" className="btn p" onClick={() => nav('/staff/residents?new=1')}>어르신 추가</button>} />
          )}
          {dash.data && rows.length > 0 && shown.length === 0 && (
            <Empty title="이 조건에 맞는 어르신이 없어요" reason={`오늘 ‘${filter ? FILTER_LABEL[filter] : ''}’에 해당하는 분이 없어요.`} action={<button type="button" className="btn o" onClick={() => setFilter(null)}>모두 보기</button>} />
          )}
          {shown.map((r, i) => (
            <Fragment key={r.id}>
              <QueueCard
                row={r}
                first={i === 0 && !filter}
                selected={sel?.id === r.id}
                onSelect={() => setSelId(narrow && selId === r.id ? null : r.id)}
                onCall={() => void callResident(r.id, r.name)}
                onOpen={() => (isLive(r.today.status) ? nav(`/staff/live?call=${r.today.call_id}`) : r.today.call_id ? nav(`/staff/calls/${r.today.call_id}`) : setSelId(r.id))}
              />
              {narrow && sel?.id === r.id && <DetailPanel row={sel} inline onCall={() => void callResident(sel.id, sel.name)} />}
            </Fragment>
          ))}
        </div>
        {!narrow && sel && <DetailPanel row={sel} onCall={() => void callResident(sel.id, sel.name)} />}
      </div>
    </div>
  );
}

function QueueCard({ row, first, selected, onSelect, onCall, onOpen }: { row: ResidentRow; first: boolean; selected: boolean; onSelect: () => void; onCall: () => void; onOpen: () => void }) {
  const a = row.assessment;
  const s = row.today.status;
  const reasons = a?.reasons ?? [];
  // 줄 높이를 고정하려고 사유 칩은 두 개까지만, 나머지는 +N
  const chips = reasons.slice(0, 2);
  const needs = uniqNeeds(a?.needs);
  const quote = a?.safety[0]?.quote ?? reasons.find((x) => x.quote)?.quote ?? null;
  const line = s === 'completed' ? null : contactLine(s, row.call_time);
  const live = isLive(s);
  const needsCall = s === 'missed' || s === 'declined' || s === 'not_called' || s === 'interrupted';
  const sub = line ?? (quote ? `“${quote}”` : null);

  let button;
  if (live) button = <button type="button" className={`btn ${first ? 'p' : 'o'}`} onClick={(e) => (e.stopPropagation(), onOpen())}>☎ 통화 보기 ›</button>;
  else if (first) button = <button type="button" className="btn p" onClick={(e) => (e.stopPropagation(), onCall())}>☎ 지금 전화</button>;
  else if (needsCall) button = <button type="button" className="btn o" onClick={(e) => (e.stopPropagation(), onCall())}>☎ {s === 'not_called' ? '전화 걸기' : '다시 걸기'}</button>;
  else button = <button type="button" className="btn o" onClick={(e) => (e.stopPropagation(), onOpen())}>상세 보기 ›</button>;

  return (
    <article
      className={`qi${first ? ' first' : ''}${selected ? ' sel' : ''}`}
      onClick={onSelect}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget && (e.preventDefault(), onSelect())}
      tabIndex={0}
      aria-label={`${row.name} 어르신, ${a?.grade_label ?? row.today.status_label}${a && a.grade !== 'urgent' ? `, ${a.score}점` : ''}`}
      aria-current={selected || undefined}
    >
      <div className="who">
        {first && <span className={`first-tag${a?.grade === 'urgent' ? ' u' : ''}`}>★ 지금 먼저</span>}
        <b>{row.name}</b>
        <span>{row.age}세 · {dong(row.neighborhood)}</span>
        {row.staff_check?.checked && !first && <span className="checked">✓ 확인 기록 있음</span>}
      </div>
      <div className="grade">
        <RowBadge row={row} />
        {a && a.grade !== 'urgent' && (
          <div className="score"><b>{a.score}</b><small>/100</small><span className="bar" aria-hidden><i style={{ width: `${Math.min(100, a.score)}%` }} /></span></div>
        )}
      </div>
      <div className="why">
        {(chips.length > 0 || needs.length > 0) && (
          <div className="chips">
            {chips.map((x, k) => <span key={k} className="chip">{x.chip}{x.points > 0 && <b>+{x.points}</b>}</span>)}
            {reasons.length > 2 && <span className="chip more" title={reasons.slice(2).map((x) => x.chip).join(', ')}>+{reasons.length - 2}</span>}
            {needs.map((n) => <NeedChip key={n.type} need={n} />)}
          </div>
        )}
        {sub && <span className="line">{sub}</span>}
        {!a && !line && <span className="line">아직 판정 전이에요</span>}
        {a && !reasons.length && !needs.length && !sub && <span className="line">걱정할 표현을 듣지 못했어요</span>}
      </div>
      <div className="act">{button}</div>
    </article>
  );
}

const BAD_FIRST: ItemStatus[] = ['risk', 'caution'];

function DetailPanel({ row, onCall, inline = false }: { row: ResidentRow; onCall: () => void; inline?: boolean }) {
  const { toast, dash } = useStaff();
  const detail = usePoll(() => api.get<ResidentDetail>(`/staff/residents/${row.id}`), 10000, row.id);
  const [checking, setChecking] = useState(false);
  const a = row.assessment;
  const d = detail.data;
  const call = d?.calls.find((x) => x.id === row.today.call_id) ?? d?.calls.find((x) => x.assessment);
  const dur = call ? duration(call.started_at, call.ended_at) : null;
  const checkCallId = d?.calls.find((x) => x.assessment && kstDate(new Date(x.created_at)) === kstDate())?.id ?? null;

  const said: { q: string; t: string; needs: Need[] }[] = [];
  if (a) {
    a.safety.forEach((s) => said.push({ q: s.quote, t: `안전 신호 · ${s.category}`, needs: [] }));
    const items = TOPICS.map((t) => ({ t, ...a.items[t] }));
    const bad = items.filter((x) => x.quote && (x.status === 'risk' || x.status === 'caution'));
    (bad.length ? bad : items.filter((x) => x.quote).slice(0, 2)).forEach((x) => {
      if (!said.some((s) => s.q === x.quote)) said.push({ q: x.quote!, t: TOPIC_LABEL[x.t], needs: [] });
    });
    // 어려움 유형: 같은 말씀이면 그 줄에 칩을 붙이고, 아니면 말씀 한 줄을 더한다
    uniqNeeds(a.needs).forEach((n) => {
      if (!n.quote) return;
      const hit = said.find((s) => s.q.includes(n.quote) || n.quote.includes(s.q));
      if (hit) hit.needs.push(n);
      else said.push({ q: n.quote, t: '', needs: [n] });
    });
  }
  const judged = a ? BAD_FIRST.flatMap((st) => TOPICS.filter((t) => a.items[t].status === st).map((t) => `${TOPIC_LABEL[t]} ${ITEM[st].label}`)) : [];
  const goods = a ? TOPICS.filter((t) => a.items[t].status === 'good') : [];
  if (goods.length) judged.push(goods.length === TOPICS.length ? '다섯 가지 모두 양호' : `${judged.length ? '나머지 ' : ''}${goods.map((t) => TOPIC_LABEL[t]).join('·')} 양호`);
  const checked = row.staff_check?.checked;

  return (
    <aside className={`panel dpanel${inline ? ' inline' : ''}`} aria-label={`${row.name} 어르신 요약`}>
      <h3>{row.name} 어르신</h3>
      <div className="sub">
        {row.age}세 · {row.region ? `${row.region} ${dong(row.neighborhood)}` : row.neighborhood}
        {call?.started_at && ` · 오늘 ${hhmm(call.started_at)} 통화${dur ? ` ${dur}` : ''}`}
      </div>
      {row.memo && <div className="sub">메모: {row.memo}</div>}

      {!a ? (
        <div style={{ marginTop: 12 }}>
          <Empty icon="☎" title="아직 오늘 통화 결과가 없어요" reason={contactLine(row.today.status, row.call_time) ?? undefined} action={!isLive(row.today.status) && <button type="button" className="btn p" onClick={onCall}>☎ 전화 걸기</button>} />
        </div>
      ) : (
        <div className="box3">
          <div className="k-said">
            <b className="h">어르신 말씀</b>
            {said.length ? (
              <ol>
                {said.map((s, i) => (
                  <li key={i}>
                    {circled(i)} “{s.q}”{s.t && ` — ${s.t}`}
                    {s.needs.length > 0 && <span className="needs">{s.needs.map((n) => <NeedChip key={n.type} need={n} />)}</span>}
                  </li>
                ))}
              </ol>
            ) : (
              <span className="subtle">인용할 말씀이 없어요 (전화를 받지 않으셨어요)</span>
            )}
          </div>
          <div className={`k-ai${checked ? ' done' : ''}`}>
            <b className="h">{checked ? 'AI 판단 · ✓ 생활지원사 확인함' : 'AI 판단 · 확인 전'}</b>
            <span style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <GradeBadge grade={a.grade} label={a.grade === 'urgent' ? a.grade_label || GRADE.urgent.label : `${a.grade_label || GRADE[a.grade].label} · ${a.score}점`} />
              {judged.length ? judged.join(' · ') : '판정한 항목이 없어요'}
            </span>
            {checked && row.staff_check?.note && <div>메모: {row.staff_check.note}</div>}
          </div>
          <div className="k-next">
            <b className="h">다음에 여쭤볼 것</b>
            {a.needs_check.length ? a.needs_check.map((t) => `${TOPIC_LABEL[t]} — 답을 듣지 못했어요`).join(' · ') : '없어요 · 다섯 가지 모두 들었어요'}
          </div>
        </div>
      )}

      {d ? (
        <>
          <div className="week" role="table" aria-label="최근 7일 항목별 상태">
            <span role="columnheader" />
            {d.week.map((w) => <span key={w.date} className="h" role="columnheader">{dayLabel(w.date)}</span>)}
            {TOPICS.map((t) => (
              <WeekRow key={t} label={TOPIC_SHORT[t]} cells={d.week.map((w) => ({ date: w.date, st: w.items ? w.items[t] : null, missed: w.call_status === 'missed' }))} />
            ))}
          </div>
          <div className="legend" aria-hidden>
            {(['good', 'caution', 'risk', 'unknown', 'none'] as const).map((k) => (
              <span key={k}><i className={`c ${WEEK_CELL[k].cls}`}>{WEEK_CELL[k].mark}</i>{WEEK_CELL[k].label}</span>
            ))}
          </div>
        </>
      ) : detail.error ? (
        <p className="err">7일 기록을 불러오지 못했어요: {detail.error}</p>
      ) : null}
      {d?.welfare && <WelfarePanel matches={d.welfare} />}

      <div className="btnrow">
        {isLive(row.today.status) ? (
          <button type="button" className="btn p" disabled>☎ 지금 통화 중</button>
        ) : (
          <button type="button" className="btn p" onClick={onCall}>☎ 전화 걸기</button>
        )}
        <button type="button" className="btn g" disabled={!checkCallId} onClick={() => setChecking(true)} title={checkCallId ? undefined : '오늘 끝난 통화가 있어야 기록할 수 있어요'}>
          확인 기록 남기기
        </button>
      </div>
      {checking && checkCallId && (
        <CheckModal
          callId={checkCallId}
          name={row.name}
          onClose={() => setChecking(false)}
          onSaved={() => {
            setChecking(false);
            toast('확인 기록을 남겼어요.');
            void dash.refresh();
            void detail.refresh();
          }}
        />
      )}
    </aside>
  );
}

function WeekRow({ label, cells }: { label: string; cells: { date: string; st: ItemStatus | null; missed: boolean }[] }) {
  return (
    <>
      <span className="rl" role="rowheader">{label}</span>
      {cells.map((c) => {
        const m = WEEK_CELL[c.st ?? 'none'];
        const text = c.st ? m.label : c.missed ? '미응답' : '통화 없음';
        return <i key={c.date} role="cell" className={`c ${m.cls}`} title={`${dayLabel(c.date)} ${label} ${text}`} aria-label={`${dayLabel(c.date)} ${label} ${text}`}>{m.mark}</i>;
      })}
    </>
  );
}
