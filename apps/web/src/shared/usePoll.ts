import { useCallback, useEffect, useRef, useState } from 'react';
import { errMsg } from './api';

export type Poll<T> = { data: T | null; error: string | null; loading: boolean; refresh: () => Promise<void> };

/** load()를 바로 한 번, 그 뒤 ms마다 다시 부른다(ms가 null이면 한 번만). 키가 바뀌면 처음부터. */
export function usePoll<T>(load: (() => Promise<T>) | null, ms: number | null, key: unknown = null): Poll<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;
  const seq = useRef(0);

  const refresh = useCallback(async () => {
    const fn = loadRef.current;
    if (!fn) return;
    const my = ++seq.current;
    try {
      const d = await fn();
      if (my !== seq.current) return;
      setData(d);
      setError(null);
    } catch (e) {
      if (my !== seq.current) return;
      setError(errMsg(e));
    } finally {
      if (my === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setData(null);
    setError(null);
    setLoading(!!loadRef.current);
    if (!loadRef.current) return;
    void refresh();
    const t = ms == null ? undefined : window.setInterval(() => void refresh(), ms);
    return () => {
      window.clearInterval(t);
      seq.current++;
    };
  }, [key, ms, refresh]);

  return { data, error, loading, refresh };
}
