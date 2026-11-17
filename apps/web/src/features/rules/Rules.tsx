// 판정 기준 — docs/판정규칙.md를 표로 보여 준다(문구는 src/strings/rules.ts)
import { GradeBadge, NeedChip } from '../../shared/ui';
import { GRADE, NEED } from '../../shared/status';
import { GRADES, GRADE_NOTES, GRADE_RENAME, GRADE_WHY_R3, HYPOTHESIS, NEEDS, NEEDS_INTRO, NEEDS_NOTES, ITEM_STATES, PRINCIPLES, REASON_EXAMPLE, RULE_VERSION, SAFETY, SAFETY_NOTES, SAFETY_SCRIPT, SCORE, SOURCES, SOURCES_GAP } from './strings';

const TOC: [string, string][] = [
  ['rule-1', '원칙'],
  ['rule-2', '항목별 상태'],
  ['rule-3', '안전 신호'],
  ['rule-4', '확인 점수'],
  ['rule-5', '단계'],
  ['rule-6', '이유 표시 형식'],
  ['rule-7', '이 값들은 가설'],
  ['rule-8', '어려움 유형'],
  ['rule-src', '근거 출처'],
];

export function RulesPage() {
  return (
    <div className="page">
      <div className="read">
        <nav className="toc" aria-label="이 페이지 목차">
          <b>목차</b>
          <ol>{TOC.map(([id, t], i) => <li key={id}><a href={`#${id}`}><span>{i + 1}</span>{t}</a></li>)}</ol>
        </nav>
        <div className="read-col">
      <div className="ph">
        <div>
          <div className="eyebrow">규칙 버전 {RULE_VERSION}</div>
          <h1>판정 기준</h1>
          <p>점수는 누구부터 연락할지 정하는 참고값이에요. 모든 값은 아래 표 그대로 코드가 계산해요.</p>
        </div>
      </div>
      <div className="doc">
        <section id="rule-1">
          <h2><span className="hn">1</span>원칙</h2>
          <ol>{PRINCIPLES.map(([h, d]) => <li key={h}><b>{h}</b> {d}</li>)}</ol>
        </section>

        <section id="rule-2">
          <h2><span className="hn">2</span>항목별 상태 (매 통화)</h2>
          <p style={{ marginTop: 0 }}>몸 상태 · 식사 · 수면 · 복약 · 기분, 다섯 항목마다 아래 넷 중 하나로 판정해요.</p>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>상태</th><th>뜻</th><th>예시 답변</th></tr></thead>
              <tbody>{ITEM_STATES.map(([ic, l, m, e]) => <tr key={l}><td style={{ whiteSpace: 'nowrap' }}><b>{ic} {l}</b></td><td>{m}</td><td>{e}</td></tr>)}</tbody>
            </table>
          </div>
        </section>

        <section id="rule-3">
          <h2><span className="hn">3</span>안전 신호 → 바로 ‘{GRADE.urgent.label}’</h2>
          <p style={{ marginTop: 0 }}>
            아래 표현이 나오면 점수와 상관없이 <GradeBadge grade="urgent" />이에요. 통화가 끝나기 전에 이 화면에 바로 뜨고, 어르신께는 고정 안내(“{SAFETY_SCRIPT}”)를 해요. 이 판단은 <b>규칙(정규식)으로만</b> 하며 AI가 끄지 못해요.
          </p>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>분류</th><th>예 (어르신 말투)</th><th>근거</th></tr></thead>
              <tbody>{SAFETY.map(([k, v, src]) => <tr key={k}><td style={{ whiteSpace: 'nowrap' }}><b>{k}</b></td><td>{v}</td><td style={{ whiteSpace: 'nowrap' }}><a href="#rule-src">{src}</a></td></tr>)}</tbody>
            </table>
          </div>
          <ul style={{ marginBottom: 0 }}>{SAFETY_NOTES.map((t) => <li key={t}>{t}</li>)}</ul>
        </section>

        <section id="rule-4">
          <h2><span className="hn">4</span>확인 점수 (0~100)</h2>
          <p style={{ marginTop: 0 }}>점수 = <b>A 오늘 통화</b> + <b>B 최근 추세</b> + <b>C 연락 상태</b></p>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>구분</th><th>계산</th><th style={{ textAlign: 'right' }}>최대</th></tr></thead>
              <tbody>{SCORE.map(([k, v, m]) => <tr key={k}><td style={{ whiteSpace: 'nowrap' }}><b>{k}</b></td><td>{v}</td><td className="num">{m}</td></tr>)}</tbody>
            </table>
          </div>
        </section>

        <section id="rule-5">
          <h2><span className="hn">5</span>단계 (단계는 사실로, 점수는 순서로)</h2>
          <p style={{ marginTop: 0 }}>{GRADE_WHY_R3}</p>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>단계</th><th>조건</th><th>생활지원사에게</th></tr></thead>
              <tbody>{GRADES.map(([g, cond, todo]) => <tr key={g}><td><GradeBadge grade={g} label={GRADE[g].label} /></td><td>{cond}</td><td>{todo}</td></tr>)}</tbody>
            </table>
          </div>
          <ul>{GRADE_NOTES.map((t) => <li key={t}>{t}</li>)}</ul>
          <p style={{ marginBottom: 0 }}>{GRADE_RENAME}</p>
        </section>

        <section id="rule-6">
          <h2><span className="hn">6</span>이유 표시 형식</h2>
          <pre className="pre">{REASON_EXAMPLE}</pre>
        </section>

        <section id="rule-7">
          <h2><span className="hn">7</span>이 값들은 가설이에요</h2>
          <p style={{ margin: 0 }}>{HYPOTHESIS}</p>
        </section>

        <section id="rule-8">
          <h2><span className="hn">8</span>어려움 유형 (점수와 별개)</h2>
          <p style={{ marginTop: 0 }}>{NEEDS_INTRO}</p>
          <p>
            점수에는 <b>넣지 않아요</b>(같은 ‘식사 주의’라도 점수는 같아요). 다만 어려움이 있으면 ‘특이 표현 없음’이 될 수 없어 단계는 최소 추가 확인이에요. 생활지원사 화면의 ‘어려움’과 사는 지역 복지서비스 연계(한국사회보장정보원 지자체·중앙부처 복지서비스)의 입력으로만 써요.
          </p>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>유형</th><th>예</th><th>아닌 것</th></tr></thead>
              <tbody>{NEEDS.map(([k, ex, not]) => <tr key={k}><td style={{ whiteSpace: 'nowrap' }}><NeedChip need={{ type: k, label: NEED[k].label }} /></td><td>{ex}</td><td>{not}</td></tr>)}</tbody>
            </table>
          </div>
          <ul style={{ marginBottom: 0 }}>{NEEDS_NOTES.map((t) => <li key={t}>{t}</li>)}</ul>
        </section>

        <section id="rule-src">
          <h2><span className="hn">9</span>근거 출처 (2026-11-16 조사)</h2>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>표시</th><th>출처</th><th>이 규칙에 쓴 내용</th></tr></thead>
              <tbody>{SOURCES.map(([k, name, url, used]) => <tr key={k}><td><b>{k}</b></td><td><a href={url} target="_blank" rel="noreferrer">{name} ↗</a></td><td>{used}</td></tr>)}</tbody>
            </table>
          </div>
          <p style={{ marginBottom: 0 }}>{SOURCES_GAP}</p>
        </section>
      </div>
        </div>
      </div>
    </div>
  );
}
