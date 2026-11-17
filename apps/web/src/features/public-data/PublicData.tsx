import { useState } from 'react';
import { api } from '../../shared/api';
import { Empty, Loading } from '../../shared/ui';
import { usePoll } from '../../shared/usePoll';
import type { PublicDataOverview } from '../../shared/types';

export function PublicDataPage() {
  const data = usePoll(() => api.get<PublicDataOverview>('/staff/public-data'), null);
  const [level, setLevel] = useState('province');
  const [search, setSearch] = useState('');
  if (!data.data) return <div className="page">{data.error
    ? <Empty title="공공데이터를 불러오지 못했어요" reason={data.error} action={<button className="btn o" onClick={() => void data.refresh()}>다시 불러오기</button>} />
    : <Loading rows={4} />}</div>;
  const { catalog, statistics } = data.data;
  const rows = statistics.regions.filter((r) => r.aggregation_level === level && r.normalized_region.includes(search))
    .sort((a, b) => b.ratio_percent - a.ratio_percent);
  const national = statistics.regions.find((r) => r.aggregation_level === 'national');
  return <div className="page">
    <div className="ph"><div><div className="eyebrow">근거 · 공공데이터</div><h1>지역 규모와 지원사업 자료</h1>
      <p>지역 비교를 위한 통계예요. 개인의 위험 점수나 지원 자격을 결정하지 않아요.</p></div></div>
    <section className="panel pd-overview">
      <h2>복지사업 검토 현황</h2>
      {catalog.warning && <p role="alert" className="err">{catalog.warning}</p>}
      <p>원문 검토 후보 {catalog.reviewed}건 · 검토 대기 {catalog.pending}건 · 제외 {catalog.excluded}건 · 목록에서 확인되지 않음 {catalog.unavailable}건</p>
      <p className="subtle">전체 {catalog.total}건 중 검토 기록과 내용이 일치하는 사업만 안내해요. 신규·내용 변경 사업은 재검토 전까지 추천하지 않아요. 원문 검토는 기관의 자격 심사나 선정 확정이 아니에요.</p>
    </section>
    <section className="panel pd-overview">
      <h2>{statistics.year}년 독거노인가구 통계</h2>
      {national && <p>전국 65세 이상 1인 가구 <b>{national.elderly_single_households.toLocaleString()}가구</b> · 전체 일반가구 {national.all_households.toLocaleString()}가구 · {national.ratio_percent}%</p>}
      <p>가구 수는 사람 수와 달라요. 전국·시도·시군구는 서로 겹치므로 합산하지 않아요.</p>
      <div className="pd-controls">
        <label>비교 단위 <select value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="province">시도</option><option value="district">시군구</option><option value="subdistrict">하위 지역</option>
        </select></label>
        <label>지역 찾기 <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="예: 서울, 고흥군" /></label>
      </div>
      <p className="subtle">같은 단위 안에서 비율이 높은 순으로 보여 드려요. {rows.length}개 지역</p>
      <div className="pd-regions">
        {rows.map((r) => <article key={r.region} className="pd-region">
          <h3>{r.normalized_region}</h3>
          <p><b>{r.ratio_percent}%</b> · 65세 이상 1인 가구 {r.elderly_single_households.toLocaleString()}가구</p>
          <p className="subtle">전체 일반가구 {r.all_households.toLocaleString()}가구</p>
          {r.region !== r.normalized_region && <p className="subtle">원문 지역: {r.region}</p>}
        </article>)}
      </div>
      {!rows.length && <Empty title="해당 지역이 없어요" reason="비교 단위나 지역 이름을 바꿔 주세요." />}
      <p className="subtle">출처: {statistics.source} · 기준연도 {statistics.year}<br />제공 파일: {statistics.source_file}<br />변환 자료를 사용했어요. 원본 Excel 대조와 최신 행정구역 기준은 별도 확인이 필요해요.</p>
    </section>
  </div>;
}
