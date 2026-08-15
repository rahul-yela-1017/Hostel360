import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  BookOpenText, Building2, CalendarCheck2, ClipboardList, Contact, CookingPot,
  FileArchive, LayoutDashboard, LogOut, Menu, Settings, ShieldCheck, Users, X
} from 'lucide-react'
import { useAuth } from '../AuthContext'
import { Logo } from './UI'

const nav = {
  ADMIN: [
    ['Overview', '/admin/dashboard', LayoutDashboard], ['Students', '/admin/students', Users],
    ['Rooms & beds', '/admin/rooms', Building2], ['Attendance', '/admin/attendance', CalendarCheck2],
    ['Wardens', '/admin/wardens', ShieldCheck], ['Cooks', '/admin/cooks', CookingPot],
    ['Reports', '/admin/reports', FileArchive], ['Settings', '/admin/settings', Settings],
  ],
  WARDEN: [
    ['Overview', '/warden/dashboard', LayoutDashboard], ['Students', '/warden/students', Users],
    ['Rooms & beds', '/warden/rooms', Building2], ['Attendance', '/warden/attendance', CalendarCheck2],
    ['Mess menu', '/warden/menu', CookingPot], ['Notices', '/warden/notices', BookOpenText],
    ['Reports', '/warden/reports', FileArchive],
  ],
  COOK: [['Today’s menu', '/cook/dashboard', CookingPot], ['Previous menus', '/cook/menu', ClipboardList]],
  STUDENT: [
    ['Home', '/student/dashboard', LayoutDashboard], ['My attendance', '/student/attendance', CalendarCheck2],
    ['Today’s menu', '/student/menu', CookingPot], ['Hostel timings', '/student/timings', ClipboardList],
    ['Wardens', '/student/wardens', Contact], ['Notices', '/student/notices', BookOpenText],
  ]
}

export default function Shell() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const location = useLocation()
  useEffect(() => setOpen(false), [location.pathname])
  const initials = user?.name?.split(' ').map(x => x[0]).slice(0, 2).join('')
  const now = useMemo(() => new Date(), [location.pathname])
  const dateLabel = now.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }).toUpperCase()
  const hour = now.getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  return <div className="app-shell">
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-top"><Logo light/><button className="icon-btn sidebar-close" onClick={() => setOpen(false)}><X/></button></div>
      <div className="hostel-pill"><div className="hostel-emblem">M</div><div><strong>Malla Reddy Boys Hostel</strong><span>Main campus</span></div></div>
      <nav>
        <small>WORKSPACE</small>
        {nav[user.role].map(([label, to, Icon]) => <NavLink key={to} to={to} className={({isActive}) => isActive ? 'active' : ''}>
          <Icon size={19}/><span>{label}</span>
        </NavLink>)}
      </nav>
      <div className="sidebar-help"><div className="help-icon">i</div><strong>Authorised hostel system</strong><span>Contact the system administrator if you need access assistance.</span></div>
      <button className="logout" onClick={logout}><LogOut size={18}/> Sign out</button>
    </aside>
    {open && <div className="sidebar-backdrop" onClick={() => setOpen(false)}/>} 
    <main className="main-area">
      <header className="topbar">
        <button className="icon-btn mobile-menu" onClick={() => setOpen(true)}><Menu/></button>
        <div className="today"><span>{dateLabel}</span><strong>{greeting}, {user.name.split(' ')[0]}.</strong></div>
        <div className="top-actions">
          <div className="profile-chip"><div className="avatar">{initials}</div><div><strong>{user.name}</strong><span>{user.role.charAt(0)+user.role.slice(1).toLowerCase()}</span></div></div>
        </div>
      </header>
      <div className="page-wrap"><Outlet/></div>
      <div className="mobile-nav">{nav[user.role].slice(0, 5).map(([label,to,Icon]) => <NavLink key={to} to={to}><Icon/><span>{label.split(' ')[0]}</span></NavLink>)}</div>
    </main>
  </div>
}
