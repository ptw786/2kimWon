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

// ── 생활지원사 로그인 토큰 (서버 /staff/login 이 PIN을 받고 준다) ─────────
const TOKEN_KEY = 'ansimon-staff-token';
let token: string | null = (() => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
})();
let needLogin = false;
const authListeners = new Set<() => void>();
function setNeedLogin(v: boolean) {
  if (needLogin === v) return;
  needLogin = v;
  authListeners.forEach((l) => l());
}
export const useNeedLogin = () =>
  useSyncExternalStore(
    (l) => (authListeners.add(l), () => authListeners.delete(l)),
    () => needLogin,
  );
export function setToken(t: string | null) {
  token = t;
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* 저장소를 못 쓰면 이 탭에서만 로그인 유지 */
  }
  setNeedLogin(!t);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  if (IS_MOCK) {
    const { mockFetch } = await import('../mock/server');
    return mockFetch<T>(method, path, body);
  }
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(token && path.startsWith('/staff/') ? { Authorization: `Bearer ${token}` } : {}),
      },
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
    if (res.status === 401 && path.startsWith('/staff/') && path !== '/staff/login') setToken(null);
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
