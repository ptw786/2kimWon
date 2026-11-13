import {BrowserRouter,Link,Route,Routes,useParams,useLocation} from 'react-router-dom'
import Sidebar from './components/Sidebar'
import DashboardPage from './pages/DashboardPage'
import RecordsPage from './pages/RecordsPage'
import CallPage from './pages/CallPage'
function CallRoute(){const {elderId}=useParams();const {search}=useLocation();if(new URLSearchParams(search).has('queue'))return <main className="route-message"><h1>전화 예약 기능이 종료되었습니다</h1><p>일반 안부전화 체험을 새로 열어 주세요.</p><Link to={`/call/${elderId}`}>일반 안부전화 열기</Link></main>;return <CallPage key={elderId} elderId={elderId}/>}
export default function App(){
 return <BrowserRouter><Routes>
  <Route element={<Sidebar/>}><Route index element={<DashboardPage/>}/><Route path="records" element={<RecordsPage/>}/></Route>
  <Route path="call/:elderId" element={<CallRoute/>}/>
  <Route path="*" element={<main className="route-message"><h1>페이지를 찾을 수 없습니다</h1><Link to="/">대시보드로 이동</Link></main>}/>
 </Routes></BrowserRouter>
}
