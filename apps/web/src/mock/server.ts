// VITE_MOCK=1일 때 /api 대신 응답하는 메모리 속 가짜 서버.
// 새로고침하면 처음 상태로 돌아간다. 실시간 통화는 시간이 흐르면 대본대로 한 턴씩 늘어난다.
import { ApiError } from '../shared/api';
import { kstDate } from '../shared/time';
import type {
  AiRun, Assessment, CallDetail, CallStatus, CallSummary, Dashboard, Day, Grade, Health, LiveCall, Resident, ResidentDetail, ResidentInput, ResidentRow, StaffCheck, Topic, Turn,
} from '../shared/types';
import {
  RESIDENTS, WELFARE, SCRIPT_GOOD, SCRIPT_HAN, SCRIPT_KANG, SCRIPT_KIM, SCRIPT_LEE, SCRIPT_PARK, addSec, assess, at, buildTurns, week, type Script,
} from './fixtures';

type Live = { t0: number; ringMs: number; gapMs: number; final: Assessment; summary: string };
type MockCall = Omit<CallSummary, 'status_label'> & { turns: (Turn & { offset: number })[]; runs: AiRun[]; staff_check: StaffCheck | null; live?: Live };

const STATUS_LABEL: Record<CallStatus, string> = {
  ringing: '벨 울리는 중', in_progress: '통화 중', completed: '통화 완료', interrupted: '통화 중단', missed: '미응답', declined: '거절',
};

let residents: Resident[] = [];
let calls: MockCall[] = [];
let weeks = new Map<number, Day[]>();
let nextCallId = 400;

function completedCall(id: number, rid: number, script: Script, start: string, sec: number, a: Assessment, summary: string): MockCall {
  const r = residents.find((x) => x.id === rid)!;
  const { turns, runs } = buildTurns(r.name, script, start, Math.max(4, Math.floor(sec / 13)));
  return {
    id, resident_id: rid, resident_name: r.name, status: 'completed', created_at: addSec(start, -2), started_at: start, ended_at: addSec(start, sec),
    summary, assessment: a, turns, runs, staff_check: null,
  };
}

function missedCall(id: number, rid: number, time: string, a: Assessment | null, days = 0): MockCall {
  const r = residents.find((x) => x.id === rid)!;
  return { id, resident_id: rid, resident_name: r.name, status: 'missed', created_at: at(time, days), started_at: null, ended_at: addSec(at(time, days), 30), summary: null, assessment: a, turns: [], runs: [], staff_check: null };
}

function liveCall(id: number, rid: number, script: Script, final: Assessment, summary: string, alreadyMs: number): MockCall {
  const r = residents.find((x) => x.id === rid)!;
  const now = Date.now();
  const t0 = now - alreadyMs;
  const { turns, runs } = buildTurns(r.name, script, new Date(t0 + 4000).toISOString(), 5);
  return {
    id, resident_id: rid, resident_name: r.name, status: 'ringing', created_at: new Date(t0).toISOString(), started_at: null, ended_at: null, summary: null, assessment: null,
    turns, runs, staff_check: null, live: { t0, ringMs: 4000, gapMs: 5000, final, summary },
  };
}

function seed() {
  residents = RESIDENTS.map((r) => ({ ...r }));
  const kimA = assess(SCRIPT_KIM, 'today', 40, [
    { kind: 'trend', chip: '식사 3일 연속', points: 10, quote: null },
    { kind: 'trend', chip: '수면 2일 연속', points: 5, quote: null },
    { kind: 'contact', chip: '어제 미응답', points: 10, quote: null },
  ]);
  const parkA = assess(SCRIPT_PARK, 'urgent', 15, [], [{ category: '낙상', quote: '어제 화장실에서 넘어졌어' }]);
  const hanA = assess(SCRIPT_HAN, 'today', 25, [{ kind: 'trend', chip: '복약 2일 연속', points: 5, quote: null }]);
  const leeA = assess(SCRIPT_LEE, 'watch', 15, [{ kind: 'trend', chip: '수면 2일 연속', points: 5, quote: null }]);
  const choiA = assess(null, 'watch', 20, [{ kind: 'contact', chip: '연속 미응답 2회', points: 20, quote: null }]);
  const choiA1 = assess(null, 'watch', 10, [{ kind: 'contact', chip: '오늘 미응답 1회', points: 10, quote: null }]);
  const limScript: Script = { ...SCRIPT_GOOD, body: SCRIPT_KIM.body, meal: SCRIPT_KIM.meal, sleep: { ...SCRIPT_KIM.sleep, origin: 'llm' } };

  calls = [
    completedCall(223, 9, SCRIPT_GOOD, at('09:02:10'), 140, assess(SCRIPT_GOOD, 'ok', 0), '다섯 가지 모두 좋다고 하셨어요.'),
    completedCall(224, 8, SCRIPT_GOOD, at('09:16:40'), 132, assess(SCRIPT_GOOD, 'ok', 0), '다섯 가지 모두 좋다고 하셨어요.'),
    completedCall(225, 7, SCRIPT_KANG, at('09:31:05'), 160, assess(SCRIPT_KANG, 'ok', 10), '식사는 하셨지만 혼자 차려 드시기 힘들다고 하셨어요. 잠을 조금 뒤척이셨어요.'),
    completedCall(226, 6, SCRIPT_GOOD, at('09:47:00'), 150, assess(SCRIPT_GOOD, 'ok', 0), '다섯 가지 모두 좋다고 하셨어요.'),
    completedCall(228, 2, SCRIPT_PARK, at('10:04:12'), 241, parkA, '어제 화장실에서 넘어지셨다고 하셨어요. 허리 통증으로 잠도 설치셨어요.'),
    completedCall(231, 1, SCRIPT_KIM, at('10:31:04'), 192, kimA, '다섯 가지 중 네 가지를 들었어요. 식사가 사흘째 좋지 않아요.'),
    completedCall(232, 5, SCRIPT_HAN, at('10:41:30'), 185, hanA, '어지럼을 말씀하셨고, 약이 떨어져 며칠 못 드셨대요.'),
    completedCall(233, 4, SCRIPT_LEE, at('10:52:20'), 168, leeA, '밤에 자주 깨시고 조금 적적하다고 하셨어요.'),
    missedCall(236, 3, '11:00:00', choiA1),
    missedCall(240, 3, '11:20:00', choiA),
    liveCall(300, 12, limScript, assess(limScript, 'watch', 15), '식사를 이틀째 못 하셨고 잠을 설치셨어요.', 4000 + 5000 * 5 + 1500),
  ];

  // 7일 기록 (오래된 날 → 오늘)
  const W = (rid: number, rows: Partial<Record<Topic, string>>, today: Parameters<typeof week>[1]) => weeks.set(rid, week(rows, today));
  weeks = new Map();
  W(1, { body: 'gggggmg', meal: 'ggyrrmr', sleep: 'gyggymy', med: 'gggggmu', mood: 'gggggmg' }, { grade: 'today', score: 40, status: 'completed' });
  W(2, { body: 'ggggggr', sleep: 'ggggggy' }, { grade: 'urgent', score: 15, status: 'completed' });
  const m = 'gggggmm';
  W(3, { body: m, meal: m, sleep: m, med: m, mood: m }, { grade: 'watch', score: 20, status: 'missed' });
  W(4, { sleep: 'gggggyy', mood: 'ggggggy' }, { grade: 'watch', score: 15, status: 'completed' });
  W(5, { body: 'gggggyr', med: 'gggggrr' }, { grade: 'today', score: 25, status: 'completed' });
  W(6, {}, { grade: 'ok', score: 0, status: 'completed' });
  W(7, { meal: 'ggggggy', sleep: 'ggggggy' }, { grade: 'ok', score: 10, status: 'completed' });
  W(8, {}, { grade: 'ok', score: 0, status: 'completed' });
  W(9, {}, { grade: 'ok', score: 0, status: 'completed' });
  W(10, {}, { grade: null, score: null, status: 'not_called' });
  W(11, {}, { grade: null, score: null, status: 'not_called' });
  W(12, {}, { grade: null, score: null, status: 'in_progress' });

  // 지난 6일 통화 기록(턴 없이 요약만)
  let pid = 100;
  for (const r of residents) {
    weeks.get(r.id)!.slice(0, 6).forEach((d, i) => {
      const days = i - 6;
      const time = r.call_time;
      if (d.call_status === 'missed') calls.push(missedCall(pid++, r.id, time, null, days));
      if (d.call_status !== 'completed' || !d.items) return;
      const a = assess(null, d.grade ?? 'ok', d.score ?? 0);
      for (const t of Object.keys(d.items) as Topic[]) a.items[t] = { status: d.items[t], quote: null, origin: 'llm' };
      a.needs_check = (Object.keys(d.items) as Topic[]).filter((t) => d.items![t] === 'unknown');
      const start = at(`${time}:05`, days);
      calls.push({ id: pid++, resident_id: r.id, resident_name: r.name, status: 'completed', created_at: start, started_at: start, ended_at: addSec(start, 150), summary: null, assessment: a, turns: [], runs: [], staff_check: null });
    });
  }
  nextCallId = 400;
}
seed();

// ── 실시간 통화를 시간에 맞춰 펼친다 ─────────────────
function view(c: MockCall): MockCall {
  if (!c.live) return c;
  const L = c.live;
  const el = Date.now() - L.t0 - L.ringMs;
  if (el < 0) return { ...c, status: 'ringing', turns: [], runs: [] };
  const start = new Date(L.t0 + L.ringMs).toISOString();
  const shown = c.turns.filter((t) => t.offset * 1000 <= el);
  const done = shown.length === c.turns.length;
  const lastAt = c.turns[c.turns.length - 1].offset;
  const runs = c.runs.filter((r) => new Date(r.at).getTime() <= Date.now() || done);
  if (done && el >= lastAt * 1000 + 3000) {
    return { ...c, status: 'completed', started_at: start, ended_at: new Date(L.t0 + L.ringMs + lastAt * 1000 + 3000).toISOString(), turns: shown, runs, assessment: L.final, summary: L.summary };
  }
  return { ...c, status: 'in_progress', started_at: start, turns: shown, runs };
}

function stepOf(c: MockCall) {
  const asked = c.turns.filter((t) => t.role === 'ai' && t.topic).map((t) => t.topic);
  const order: Topic[] = ['body', 'meal', 'sleep', 'med', 'mood'];
  const last = asked[asked.length - 1];
  const index = c.status === 'completed' ? 5 : last ? order.indexOf(last) + 1 : 0;
  return { index, total: 5 };
}

const summary = (c: MockCall): CallSummary => {
  const { turns: _t, runs: _r, staff_check: _s, live: _l, ...rest } = c;
  return { ...rest, status_label: STATUS_LABEL[c.status] };
};
const toTurn = ({ offset: _o, ...t }: Turn & { offset: number }): Turn => t;
const allViews = () => calls.map(view);
const isToday = (iso: string) => kstDate(new Date(iso)) === kstDate();
const GRADE_RANK: Record<Grade, number> = { urgent: 0, today: 1, watch: 2, ok: 3 };

function dashboard(): Dashboard {
  const vs = allViews();
  const rows: ResidentRow[] = residents.map((r) => {
    const todays = vs.filter((c) => c.resident_id === r.id && isToday(c.created_at)).sort((a, b) => b.created_at.localeCompare(a.created_at));
    const latest = todays[0];
    const ended = todays.find((c) => c.assessment);
    return {
      ...r,
      today: latest ? { call_id: latest.id, status: latest.status, status_label: STATUS_LABEL[latest.status] } : { call_id: null, status: 'not_called', status_label: '통화 전' },
      assessment: ended?.assessment ?? null,
      staff_check: ended?.staff_check ?? null,
    };
  });
  rows.sort((a, b) => {
    if (!a.assessment || !b.assessment) return a.assessment ? -1 : b.assessment ? 1 : a.call_time.localeCompare(b.call_time);
    return GRADE_RANK[a.assessment.grade] - GRADE_RANK[b.assessment.grade] || b.assessment.score - a.assessment.score;
  });
  const g = (k: Grade) => rows.filter((r) => r.assessment?.grade === k).length;
  return {
    date: kstDate(),
    counts: {
      total: rows.length, urgent: g('urgent'), today: g('today'), watch: g('watch'), ok: g('ok'),
      missed: rows.filter((r) => r.today.status === 'missed').length,
      not_called: rows.filter((r) => r.today.status === 'not_called').length,
    },
    residents: rows,
  };
}

function residentDetail(id: number): ResidentDetail {
  const r = residents.find((x) => x.id === id);
  if (!r) throw new ApiError(404, '어르신을 찾을 수 없어요.');
  const w = weeks.get(id) ?? week({}, { grade: null, score: null, status: 'not_called' });
  const vs = allViews();
  // 오늘 칸은 현재 통화 상태를 반영한다
  const todayCall = vs.filter((c) => c.resident_id === id && isToday(c.created_at)).sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  const last = { ...w[6] };
  if (todayCall?.status === 'completed' && todayCall.assessment) {
    last.call_status = 'completed';
    last.items = Object.fromEntries(Object.entries(todayCall.assessment.items).map(([k, v]) => [k, v.status])) as Day['items'];
    last.grade = todayCall.assessment.grade;
    last.score = todayCall.assessment.score;
  } else if (todayCall) last.call_status = todayCall.status;
  return {
    resident: r,
    week: [...w.slice(0, 6), last],
    calls: vs.filter((c) => c.resident_id === id).sort((a, b) => b.created_at.localeCompare(a.created_at)).map(summary),
    welfare: WELFARE[id] ?? [],
  };
}

function validate(b: Partial<ResidentInput>, partial: boolean) {
  if (!partial || b.name !== undefined) if (!b.name?.trim()) throw new ApiError(422, '이름을 적어 주세요.');
  if (!partial || b.age !== undefined) if (!b.age || b.age < 50 || b.age > 120) throw new ApiError(422, '나이는 50~120 사이로 적어 주세요.');
  if (!partial || b.region !== undefined) if ((b.region ?? '').trim().split(/\s+/).length < 2) throw new ApiError(422, '지역을 시도와 시군구까지 적어 주세요.');
  if (!partial || b.call_time !== undefined) if (!/^\d{2}:\d{2}$/.test(b.call_time ?? '')) throw new ApiError(422, '전화 시간을 HH:MM으로 적어 주세요.');
}

const delay = () => new Promise((r) => setTimeout(r, 120));

export async function mockFetch<T>(method: string, fullPath: string, body?: unknown): Promise<T> {
  await delay();
  const [path, qs] = fullPath.split('?');
  const q = new URLSearchParams(qs ?? '');
  const seg = path.split('/').filter(Boolean); // ['staff','calls','231']
  const key = `${method} /${seg.map((s) => (/^\d+$/.test(s) ? ':id' : s)).join('/')}`;
  const id = Number(seg.find((s) => /^\d+$/.test(s)));
  let out: unknown;

  switch (key) {
    case 'GET /health':
      out = { ok: true, db: true, llm: { mode: 'ollama', model: 'ax4-light:q4_K_M', reachable: true } } satisfies Health;
      break;
    case 'GET /staff/dashboard':
      out = dashboard();
      break;
    case 'GET /staff/residents/:id':
      out = residentDetail(id);
      break;
    case 'POST /staff/residents': {
      const b = body as ResidentInput;
      validate(b, false);
      const nid = Math.max(...residents.map((r) => r.id)) + 1;
      const r: Resident = { id: nid, code: `KY-${String(nid).padStart(2, '0')}`, name: b.name.trim(), age: b.age, region: b.region.trim(), neighborhood: b.neighborhood.trim(), call_time: b.call_time, memo: b.memo?.trim() || null, is_virtual: true };
      residents.push(r);
      weeks.set(nid, week({}, { grade: null, score: null, status: 'not_called' }).map((d, i) => (i < 6 ? { ...d, call_status: 'not_called', items: null, grade: null, score: null } : d)));
      out = r;
      break;
    }
    case 'PATCH /staff/residents/:id': {
      const r = residents.find((x) => x.id === id);
      if (!r) throw new ApiError(404, '어르신을 찾을 수 없어요.');
      const b = body as Partial<ResidentInput>;
      validate(b, true);
      Object.assign(r, b, b.memo !== undefined ? { memo: b.memo?.trim() || null } : {});
      calls.forEach((c) => c.resident_id === id && (c.resident_name = r.name));
      out = r;
      break;
    }
    case 'POST /staff/residents/:id/call': {
      const r = residents.find((x) => x.id === id);
      if (!r) throw new ApiError(404, '어르신을 찾을 수 없어요.');
      if (allViews().some((c) => c.resident_id === id && (c.status === 'ringing' || c.status === 'in_progress'))) throw new ApiError(409, '이미 벨이 울리고 있거나 통화 중이에요.');
      const c = liveCall(nextCallId++, id, SCRIPT_GOOD, assess(SCRIPT_GOOD, 'ok', 0), '다섯 가지 모두 좋다고 하셨어요.', 0);
      c.created_at = new Date().toISOString();
      calls.push(c);
      out = summary(view(c));
      break;
    }
    case 'GET /staff/calls': {
      const date = q.get('date');
      const rid = q.get('resident_id');
      out = allViews()
        .filter((c) => (!date || kstDate(new Date(c.created_at)) === date) && (!rid || c.resident_id === Number(rid)))
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .slice(0, Number(q.get('limit') ?? 50))
        .map(summary);
      break;
    }
    case 'GET /staff/calls/:id': {
      const c = allViews().find((x) => x.id === id);
      if (!c) throw new ApiError(404, '통화를 찾을 수 없어요.');
      // 이 통화에서 찾은 어려움에 해당하는 연계만
      const types = new Set((c.assessment?.needs ?? []).map((n) => n.type));
      const welfare = (WELFARE[c.resident_id] ?? []).filter((m) => types.has(m.need));
      out = { ...summary(c), turns: c.turns.map(toTurn), ai_runs: c.runs, staff_check: c.staff_check, step: stepOf(c), welfare } satisfies CallDetail;
      break;
    }
    case 'GET /staff/live':
      out = { calls: allViews().filter((c) => c.status === 'ringing' || c.status === 'in_progress').map((c) => ({ ...summary(c), step: stepOf(c) }) satisfies LiveCall) };
      break;
    case 'POST /staff/demo/reset':
      seed();
      out = { ok: true };
      break;
    case 'POST /staff/calls/:id/check': {
      const c = calls.find((x) => x.id === id);
      if (!c) throw new ApiError(404, '통화를 찾을 수 없어요.');
      const note = String((body as { note?: string })?.note ?? '');
      if (note.length > 300) throw new ApiError(422, '확인 기록은 300자까지 적을 수 있어요.');
      c.staff_check = { checked: true, note, at: new Date().toISOString() };
      out = c.staff_check;
      break;
    }
    default:
      throw new ApiError(404, `가짜 서버에 없는 경로예요: ${method} ${path}`);
  }
  return structuredClone(out) as T;
}
