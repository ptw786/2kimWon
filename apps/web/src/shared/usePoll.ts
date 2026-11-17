import { useCallback, useEffect, useRef, useState } from 'react';
import { errMsg } from './api';

export type Poll<T> = { data: T | null; error: string | null; loading: boolean; refresh: () => Promise<void> };

/** load()를 바로 한 번, 그 뒤 ms마다 다시 부른다(ms가 null이면 한 번만). 키가 바뀌면 처음부터.
 *  서버가 ms보다 느려도 화면이 멈추지 않게: 앞 요청이 끝나기 전에는 주기 요청을 보내지 않고,
 *  늦게 도착한 응답도 더 최근 응답보다 앞선 요청이 아니면 그대로 쓴다(외부 리뷰 #10). 키가 바뀐 뒤의 응답만 버린다. */
export function usePoll<T>(load: (() => Promise<T>) | null, ms: number | null, key: unknown = null): Poll<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;
  const gen = useRef(0); // 키가 바뀔 때마다 +1
  const sent = useRef(0); // 보낸 요청 번호
  const applied = useRef(0); // 화면에 쓴 가장 최근 요청 번호
  const inFlight = useRef(0);

  const refresh = useCallback(async () => {
    const fn = loadRef.current;
    if (!fn) return;
    const g = gen.current;
    const my = ++sent.current;
    inFlight.current++;
    try {
      const d = await fn();
      if (g !== gen.current || my < applied.current) return;
      applied.current = my;
      setData(d);
      setError(null);
    } catch (e) {
      if (g !== gen.current || my < applied.current) return;
      applied.current = my;
      setError(errMsg(e));
    } finally {
      if (g === gen.current) {
        inFlight.current--;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    gen.current++;
    applied.current = sent.current;
    inFlight.current = 0;
    setData(null);
    setError(null);
    setLoading(!!loadRef.current);
    if (!loadRef.current) return;
    void refresh();
    const t = ms == null ? undefined : window.setInterval(() => {
      if (inFlight.current === 0) void refresh();
    }, ms);
    return () => {
      window.clearInterval(t);
      gen.current++;
    };
  }, [key, ms, refresh]);

  return { data, error, loading, refresh };
}
