import type { ElderApi } from './types.ts'
import { mockApi } from '../mock/mockApi.ts'
import { ApiError } from './errors.ts'

export { ApiError }

/** 화면에 보여 줄 쉬운 문장. 서버가 준 한국어 detail이 있으면 그대로 쓴다. */
export function friendly(error: unknown): string {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500 && error.message) return error.message
  return '연결이 잠시 끊겼어요. 잠시 뒤 다시 눌러 주세요.'
}

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, '')
  }
  if (!response.ok) {
    let detail = ''
    try { const data = await response.json(); if (typeof data?.detail === 'string') detail = data.detail } catch { /* not json */ }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

const realApi: ElderApi = {
  residents: () => request('GET', '/elder/residents'),
  byCode: (code) => request('GET', `/elder/by-code/${encodeURIComponent(code)}`),
  home: (id) => request('GET', `/elder/${id}/home`),
  records: (id) => request('GET', `/elder/${id}/records`),
  incoming: (id) => request('GET', `/elder/${id}/incoming`),
  answer: (callId) => request('POST', `/elder/calls/${callId}/answer`),
  decline: (callId) => request('POST', `/elder/calls/${callId}/decline`),
  turn: (callId, body) => request('POST', `/elder/calls/${callId}/turn`, body),
  hangup: (callId) => request('POST', `/elder/calls/${callId}/hangup`),
  call: (callId) => request('GET', `/elder/calls/${callId}`),
  ringMe: async (id) => { await request('POST', `/staff/residents/${id}/call`) },
}

export const isMock = import.meta.env.VITE_MOCK === '1'
export const api: ElderApi = isMock ? mockApi : realApi

/** crypto.randomUUID는 HTTPS에서만 있다. LAN의 http 주소에서도 쓸 수 있게 직접 만든다. */
export function newTurnId(): string {
  if (typeof crypto.randomUUID === 'function' && window.isSecureContext) return crypto.randomUUID()
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}
