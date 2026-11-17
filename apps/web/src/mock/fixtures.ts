// 가짜 데이터 — CONTRACT.md 모양 그대로, 디자인 시안(preview-v3)의 예시를 따른다.
// 모두 가상 인물이다. 시각은 '오늘(한국 시간)'을 기준으로 만든다.
import { kstDate } from '../shared/time';
import type { AiRun, Assessment, Day, Grade, ItemStatus, Need, Origin, Reason, Resident, Topic, Turn, WelfareMatch } from '../shared/types';

export const MODEL = 'ax4-light:q4_K_M';
const TODAY = kstDate();

export function dateOffset(days: number): string {
  const d = new Date(`${TODAY}T12:00:00+09:00`);
  d.setUTCDate(d.getUTCDate() + days);
  return kstDate(d);
}
export const at = (time: string, days = 0) => `${dateOffset(days)}T${time.length === 5 ? `${time}:00` : time}+09:00`;
export const addSec = (iso: string, s: number) => {
  const d = new Date(new Date(iso).getTime() + s * 1000);
  const t = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(d);
  return `${kstDate(d)}T${t}+09:00`;
};

export const RESIDENTS: Resident[] = [
  { id: 1, code: 'KY-01', name: '김영자', age: 78, region: '대전광역시 중구', neighborhood: '중구 은행동', call_time: '10:30', memo: '혼자 사세요 · 아침을 자주 거르세요', is_virtual: true },
  { id: 2, code: 'KY-02', name: '박정호', age: 75, region: '대전광역시 유성구', neighborhood: '유성구 봉명동', call_time: '10:00', memo: null, is_virtual: true },
  { id: 3, code: 'KY-03', name: '최복순', age: 80, region: '대전광역시 동구', neighborhood: '동구 가양동', call_time: '11:00', memo: '귀가 어두우셔서 천천히', is_virtual: true },
  { id: 4, code: 'KY-04', name: '이순희', age: 82, region: '대전광역시 서구', neighborhood: '서구 둔산동', call_time: '10:50', memo: null, is_virtual: true },
  { id: 5, code: 'KY-05', name: '한옥분', age: 79, region: '대전광역시 서구', neighborhood: '서구 탄방동', call_time: '10:40', memo: '혈압약 복용 중', is_virtual: true },
  { id: 6, code: 'KY-06', name: '정말순', age: 77, region: '대전광역시 중구', neighborhood: '중구 대흥동', call_time: '09:45', memo: null, is_virtual: true },
  { id: 7, code: 'KY-07', name: '강금자', age: 81, region: '서울특별시 서대문구', neighborhood: '서대문구 홍은동', call_time: '09:30', memo: '서울 사는 따님 댁 근처로 이사하셨어요', is_virtual: true },
  { id: 8, code: 'KY-08', name: '윤덕수', age: 76, region: '대전광역시 유성구', neighborhood: '유성구 노은동', call_time: '09:15', memo: null, is_virtual: true },
  { id: 9, code: 'KY-09', name: '장순례', age: 84, region: '대전광역시 동구', neighborhood: '동구 판암동', call_time: '09:00', memo: null, is_virtual: true },
  { id: 10, code: 'KY-10', name: '오말녀', age: 79, region: '대전광역시 중구', neighborhood: '중구 문화동', call_time: '14:00', memo: null, is_virtual: true },
  { id: 11, code: 'KY-11', name: '서정자', age: 83, region: '대전광역시 서구', neighborhood: '서구 갈마동', call_time: '15:00', memo: null, is_virtual: true },
  { id: 12, code: 'KY-12', name: '임봉순', age: 80, region: '대전광역시 대덕구', neighborhood: '대덕구 송촌동', call_time: '11:30', memo: null, is_virtual: true },
];

// ── 대화 대본 ────────────────────────────────────
export const QUESTION: Record<Topic, string> = {
  body: '오늘 몸은 좀 어떠세요?',
  meal: '오늘 아침 식사는 하셨어요?',
  sleep: '어젯밤 잠은 편히 주무셨어요?',
  med: '드시는 약은 잘 챙겨 드셨어요?',
  mood: '요즘 기분은 어떠세요?',
};
const EMPATHY: Record<ItemStatus, string> = {
  good: '다행이에요.',
  caution: '그러셨군요. 오늘은 조금 쉬어 가세요.',
  risk: '아이고, 걱정되네요.',
  unknown: '괜찮아요. 다음에 다시 여쭤볼게요.',
};

export type Answer = { text: string; status: ItemStatus; origin: Origin; quote?: string; empathy?: string; retries?: string[]; ms?: number; needs?: Need[] };
export type Script = Record<Topic, Answer>;
const ORDER: Topic[] = ['body', 'meal', 'sleep', 'med', 'mood'];

/** 대본 → 턴 + AI 실행 기록. gap초 간격. */
export function buildTurns(name: string, s: Script, start: string, gap = 6): { turns: (Turn & { offset: number })[]; runs: AiRun[] } {
  const turns: (Turn & { offset: number })[] = [];
  const runs: AiRun[] = [];
  let t = 0;
  const push = (turn: Omit<Turn, 'at'>) => {
    turns.push({ ...turn, at: addSec(start, t), offset: t });
    t += gap;
  };
  push({ role: 'ai', topic: 'body', text: `${name} 어르신, 안녕하세요. 안심온이에요. ${QUESTION.body}`, ms: null });
  ORDER.forEach((topic, i) => {
    const a = s[topic];
    for (const r of a.retries ?? []) {
      push({ role: 'elder', topic, text: r, source: r ? 'stt' : 'silence', judged: [] });
      push({ role: 'ai', topic, text: `다시 여쭤볼게요. ${QUESTION[topic]}`, ms: null });
    }
    const judged = a.status === 'unknown' || a.origin === 'none' ? [] : [{ topic, status: a.status, origin: a.origin as 'llm' | 'rule' }];
    push({ role: 'elder', topic, text: a.text, source: a.text ? 'stt' : 'silence', judged, ...(a.needs?.length ? { needs: a.needs } : {}) });
    const atNow = addSec(start, t - 1); // 다음 AI 응답 직전
    // 턴마다 다른 시간이 나오도록 질문 순서로 조금씩 바꾼다
    const extractMs = a.origin === 'llm' ? a.ms ?? 371 + i * 23 : null;
    const empathyMs = a.status !== 'good' && a.status !== 'unknown' ? 262 + i * 19 : null;
    if (extractMs != null) runs.push({ at: atNow, step: 'extract', model: MODEL, ms: extractMs, outcome: 'ok', note: null });
    if (a.origin === 'rule') runs.push({ at: atNow, step: 'extract', model: MODEL, ms: null, outcome: 'fallback', note: '시간 초과 4.0s' });
    const next = ORDER[i + 1];
    const emp = a.empathy ?? EMPATHY[a.status];
    if (empathyMs != null) runs.push({ at: addSec(atNow, 0), step: 'empathy', model: MODEL, ms: empathyMs, outcome: 'ok', note: null });
    const ms = extractMs == null && empathyMs == null ? null : (extractMs ?? 0) + (empathyMs ?? 0);
    push({ role: 'ai', topic: next ?? null, text: next ? `${emp} ${QUESTION[next]}` : `${emp} 오늘도 이야기 나눠 주셔서 고마워요. 내일 또 전화드릴게요.`, ms });
  });
  runs.push({ at: addSec(start, t), step: 'summary', model: MODEL, ms: 1200, outcome: 'ok', note: null });
  return { turns, runs };
}

const good = (text: string, ms?: number): Answer => ({ text, status: 'good', origin: 'llm', quote: text.replace(/[.。]$/, ''), ms });
const need = (type: Need['type'], label: string, quote: string, origin: Need['origin'] = 'llm'): Need => ({ type, label, quote, origin });

export const SCRIPT_KIM: Script = {
  body: good('몸은 그럭저럭 괜찮아', 412),
  meal: { text: '이틀째 밥을 못 먹었어. 반찬이 없어서', status: 'risk', origin: 'llm', quote: '이틀째 밥을 못 먹었어', empathy: '아이고, 걱정되네요. 죽이라도 조금 드셔 보세요.', ms: 405, needs: [need('meal_difficulty', '식사 어려움', '반찬이 없어서', 'rule')] },
  sleep: { text: '잠은 좀 설쳤지', status: 'caution', origin: 'rule', quote: '잠은 좀 설쳤지' },
  med: { text: '', status: 'unknown', origin: 'none', retries: ['응? 뭐라고?', ''] },
  mood: good('전화해 줘서 좋지 뭐', 388),
};

export const SCRIPT_GOOD: Script = {
  body: good('응, 괜찮아'),
  meal: good('아침 잘 먹었어'),
  sleep: good('푹 잤어'),
  med: good('약도 먹었지'),
  mood: good('기분 좋아'),
};

export const SCRIPT_PARK: Script = {
  body: { text: '어제 화장실에서 넘어졌어. 허리가 아파', status: 'risk', origin: 'llm', quote: '어제 화장실에서 넘어졌어', empathy: '지금 바로 생활지원사님께 알려 드릴게요. 위급하시면 119에 전화하세요.' },
  meal: good('밥은 먹었어'),
  sleep: { text: '허리 때문에 잘 못 잤어', status: 'caution', origin: 'llm', quote: '잘 못 잤어' },
  med: good('약은 먹었어'),
  mood: good('그냥 그래'),
};

export const SCRIPT_HAN: Script = {
  body: { text: '자꾸 어지러워', status: 'risk', origin: 'llm', quote: '어지러워' },
  meal: good('밥은 조금 먹었어'),
  sleep: good('잘 잤어'),
  med: { text: '약을 며칠 안 먹었어. 다 떨어져서', status: 'risk', origin: 'llm', quote: '약을 며칠 안 먹었어' },
  mood: good('괜찮아'),
};

export const SCRIPT_LEE: Script = {
  body: good('몸은 괜찮아'),
  meal: good('먹었어'),
  sleep: { text: '밤에 자꾸 깨', status: 'caution', origin: 'llm', quote: '밤에 자꾸 깨' },
  med: good('먹었지'),
  mood: { text: '좀 적적하지. 말할 사람이 없어', status: 'caution', origin: 'rule', quote: '좀 적적하지', needs: [need('loneliness', '외로움', '말할 사람이 없어', 'rule')] },
};

export const SCRIPT_KANG: Script = {
  ...SCRIPT_GOOD,
  meal: { text: '먹긴 먹었는데, 혼자 차려 먹기가 힘들어', status: 'caution', origin: 'llm', quote: '혼자 차려 먹기가 힘들어', empathy: '그러셨군요. 혼자 챙겨 드시기 쉽지 않죠.', needs: [need('meal_difficulty', '식사 어려움', '혼자 차려 먹기가 힘들어')] },
  sleep: { text: '조금 뒤척였어', status: 'caution', origin: 'llm', quote: '조금 뒤척였어' },
};

// ── 판정 ─────────────────────────────────────────
const LABEL: Record<Grade, string> = { urgent: '즉시 확인', today: '우선 확인', watch: '추가 확인', ok: '특이 표현 없음' };

export function assess(script: Script | null, grade: Grade, score: number, extra: Reason[] = [], safety: Assessment['safety'] = []): Assessment {
  const items = {} as Assessment['items'];
  const itemReasons: Reason[] = [];
  const names: Record<Topic, string> = { body: '몸 상태', meal: '식사', sleep: '수면', med: '복약', mood: '기분' };
  for (const t of ORDER) {
    const a = script?.[t];
    items[t] = a ? { status: a.status, quote: a.status === 'unknown' ? null : a.quote ?? a.text, origin: a.origin } : { status: 'unknown', quote: null, origin: 'none' };
    if (a?.status === 'risk') itemReasons.push({ kind: 'item', chip: `${names[t]} 위험`, points: 10, quote: a.quote ?? a.text });
    if (a?.status === 'caution') itemReasons.push({ kind: 'item', chip: `${names[t]} 주의`, points: 5, quote: a.quote ?? a.text });
  }
  const safetyReasons: Reason[] = safety.map((s) => ({ kind: 'safety', chip: `${s.category} 표현`, points: 0, quote: s.quote }));
  return {
    score,
    grade,
    grade_label: LABEL[grade],
    reasons: [...safetyReasons, ...itemReasons, ...extra],
    items,
    safety,
    needs_check: ORDER.filter((t) => items[t].status === 'unknown'),
    needs: ORDER.flatMap((t) => script?.[t]?.needs ?? []),
    rule_version: 'r2.1',
  };
}

// ── 7일 기록 ─────────────────────────────────────
type W = 'g' | 'y' | 'r' | 'u' | 'n' | 'm';
const ST: Record<'g' | 'y' | 'r' | 'u', ItemStatus> = { g: 'good', y: 'caution', r: 'risk', u: 'unknown' };

/** rows: 항목별 7글자(오래된 날 → 오늘). n=통화 안 함, m=미응답 */
export function week(rows: Partial<Record<Topic, string>>, today: { grade: Grade | null; score: number | null; status: Day['call_status'] }): Day[] {
  return Array.from({ length: 7 }, (_, i) => {
    const date = dateOffset(i - 6);
    const marks = ORDER.map((t) => (rows[t] ?? 'gggggg' + (today.status === 'completed' ? 'g' : 'n'))[i] as W);
    const off = marks.find((m) => m === 'n' || m === 'm');
    if (i === 6 && today.status !== 'completed' && today.status !== 'interrupted') {
      return { date, call_status: today.status, items: null, grade: today.grade, score: today.score };
    }
    if (off) return { date, call_status: off === 'm' ? 'missed' : 'not_called', items: null, grade: null, score: null };
    const items = Object.fromEntries(ORDER.map((t, k) => [t, ST[marks[k] as 'g']])) as Record<Topic, ItemStatus>;
    const pts = Object.values(items).reduce((s, v) => s + (v === 'risk' ? 10 : v === 'caution' ? 5 : 0), 0);
    const grade: Grade = i === 6 && today.grade ? today.grade : pts >= 40 ? 'today' : pts >= 15 ? 'watch' : 'ok';
    return { date, call_status: 'completed', items, grade, score: i === 6 && today.score != null ? today.score : pts };
  });
}

// ── 복지서비스 연계 (F11) ─────────────────────────
// 한국사회보장정보원 지자체·중앙부처 복지서비스 목록에서 고른 모양. 문구는 원문 일부를 줄인 가상 예시다.
export const WELFARE_AS_OF = '2026-11-13';
const bokjiro = (id: string, local: boolean) => `https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId=${id}&wlfareInfoReldBztpCd=${local ? '02' : '01'}`;

export const WELFARE: Record<number, WelfareMatch[]> = {
  // 강금자 (서울 서대문구) — 지자체 사업 3건
  7: [
    {
      need: 'meal_difficulty', need_label: '식사 어려움', region: '서울특별시 서대문구', note: null, data_as_of: WELFARE_AS_OF,
      services: [
        {
          id: 'WLF00004781', name: '저소득 어르신 무료급식 지원 사업', org: '서대문구 어르신복지과', area: '서울특별시 서대문구', source: '지자체복지서비스',
          summary: '식사를 챙기기 어려운 저소득 어르신께 경로식당 점심이나 거동이 불편하면 도시락을 드려요.',
          target_quote: '관내 거주 만 60세 이상 기초생활수급자 및 차상위계층 어르신 중 결식 우려가 있는 분',
          apply_quote: '거주지 동 주민센터 방문 신청', link: bokjiro('WLF00004781', true),
        },
        {
          id: 'WLF00005312', name: '고독사 예방 밑반찬 지원사업', org: '서대문구 복지정책과', area: '서울특별시 서대문구', source: '지자체복지서비스',
          summary: '홀로 사는 어르신께 주 1회 밑반찬을 배달하며 안부를 확인해요.',
          target_quote: '관내 1인 가구 중 고독사 위험이 있는 중장년·어르신',
          apply_quote: '동 주민센터 또는 복지플래너 상담 후 연계', link: bokjiro('WLF00005312', true),
        },
        {
          id: 'WLF00003957', name: '홀몸어르신 도시락 배달', org: '서대문구 어르신복지과', area: '서울특별시 서대문구', source: '지자체복지서비스',
          summary: '거동이 불편해 경로식당을 이용하기 어려운 홀몸어르신 댁으로 점심 도시락을 배달해요.',
          target_quote: null, apply_quote: '주소지 동 주민센터 신청', link: bokjiro('WLF00003957', true),
        },
      ],
    },
  ],
  // 김영자 (대전 중구) — 지자체 사업이 없어 중앙부처 서비스로
  1: [
    {
      need: 'meal_difficulty', need_label: '식사 어려움', region: '대전광역시 중구', data_as_of: WELFARE_AS_OF,
      note: '이 지역에는 맞는 지자체 사업이 없어 중앙부처 서비스를 보여 드려요.',
      services: [
        {
          id: 'WLF00001173', name: '농식품바우처', org: '농림축산식품부', area: '전국(중앙부처)', source: '중앙부처복지서비스',
          summary: '생계급여 수급 가구에 국산 채소·과일·우유 등을 살 수 있는 카드 포인트를 드려요.',
          target_quote: '중위소득 32% 이하 생계급여 수급 가구', apply_quote: '주소지 읍·면·동 행정복지센터 방문 신청', link: bokjiro('WLF00001173', false),
        },
        {
          id: 'WLF00000862', name: '푸드뱅크·푸드마켓 이용 지원', org: '보건복지부', area: '전국(중앙부처)', source: '중앙부처복지서비스',
          summary: '기부받은 식품과 생활용품을 결식 우려가 있는 분께 나눠 드려요.',
          target_quote: '결식 우려가 있는 저소득층, 홀로 사는 어르신 등', apply_quote: null, link: bokjiro('WLF00000862', false),
        },
      ],
    },
  ],
  // 이순희 (대전 서구) — 찾은 서비스가 없을 때
  4: [{ need: 'loneliness', need_label: '외로움', region: '대전광역시 서구', services: [], note: '이 지역 목록에서 맞는 서비스를 찾지 못했어요. 동 주민센터에 직접 여쭤 보세요.', data_as_of: WELFARE_AS_OF }],
};
