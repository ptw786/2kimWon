import {NavLink,Outlet,useLocation} from 'react-router-dom'
import {CalendarClock,ClipboardList,LayoutDashboard,ShieldCheck} from 'lucide-react'
import {Brand} from './Common'
export default function Sidebar(){
 const {pathname}=useLocation()
 return <div className="app"><aside className="sidebar"><Brand/><div className="workspace">돌봄 서비스 관리</div>
  <nav className="nav" aria-label="관리 메뉴"><NavLink to="/" end className={({isActive})=>isActive?'on':''}><LayoutDashboard size={19}/> 대시보드</NavLink><NavLink to="/records" className={({isActive})=>isActive?'on':''}><ClipboardList size={19}/> 통화 기록</NavLink><NavLink to="/schedules" className={({isActive})=>isActive?'on':''}><CalendarClock size={19}/> 안부전화 예약</NavLink></nav>
  <div className="sidebar-bottom"><ShieldCheck size={17}/><span>무료 · 로컬 개발 버전<br/><small>실제 전화망 연결 없음</small></span></div>
 </aside><div className="main"><header className="header"><div className="mobilebrand"><Brand/></div><div className="crumb">돌봄 관리 <span> / </span>{pathname==='/records'?'통화 기록':pathname==='/schedules'?'안부전화 예약':'대시보드'}</div><div className="header-right"><span className="online-dot"/>로컬 서버 연결형</div></header><main className="content"><Outlet/></main></div>
 <nav className="mobile-nav" aria-label="모바일 관리 메뉴"><NavLink to="/" end><LayoutDashboard size={19}/>현황</NavLink><NavLink to="/records"><ClipboardList size={19}/>기록</NavLink><NavLink to="/schedules"><CalendarClock size={19}/>예약</NavLink></nav></div>
}
