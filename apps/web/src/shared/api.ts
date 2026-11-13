// /api 호출. VITE_MOCK=1이면 src/mock의 가짜 서버가 같은 모양으로 답한다.
import { useSyncExternalStore } from 'react';
import { IS_MOCK } from './config';

export class ApiError extends Error {
  constructor(public status: number, message: string, public down = false) {
    super(message);
  }
}

// ── 서버 연결 상태(배너용) ─────────────────────────
let down = false;
const listeners = new Set<() => void>();
function setDown(v: boolean) {
  if (down === v) return;
  down = v;
  listeners.forEach((l) => l());
}
export const useApiDown = () =>
  useSyncExternalStore(
    (l) => (listeners.add(l), () => listeners.delete(l)),
    () => down,
  );

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (IS_MOCK) {
    const { mockFetch } = await import('../mock/server');
    return mockFetch<T>(method, path, body);
  }
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    setDown(true);
    throw new ApiError(0, '서버에 연결할 수 없어요.', true);
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    // Vite 프록시는 API가 꺼져 있으면 본문 없는 5xx를 돌려준다.
    const isDown = res.status >= 500 && typeof detail !== 'string';
    setDown(isDown);
    throw new ApiError(res.status, typeof detail === 'string' ? detail : isDown ? '서버에 연결할 수 없어요.' : `요청을 처리하지 못했어요 (${res.status})`, isDown);
  }
  setDown(false);
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
};

export const errMsg = (e: unknown) => (e instanceof Error ? e.message : '알 수 없는 오류가 났어요.');
