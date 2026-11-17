import { useEffect, useState } from 'react';
import { APP_URL } from './config';

/** 어르신 앱(5181)이 켜져 있는지: no-cors 요청이 네트워크 오류 없이 돌아오면 켜진 것 */
export function useAppReachable() {
  const [state, setState] = useState<'checking' | 'up' | 'down'>('checking');
  useEffect(() => {
    let alive = true;
    const ctl = new AbortController();
    const t = window.setTimeout(() => ctl.abort(), 2500);
    fetch(`${APP_URL}/`, { mode: 'no-cors', signal: ctl.signal, cache: 'no-store' })
      .then(() => alive && setState('up'))
      .catch(() => alive && setState('down'))
      .finally(() => window.clearTimeout(t));
    return () => {
      alive = false;
      window.clearTimeout(t);
      ctl.abort();
    };
  }, []);
  return state;
}
