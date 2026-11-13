// 연계할 만한 지원 (F11) — 통화에서 들은 어려움 + 사는 지역으로 찾은 사회보장 복지서비스.
// 오늘 확인 순서 오른쪽 패널(최근 7일 기준)과 통화 상세 오른쪽 칸(이 통화 기준)이 같이 쓴다.
import { NeedChip } from './ui';
import type { WelfareMatch } from './types';

export function WelfarePanel({ matches }: { matches: WelfareMatch[] }) {
  const asOf = matches.find((m) => m.data_as_of)?.data_as_of;
  return (
    <section className="welfare" aria-label="연계할 만한 지원">
      <div className="wf-hd">
        <h4>연계할 만한 지원</h4>
        <span className="subtle">어르신 말씀 + 사는 지역 기준</span>
      </div>
      {matches.length === 0 ? (
        <p className="wf-empty">아직 연계할 어려움이 없어요</p>
      ) : (
        matches.map((m) => (
          <div className="wf-match" key={`${m.need}-${m.region}`}>
            <div className="wf-need">
              <NeedChip need={{ type: m.need, label: m.need_label }} />
              <span>{m.region}</span>
            </div>
            {m.note && <p className="wf-note">{m.note}</p>}
            {m.services.length === 0 && <p className="wf-note">이 지역에서 맞는 서비스를 찾지 못했어요.</p>}
            {m.services.slice(0, 3).map((s) => (
              <article className="wf-svc" key={s.id}>
                <div className="wf-top">
                  <b>{s.name}</b>
                  <span className="wf-src">{s.source}</span>
                </div>
                <div className="subtle">{s.area}{s.org && ` · ${s.org}`}</div>
                {s.summary && <p>{s.summary}</p>}
                {s.target_quote && <p className="wf-q"><span className="tag t-rule">지원대상</span> “{s.target_quote}”</p>}
                {s.apply_quote && <p className="wf-q"><span className="tag t-rule">신청방법</span> “{s.apply_quote}”</p>}
                {s.link && (
                  <a href={s.link} target="_blank" rel="noopener noreferrer" className="wf-link">
                    복지로에서 보기 <span aria-hidden>↗</span><span className="sr"> (새 창)</span>
                  </a>
                )}
              </article>
            ))}
          </div>
        ))
      )}
      <p className="wf-foot">출처: 한국사회보장정보원 지자체·중앙부처 복지서비스 (공공데이터포털){asOf && <> · <span className="nowrap">조회 {asOf}</span></>}</p>
    </section>
  );
}
