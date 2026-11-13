// 데이터 원칙 — 편집형(NYT·FT 굵은 괘선 + 큰 번호, GOV.UK 요약 목록): 왼쪽 큰 문장, 오른쪽 설명 + "이렇게 지켜요" 증거
import { Link } from 'react-router-dom';

type Proof = { label: string; to?: string; code?: boolean };
const ITEMS: { h: string; p: string; proof: Proof[] }[] = [
  {
    h: 'AI는 확인 대상을 늘리는 쪽으로만 써요',
    p: 'AI가 ‘괜찮다’고 해도 규칙이 잡은 위험 신호를 내리지 않아요. 낙상·호흡·자해 같은 안전 신호는 정해진 표현(규칙)으로만 잡고, AI가 끄지 못해요.',
    proof: [{ label: 'apps/api/tests/test_llm_fallback.py · test_llm_good_cannot_override_safety_regex', code: true }, { label: '판정 기준 3. 안전 신호', to: '/staff/rules#rule-3' }],
  },
  {
    h: '판정에는 어르신 말씀을 그대로 붙여요',
    p: 'AI 결과는 인용한 문장이 실제 대답 안에 있을 때만 써요. 인용이 없거나 AI가 늦으면(4초) 키워드 규칙이 대신 판정하고, 그 사실을 기록에 남겨요.',
    proof: [{ label: 'test_quote_not_in_answer_is_discarded · test_timeout_falls_back_to_rules_and_is_recorded', code: true }, { label: '통화 상세 · AI 실행 기록', to: '/staff/calls' }],
  },
  {
    h: '나이·성별은 점수에 넣지 않아요',
    p: '같은 말을 했으면 같은 점수예요. 나이는 어르신을 구분하는 데만 쓰고, 점수 계산 함수는 나이·성별을 입력으로 받지 않아요.',
    proof: [{ label: 'apps/api/tests/test_rules.py · test_age_and_gender_are_not_inputs', code: true }, { label: '판정 기준 4. 확인 점수', to: '/staff/rules#rule-4' }],
  },
  {
    h: '의료 판단이 아니에요',
    p: '점수는 생활지원사가 누구부터 연락할지 정하는 참고 순서예요. 진단·자동 신고를 하지 않고, 확인은 사람이 전화나 방문으로 해요.',
    proof: [{ label: '모든 화면 아래 고지 · 확인 기록 남기기(생활지원사)' }, { label: '판정 기준 5. 단계', to: '/staff/rules#rule-5' }],
  },
  {
    h: '로컬 AI만 써요',
    p: 'AI는 기관 PC의 Ollama(폐쇄망)에서만 돌아요. 대화 내용이 외부 서버로 나가지 않아요. AI가 꺼지면 키워드 규칙으로 끝까지 동작해요.',
    proof: [{ label: 'apps/api/app/services/llm.py', code: true }, { label: '외부 호출은 이 어댑터 하나뿐이에요' }, { label: '왼쪽 아래 ‘AI 연결’ 상태 카드' }],
  },
  {
    h: '통화 원문은 기관 서버에만 둬요',
    p: '대화 원문과 판정 기록은 수행기관 서버에만 저장해요. 보관 기간은 수행기관과 협의해 정하고, 지금 화면의 어르신·통화는 모두 지어낸 시연용 데이터예요.',
    proof: [{ label: '시연: 가상 데이터만 사용 · 상단 ‘가상 데이터’ 표시' }, { label: '보관 기간: 수행기관과 협의 예정' }],
  },
];

export function PrinciplesPage() {
  return (
    <div className="page">
      <article className="ed">
        <header className="ed-hd">
          <div className="eyebrow">근거 · 데이터 원칙</div>
          <h1 className="serif">안심온이 지키는 여섯 가지</h1>
          <p>약속만 적지 않고, 무엇이 그 약속을 지키게 하는지(테스트·코드·화면)를 같이 적었어요. 점수 계산은 <Link to="/staff/rules" className="ed-link">판정 기준</Link>에 있어요.</p>
        </header>
        <ol className="ed-list">
          {ITEMS.map((it, i) => (
            <li key={it.h}>
              <span className="ed-n" aria-hidden>{String(i + 1).padStart(2, '0')}</span>
              <h2 className="serif"><span className="sr">{i + 1}. </span>{it.h}</h2>
              <div className="ed-body">
                <p>{it.p}</p>
                <dl className="ed-proof">
                  <dt>이렇게 지켜요</dt>
                  {it.proof.map((x) => <dd key={x.label} className={x.code ? 'code' : undefined}>{x.to ? <Link to={x.to} className="ed-link">{x.label} ›</Link> : x.label}</dd>)}
                </dl>
              </div>
            </li>
          ))}
        </ol>
      </article>
    </div>
  );
}
