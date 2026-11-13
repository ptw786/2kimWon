import { Link, Route, Routes } from 'react-router-dom';
import { StaffLayout } from '../shared/StaffLayout';
import { Empty } from '../shared/ui';
import { CallDetailPage } from '../features/call-detail';
import { CallsPage } from '../features/calls';
import { DashboardPage } from '../features/queue';
import { LandingPage } from '../features/landing';
import { LivePage } from '../features/live';
import { PrinciplesPage } from '../features/rules';
import { ResidentsPage } from '../features/residents';
import { RulesPage } from '../features/rules';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/staff" element={<StaffLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="live" element={<LivePage />} />
        <Route path="residents" element={<ResidentsPage />} />
        <Route path="calls" element={<CallsPage />} />
        <Route path="calls/:id" element={<CallDetailPage />} />
        <Route path="rules" element={<RulesPage />} />
        <Route path="principles" element={<PrinciplesPage />} />
        <Route path="*" element={<div className="page"><Empty title="없는 화면이에요" reason="주소를 다시 확인해 주세요." action={<Link to="/staff" className="btn p">오늘 확인 순서로</Link>} /></div>} />
      </Route>
      <Route path="*" element={<div className="page"><Empty title="없는 화면이에요" reason="주소를 다시 확인해 주세요." action={<Link to="/" className="btn p">처음으로</Link>} /></div>} />
    </Routes>
  );
}
