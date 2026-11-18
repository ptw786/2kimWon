// 통화 기록 — 날짜·단계로 거르고, 줄을 누르면 통화 상세로
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CallBadge, Empty, GradeBadge, Loading } from '../../shared/ui';
import { api } from '../../shared/api';
import { GRADE, GRADE_ORDER } from '../../shared/status';
import { duration, hhmm, kstDate, monthDay } from '../../shared/time';
import { usePoll } from '../../shared/usePoll';
import type { CallSummary, Grade } from '../../shared/types';

type GradeFilter = Grade | 'none' | 'all';

export function CallsPage() {
  const [date, setDate] = useState(kstDate());
  const [grade, setGrade] = useState<GradeFilter>('all');
  const [page, setPage] = useState(0);
  const calls = usePoll(() => api.get<CallSummary[]>(`/staff/calls?date=${date}&limit=51&offset=${page * 50}${grade === 'all' ? '' : `&grade=${grade}`}`), 10000, `${date}:${grade}:${page}`);
  const list = (calls.data ?? []).slice(0, 50);
  const hasNext = (calls.data?.length ?? 0) > 50;

  return (
    <div className="page">
      <div className="ph">
        <div>
          <div className="eyebrow">{monthDay(`${date}T12:00:00+09:00`)} · {calls.data ? `${list.length}건 · ${page + 1}페이지` : '불러오는 중'}</div>
          <h1>통화 기록</h1>
          <p>최신 통화가 위에 있어요. 줄을 누르면 대화와 판정 근거를 볼 수 있어요.</p>
        </div>
      </div>
      <div className="toolbar">
        <label className="field">날짜<input type="date" value={date} max={kstDate()} onChange={(e) => { if (e.target.value) { setDate(e.target.value); setPage(0); } }} /></label>
        <label className="field">
          단계
          <select value={grade} onChange={(e) => { setGrade(e.target.value as GradeFilter); setPage(0); }}>
            <option value="all">전체</option>
            {GRADE_ORDER.map((g) => <option key={g} value={g}>{GRADE[g].icon} {GRADE[g].label}</option>)}
            <option value="none">판정 없음(통화 중·벨)</option>
          </select>
        </label>
        {(grade !== 'all' || date !== kstDate() || page > 0) && <button type="button" className="btn o" onClick={() => (setDate(kstDate()), setGrade('all'), setPage(0))}>오늘 · 전체로</button>}
      </div>

      {!calls.data && calls.loading && <Loading rows={5} />}
      {!calls.data && calls.error && <Empty icon="⚠" title="통화 기록을 불러오지 못했어요" reason={calls.error} action={<button type="button" className="btn o" onClick={() => void calls.refresh()}>다시 불러오기</button>} />}
      {calls.data && list.length === 0 && <Empty title="이 조건에 맞는 통화가 없어요" reason="날짜나 단계를 바꿔 보세요." />}

      <nav className="toolbar" aria-label="통화 기록 페이지">
        <button className="btn o" disabled={page === 0 || calls.loading} onClick={() => setPage((p) => p - 1)}>이전 50건</button>
        <span>{page + 1}페이지</span>
        <button className="btn o" disabled={!hasNext || calls.loading} onClick={() => setPage((p) => p + 1)}>다음 50건</button>
      </nav>
      {list.length > 0 && (
        <div className="rows calls" role="table" aria-label="통화 기록">
          <div className="row head" role="row">
            <span role="columnheader">시각</span><span role="columnheader">어르신</span><span role="columnheader">단계 · 점수</span><span role="columnheader">요약</span><span role="columnheader">통화</span>
          </div>
          {list.map((c) => {
            const dur = duration(c.started_at, c.ended_at);
            return (
              <Link to={`/staff/calls/${c.id}`} className="row" role="row" key={c.id}>
                <span role="cell">{hhmm(c.started_at ?? c.created_at)}{dur && <span className="subtle"> · {dur}</span>}</span>
                <span role="cell"><b>{c.resident_name}</b></span>
                <span role="cell">{c.assessment ? <><GradeBadge grade={c.assessment.grade} label={c.assessment.grade_label} /> {c.assessment.grade !== 'urgent' && <b>{c.assessment.score}점</b>}</> : <span className="subtle">—</span>}</span>
                <span role="cell" className="clamp2 wide">{c.summary ?? (c.assessment?.reasons.map((r) => r.chip).join(' · ') || '요약 없음')}</span>
                <span role="cell"><CallBadge status={c.status} /></span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
