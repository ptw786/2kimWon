// packages/contracts/CONTRACT.md의 타입을 그대로 옮겼다. 계약이 바뀌면 여기도 같이 고친다.

export type Topic = 'body' | 'meal' | 'sleep' | 'med' | 'mood';
export type ItemStatus = 'good' | 'caution' | 'risk' | 'unknown';
export type Grade = 'urgent' | 'today' | 'watch' | 'ok';
export type CallStatus = 'ringing' | 'in_progress' | 'completed' | 'interrupted' | 'missed' | 'declined';
export type Origin = 'llm' | 'rule' | 'none';

export type NeedType = 'meal_difficulty' | 'sleep_problem' | 'help_request' | 'loneliness';
export type Need = { type: NeedType; label: string; quote: string; origin: 'llm' | 'rule' };

export type WelfareService = {
  id: string;
  name: string;
  org: string | null;
  area: string;
  summary: string | null;
  target_quote: string | null;
  apply_quote: string | null;
  link: string | null;
  source: '지자체복지서비스' | '중앙부처복지서비스';
};
export type WelfareMatch = { need: NeedType; need_label: string; region: string; services: WelfareService[]; note: string | null; data_as_of: string };

export type Reason = { kind: 'safety' | 'item' | 'trend' | 'contact'; chip: string; points: number; quote: string | null };

export type Assessment = {
  score: number;
  grade: Grade;
  grade_label: string;
  reasons: Reason[];
  items: Record<Topic, { status: ItemStatus; quote: string | null; origin: Origin }>;
  safety: { category: string; quote: string }[];
  needs_check: Topic[];
  needs?: Need[]; // v2.1 — 이전 서버는 보내지 않으므로 없을 수 있다
  rule_version: string;
};

export type CallSummary = {
  id: number;
  resident_id: number;
  resident_name: string;
  status: CallStatus;
  status_label: string;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  summary: string | null;
  assessment: Assessment | null;
};

export type Turn = {
  role: 'ai' | 'elder';
  text: string;
  topic: Topic | null;
  at: string;
  source?: 'stt' | 'text' | 'option' | 'silence';
  judged?: { topic: Topic; status: ItemStatus; origin: 'llm' | 'rule' }[];
  needs?: Need[]; // elder 턴에만
  ms?: number | null; // ai 턴에만 · null = 규칙만 사용
};

export type AiRun = {
  at: string;
  step: 'extract' | 'empathy' | 'summary';
  model: string | null;
  ms: number | null;
  outcome: 'ok' | 'fallback';
  note: string | null;
};

export type StaffCheck = { checked: boolean; note: string; at: string };
export type Step = { index: number; total: number };

export type CallDetail = CallSummary & { turns: Turn[]; ai_runs: AiRun[]; staff_check: StaffCheck | null; step: Step; welfare?: WelfareMatch[] };
export type LiveCall = CallSummary & { step: Step };

export type Resident = {
  id: number;
  code: string;
  name: string;
  age: number;
  region?: string; // '대전광역시 중구' (v2.1)
  neighborhood: string;
  call_time: string;
  memo: string | null;
  is_virtual: boolean;
};

export type ResidentRow = Resident & {
  today: { call_id: number | null; status: CallStatus | 'not_called'; status_label: string };
  assessment: Assessment | null;
  staff_check: StaffCheck | null;
};

export type Day = {
  date: string;
  call_status: CallStatus | 'not_called';
  items: Record<Topic, ItemStatus> | null;
  grade: Grade | null;
  score: number | null;
};

export type Dashboard = {
  date: string;
  counts: { total: number; urgent: number; today: number; watch: number; ok: number; missed: number; not_called: number };
  residents: ResidentRow[];
};

export type ResidentDetail = { resident: Resident; week: Day[]; calls: CallSummary[]; welfare?: WelfareMatch[] };

export type Health = { ok: boolean; db: boolean; llm: { mode: 'ollama' | 'rules'; model: string | null; reachable: boolean } };

export type ResidentInput = { name: string; age: number; region: string; neighborhood: string; call_time: string; memo?: string | null };
