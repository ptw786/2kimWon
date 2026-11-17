// 어르신 앱 주소. QR과 소개 페이지 iframe이 이 주소를 쓴다.
// 폰에서 찍으려면 VITE_APP_PUBLIC_URL에 같은 와이파이의 PC 주소(예: http://192.168.0.12:5181)를 넣는다.
export const APP_URL: string = (import.meta.env.VITE_APP_PUBLIC_URL as string | undefined)?.replace(/\/$/, '') || `${location.protocol}//${location.hostname}:5181`;

export const elderUrl = (code: string) => `${APP_URL}/r/${encodeURIComponent(code)}`;

/** localhost 주소는 폰 카메라로 찍어도 열리지 않는다 */
export const appUrlIsLocal = /\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(APP_URL);

export const IS_MOCK = import.meta.env.VITE_MOCK === '1';
