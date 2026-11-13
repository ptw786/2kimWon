// 상태·단계·항목의 한글 라벨과 아이콘은 이 파일 하나에서만 정한다.
// 규칙: 색만으로 구분하지 않는다(항상 아이콘 + 글자). 빨강(b-u)은 '즉시 확인'에만 쓴다.
// 단계 라벨은 서버의 grade_label을 먼저 쓰고, 없을 때만 아래 값을 쓴다(계약 v2.1).
import type { AiRun, CallStatus, Grade, ItemStatus, NeedType, Topic, Turn } from './types';

export type Meta = { label: string; icon: string; cls: string };

export const TOPICS: Topic[] = ['body', 'meal', 'sleep', 'med', 'mood'];

export const TOPIC_LABEL: Record<Topic, string> = { body: '몸 상태', meal: '식사', sleep: '수면', med: '복약', mood: '기분' };
export const TOPIC_SHORT: Record<Topic, string> = { body: '몸', meal: '식사', sleep: '수면', med: '복약', mood: '기분' };

export const GRADE: Record<Grade, Meta> = {
  // 강조 위계: 즉시(빨강 채움) > 우선(주황 채움+테두리) > 추가(옅은 테두리) > 특이 표현 없음(채움 없이 조용히)
  urgent: { label: '즉시 확인', icon: '⚠', cls: 'g-u' },
  today: { label: '우선 확인', icon: '●', cls: 'g-t' },
  watch: { label: '추가 확인', icon: '◐', cls: 'g-w' },
  ok: { label: '특이 표현 없음', icon: '✓', cls: 'g-o' },
};
export const GRADE_ORDER: Grade[] = ['urgent', 'today', 'watch', 'ok'];

/** 어려움 유형(needs): 점수와 별개라 상태색(빨강·주황)을 쓰지 않고 버터색 칩 하나로 보인다. */
export const NEED: Record<NeedType, { label: string; icon: string }> = {
  meal_difficulty: { label: '식사 어려움', icon: '♨' },
  sleep_problem: { label: '수면 문제', icon: '☾' },
  help_request: { label: '도움 요청', icon: '⚑' },
  loneliness: { label: '외로움', icon: '♡' },
};

export const ITEM: Record<ItemStatus, Meta> = {
  good: { label: '양호', icon: '✓', cls: 'b-o' },
  caution: { label: '주의', icon: '◐', cls: 'b-w' },
  risk: { label: '위험', icon: '▲', cls: 'b-t' },
  unknown: { label: '미확인', icon: '?', cls: 'b-m' },
};

/** 7일 표 칸: 색 + 기호를 같이 쓴다. */
export const WEEK_CELL: Record<ItemStatus | 'none', { cls: string; mark: string; label: string }> = {
  good: { cls: 'cg', mark: '✓', label: '양호' },
  caution: { cls: 'cy', mark: '◐', label: '주의' },
  risk: { cls: 'cr', mark: '▲', label: '위험' },
  unknown: { cls: 'cu', mark: '?', label: '미확인' },
  none: { cls: 'cn', mark: '', label: '통화 없음·미응답' },
};

export const CALL: Record<CallStatus | 'not_called', Meta> = {
  ringing: { label: '벨 울리는 중', icon: '♪', cls: 'b-live' },
  in_progress: { label: '통화 중', icon: '●', cls: 'b-live' },
  completed: { label: '통화 완료', icon: '✓', cls: 'b-o' },
  interrupted: { label: '통화 중단', icon: '◑', cls: 'b-w' },
  missed: { label: '미응답', icon: '○', cls: 'b-m' },
  declined: { label: '거절', icon: '✕', cls: 'b-m' },
  not_called: { label: '통화 전', icon: '◌', cls: 'b-m' },
};

export const isLive = (s: CallStatus | 'not_called') => s === 'ringing' || s === 'in_progress';

export const AI_STEP: Record<AiRun['step'], string> = { extract: '추출', empathy: '공감 응답', summary: '요약' };

export const SOURCE: Record<NonNullable<Turn['source']>, string> = { stt: '음성', text: '글자', option: '버튼', silence: '무응답' };

export const ORIGIN_TAG = { llm: { label: 'AI 판정', cls: 't-ai' }, rule: { label: '규칙 판정', cls: 't-rule' } } as const;

/** 대기열 카드에 한 줄로 붙이는 연락 상태 설명 */
export function contactLine(status: CallStatus | 'not_called', callTime: string): string | null {
  switch (status) {
    case 'missed':
      return '오늘 전화를 받지 않으셨어요';
    case 'declined':
      return '오늘 전화를 거절하셨어요';
    case 'not_called':
      return `${callTime}에 전화할 예정이에요`;
    case 'ringing':
      return '지금 벨이 울리고 있어요';
    case 'in_progress':
      return '지금 통화 중이에요';
    case 'interrupted':
      return '통화가 중간에 끊겼어요';
    default:
      return null;
  }
}
