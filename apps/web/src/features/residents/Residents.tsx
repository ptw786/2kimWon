// 어르신 목록 + 추가·수정 (POST/PATCH /staff/residents)
import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useStaff } from '../../shared/StaffLayout';
import { Empty, Loading, RowBadge } from '../../shared/ui';
import { api, errMsg } from '../../shared/api';
import type { Resident, ResidentInput, ResidentRow } from '../../shared/types';

// 복지서비스 검색에 쓰는 시도+시군구. 자유 입력이고, 자주 쓰는 값만 제안한다.
const REGION_EXAMPLES = ['대전광역시 중구', '대전광역시 동구', '대전광역시 서구', '대전광역시 유성구', '대전광역시 대덕구', '서울특별시 서대문구', '서울특별시 종로구'];
const dong = (n: string) => n.split(' ').pop() ?? n;

export function ResidentsPage() {
  const { dash, toast } = useStaff();
  const [params, setParams] = useSearchParams();
  const [editing, setEditing] = useState<ResidentRow | 'new' | null>(null);
  useEffect(() => {
    if (params.get('new') === '1') setEditing('new');
  }, [params]);
  const close = () => {
    setEditing(null);
    if (params.has('new')) setParams({}, { replace: true });
  };
  const rows = [...(dash.data?.residents ?? [])].sort((a, b) => a.code.localeCompare(b.code));

  return (
    <div className="page">
      <div className="ph">
        <div>
          <div className="eyebrow">어르신 {rows.length}분</div>
          <h1>어르신 목록</h1>
          <p>매일 정해진 시간에 안부전화를 드려요. 코드는 어르신 앱 QR에 들어가요.</p>
        </div>
        <div className="act"><button type="button" className="btn p" onClick={() => setEditing('new')}>＋ 어르신 추가</button></div>
      </div>

      {!dash.data && dash.loading && <Loading rows={4} />}
      {!dash.data && dash.error && <Empty icon="⚠" title="목록을 불러오지 못했어요" reason={dash.error} action={<button type="button" className="btn o" onClick={() => void dash.refresh()}>다시 불러오기</button>} />}
      {dash.data && rows.length === 0 && <Empty icon="♡" title="아직 등록된 어르신이 없어요" reason="오른쪽 위 ‘어르신 추가’로 첫 분을 등록해 주세요." action={<button type="button" className="btn p" onClick={() => setEditing('new')}>어르신 추가</button>} />}

      {rows.length > 0 && (
        <div className="rows res" role="table" aria-label="어르신 목록">
          <div className="row head" role="row">
            <span role="columnheader">코드</span><span role="columnheader">이름</span><span role="columnheader">나이</span><span role="columnheader">사는 곳</span><span role="columnheader">전화 시간</span><span role="columnheader">오늘</span><span role="columnheader"><span className="sr">수정</span></span>
          </div>
          {rows.map((r) => (
            <div className="row" role="row" key={r.id}>
              <span role="cell" className="mono">{r.code}</span>
              <span role="cell"><b>{r.name}</b>{r.is_virtual && <span className="subtle"> · 가상</span>}</span>
              <span role="cell"><span className="lbl">나이</span>{r.age}세</span>
              <span role="cell"><span className="lbl">사는 곳</span>{r.region ? <>{r.region} <span className="subtle">{dong(r.neighborhood)}</span></> : r.neighborhood}</span>
              <span role="cell"><span className="lbl">전화</span>{r.call_time}</span>
              <span role="cell" className="wide" style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', minWidth: 0 }}>
                <RowBadge row={r} />
                {r.today.call_id && <Link to={`/staff/calls/${r.today.call_id}`} className="subtle" style={{ textDecoration: 'underline' }}>통화 보기</Link>}
                {r.memo && <span className="ell" title={r.memo}>{r.memo}</span>}
              </span>
              <span role="cell"><button type="button" className="btn o" onClick={() => setEditing(r)}>수정</button></span>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <ResidentForm
          initial={editing === 'new' ? null : editing}
          onClose={close}
          onSaved={(r, isNew) => {
            close();
            toast(isNew ? `${r.name} 어르신을 추가했어요 (${r.code}).` : `${r.name} 어르신 정보를 고쳤어요.`);
            void dash.refresh();
          }}
        />
      )}
    </div>
  );
}

function ResidentForm({ initial, onClose, onSaved }: { initial: Resident | null; onClose: () => void; onSaved: (r: Resident, isNew: boolean) => void }) {
  const [f, setF] = useState({
    name: initial?.name ?? '',
    age: initial ? String(initial.age) : '',
    region: initial?.region ?? '',
    neighborhood: initial?.neighborhood ?? '',
    call_time: initial?.call_time ?? '10:00',
    memo: initial?.memo ?? '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const age = Number(f.age);
    if (!f.name.trim()) return setError('이름을 적어 주세요.');
    if (!Number.isInteger(age) || age < 50 || age > 120) return setError('나이는 50~120 사이 숫자로 적어 주세요.');
    const region = f.region.trim().replace(/\s+/g, ' ');
    if (region.split(' ').length < 2) return setError('지역을 시도와 시군구까지 적어 주세요. 예: 대전광역시 중구');
    if (!f.neighborhood.trim()) return setError('사는 동네(동)를 적어 주세요.');
    const body: ResidentInput = { name: f.name.trim(), age, region, neighborhood: f.neighborhood.trim(), call_time: f.call_time, memo: f.memo.trim() || null };
    setBusy(true);
    setError('');
    try {
      const r = initial ? await api.patch<Resident>(`/staff/residents/${initial.id}`, body) : await api.post<Resident>('/staff/residents', body);
      onSaved(r, !initial);
    } catch (err) {
      setError(errMsg(err));
      setBusy(false);
    }
  }

  return (
    <div className="modal-bg" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="res-title">
        <h3 id="res-title">{initial ? `${initial.name} 어르신 정보 고치기` : '어르신 추가'}</h3>
        <div className="subtle">{initial ? `코드 ${initial.code}` : '코드는 저장할 때 자동으로 붙어요.'}</div>
        <form onSubmit={submit}>
          <div className="grid2">
            <label className="field">이름<input value={f.name} onChange={set('name')} autoFocus required maxLength={20} /></label>
            <label className="field">나이<input value={f.age} onChange={set('age')} inputMode="numeric" required /></label>
          </div>
          <label className="field">
            지역(시도 + 시군구) <span className="hint">복지서비스를 찾을 때 써요</span>
            <input value={f.region} onChange={set('region')} list="region-examples" placeholder="예: 대전광역시 중구, 서울특별시 서대문구" required maxLength={40} />
            <datalist id="region-examples">{REGION_EXAMPLES.map((x) => <option key={x} value={x} />)}</datalist>
          </label>
          <div className="grid2">
            <label className="field">사는 곳(구·동)<input value={f.neighborhood} onChange={set('neighborhood')} placeholder="예: 중구 은행동" required maxLength={30} /></label>
            <label className="field">매일 전화 시간<input type="time" value={f.call_time} onChange={set('call_time')} required /></label>
          </div>
          <label className="field">메모 <span className="hint">(선택 · 생활지원사만 봐요)</span><textarea value={f.memo} onChange={set('memo')} maxLength={200} placeholder="예: 귀가 어두우셔서 천천히" /></label>
          <p className="subtle" style={{ margin: 0 }}>나이는 점수에 넣지 않아요. 어르신을 구분하는 데만 써요.</p>
          {error && <p className="err" role="alert">{error}</p>}
          <div className="acts2">
            <button type="button" className="btn o" onClick={onClose}>닫기</button>
            <button type="submit" className="btn p" disabled={busy}>{busy ? '저장하는 중…' : initial ? '고친 내용 저장' : '추가하기'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
