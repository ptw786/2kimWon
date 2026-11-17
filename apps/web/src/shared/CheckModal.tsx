import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, errMsg } from './api';
import type { StaffCheck } from './types';

/** 생활지원사 확인 기록 남기기 → POST /staff/calls/{id}/check */
export function CheckModal({ callId, name, onClose, onSaved }: { callId: number; name: string; onClose: () => void; onSaved: (c: StaffCheck) => void }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      onSaved(await api.post<StaffCheck>(`/staff/calls/${callId}/check`, { note: note.trim() }));
    } catch (err) {
      setError(errMsg(err));
      setBusy(false);
    }
  }

  return (
    <div className="modal-bg" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="check-title">
        <h3 id="check-title">확인 기록 남기기</h3>
        <div className="subtle">{name} 어르신 · 통화 #{callId}</div>
        <form onSubmit={submit}>
          <label className="field">
            무엇을 확인하셨나요?
            <textarea ref={ref} value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} placeholder="예: 전화로 다시 여쭤 보니 죽을 조금 드셨대요. 내일 방문 예정." />
            <span className="hint">{note.length} / 300자 · 비워 두면 '확인함'만 남겨요</span>
          </label>
          {error && <p className="err" role="alert">{error}</p>}
          <div className="acts2">
            <button type="button" className="btn o" onClick={onClose}>닫기</button>
            <button type="submit" className="btn p" disabled={busy}>{busy ? '저장하는 중…' : '기록 남기기'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
