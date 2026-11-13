import type { ReactNode } from 'react';
import { CALL, GRADE, ITEM, NEED, TOPIC_LABEL } from './status';
import type { CallStatus, Grade, ItemStatus, Need, ResidentRow, Topic } from './types';

export function GradeBadge({ grade, label }: { grade: Grade; label?: string }) {
  const m = GRADE[grade];
  return <span className={`badge ${m.cls}`}><span aria-hidden>{m.icon}</span>{label || m.label}</span>;
}

/** 어려움 유형 칩 — 점수와 별개라 버터색 하나로만 보인다 */
export function NeedChip({ need }: { need: Pick<Need, 'type' | 'label'> }) {
  const m = NEED[need.type];
  return <span className="need"><span aria-hidden>{m?.icon ?? '•'}</span>{need.label || m?.label}</span>;
}

/** 같은 유형은 한 번만 */
export const uniqNeeds = (needs: Need[] | undefined) => (needs ?? []).filter((n, i, all) => all.findIndex((x) => x.type === n.type) === i);

export function ItemBadge({ status, topic }: { status: ItemStatus; topic?: Topic }) {
  const m = ITEM[status];
  return <span className={`badge ${m.cls}`}><span aria-hidden>{m.icon}</span>{topic ? `${TOPIC_LABEL[topic]} ${m.label}` : m.label}</span>;
}

export function CallBadge({ status }: { status: CallStatus | 'not_called' }) {
  const m = CALL[status];
  return <span className={`badge ${m.cls}`}><span aria-hidden>{m.icon}</span>{m.label}</span>;
}

/** 대기열·목록에서 한 어르신을 대표하는 배지: 미응답·거절·통화 전이면 연락 상태, 아니면 단계 */
export function RowBadge({ row }: { row: ResidentRow }) {
  const s = row.today.status;
  if (s === 'missed' || s === 'declined' || s === 'ringing' || s === 'in_progress' || !row.assessment) return <CallBadge status={s} />;
  return <GradeBadge grade={row.assessment.grade} label={row.assessment.grade_label} />;
}

export function Empty({ icon = '◌', title, reason, action }: { icon?: string; title: string; reason?: string; action?: ReactNode }) {
  return (
    <div className="empty" role="status">
      <span className="ic" aria-hidden>{icon}</span>
      <b>{title}</b>
      {reason && <span>{reason}</span>}
      {action}
    </div>
  );
}

export function Loading({ rows = 3 }: { rows?: number }) {
  return (
    <div className="queue" aria-busy="true" aria-label="불러오는 중이에요">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton" />)}
    </div>
  );
}

export function Kpi({ label, icon, value, unit, foot, alert, on, onClick }: { label: string; icon?: string; value: number | string; unit: string; foot: string; alert?: boolean; on?: boolean; onClick?: () => void }) {
  const zero = value === 0;
  return (
    <button type="button" className={`kpi${alert ? ' u' : ''}${on ? ' on' : ''}${zero ? ' zero' : ''}`} aria-pressed={on} onClick={onClick}>
      <small>{label}{on ? <span className="kpi-on">✓ 필터 켜짐</span> : icon && <span aria-hidden>{icon}</span>}</small>
      <strong>{value}<em>{unit}</em></strong>
      <span>{foot}</span>
    </button>
  );
}

const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];
export const circled = (i: number) => CIRCLED[i] ?? `${i + 1}.`;
