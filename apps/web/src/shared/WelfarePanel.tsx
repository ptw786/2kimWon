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
        <span className="subtle">생활지원 후보 · 최종 신청 자격은 기관 확인</span>
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
                {s.eligibility && <div className="wf-note" role="note">
                  <b>ⓘ 신청 자격 확인 필요</b>
                  <ul>{s.eligibility.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                </div>}
                {s.checked_at && <p className="subtle">사업 정보 확인일: {s.checked_at}</p>}
                <p className="subtle">연락처: {s.contact || '미제공 · 공식 상세에서 확인해 주세요'}</p>
                {!s.apply_quote && <p className="subtle">신청방법: 미제공 · 공식 상세에서 확인해 주세요</p>}
                {s.source_area && s.source_area !== s.area && <p className="subtle">출처의 지역명: {s.source_area}</p>}
                {s.target_quote && <p className="wf-q"><span className="tag t-rule">지원대상</span> “{s.target_quote}”</p>}
                {s.apply_quote && <p className="wf-q"><span className="tag t-rule">신청방법</span> “{s.apply_quote}”</p>}
                {(s.target_text || s.criteria_text || s.apply_text) && <details>
                  <summary>지원 조건·신청방법 원문 보기</summary>
                  {s.target_text && <p><b>지원대상</b> {s.target_text}</p>}
                  {s.criteria_text && <p><b>선정기준</b> {s.criteria_text}</p>}
                  {s.apply_text && <p><b>신청방법</b> {s.apply_text}</p>}
                </details>}
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
      <p className="wf-foot">출처: 한국사회보장정보원 지자체·중앙부처 복지서비스 (공공데이터포털){asOf && <> · <span className="nowrap">자료 기준 {asOf} · 사업별 확인일은 위에 표시</span></>}</p>
    </section>
  );
}
