import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import Shell from './components/Shell'
import { Loading } from './components/UI'

const Login=lazy(()=>import('./pages/Login'))
const Dashboard=lazy(()=>import('./pages/Dashboard'))
const Students=lazy(()=>import('./pages/Students'))
const Rooms=lazy(()=>import('./pages/Rooms'))
const Attendance=lazy(()=>import('./pages/Attendance'))
const MenuEditor=lazy(()=>import('./pages/MenuEditor'))
const MenuView=lazy(()=>import('./pages/MenuEditor').then(m=>({default:m.MenuView})))
const Reports=lazy(()=>import('./pages/Reports'))
const Staff=lazy(()=>import('./pages/Staff'))
const Settings=lazy(()=>import('./pages/Settings'))
const Notices=lazy(()=>import('./pages/InfoPages').then(m=>({default:m.Notices})))
const Timings=lazy(()=>import('./pages/InfoPages').then(m=>({default:m.Timings})))
const Wardens=lazy(()=>import('./pages/InfoPages').then(m=>({default:m.Wardens})))
const ChangePassword=lazy(()=>import('./pages/ChangePassword'))

const home={ADMIN:'/admin/dashboard',WARDEN:'/warden/dashboard',COOK:'/cook/dashboard',STUDENT:'/student/dashboard'}
function Protected({roles}){const{user}=useAuth();const location=useLocation();if(!user)return <Navigate to="/login" state={{from:location}} replace/>;if(user.must_change_password)return <Navigate to="/change-password" replace/>;if(!roles.includes(user.role))return <Navigate to={home[user.role]} replace/>;return <Shell/>}
export default function App(){const{user}=useAuth();return <Suspense fallback={<Loading label="Opening your workspace…"/>}><Routes><Route path="/" element={<Navigate to={user?(user.must_change_password?'/change-password':home[user.role]):'/login'} replace/>}/><Route path="/login" element={<Login/>}/><Route path="/change-password" element={<ChangePassword/>}/>
<Route element={<Protected roles={['ADMIN']}/>}><Route path="/admin/dashboard" element={<Dashboard/>}/><Route path="/admin/wardens" element={<Staff type="wardens"/>}/><Route path="/admin/cooks" element={<Staff type="cooks"/>}/><Route path="/admin/students" element={<Students/>}/><Route path="/admin/rooms" element={<Rooms/>}/><Route path="/admin/attendance" element={<Attendance/>}/><Route path="/admin/reports" element={<Reports/>}/><Route path="/admin/settings" element={<Settings/>}/></Route>
<Route element={<Protected roles={['WARDEN']}/>}><Route path="/warden/dashboard" element={<Dashboard/>}/><Route path="/warden/students" element={<Students/>}/><Route path="/warden/students/:id" element={<Students/>}/><Route path="/warden/rooms" element={<Rooms/>}/><Route path="/warden/attendance" element={<Attendance/>}/><Route path="/warden/menu" element={<MenuEditor/>}/><Route path="/warden/notices" element={<Notices/>}/><Route path="/warden/reports" element={<Reports/>}/></Route>
<Route element={<Protected roles={['COOK']}/>}><Route path="/cook/dashboard" element={<Dashboard/>}/><Route path="/cook/menu" element={<MenuEditor cookMode/>}/></Route>
<Route element={<Protected roles={['STUDENT']}/>}><Route path="/student/dashboard" element={<Dashboard/>}/><Route path="/student/attendance" element={<Attendance/>}/><Route path="/student/menu" element={<MenuView/>}/><Route path="/student/timings" element={<Timings/>}/><Route path="/student/wardens" element={<Wardens/>}/><Route path="/student/notices" element={<Notices/>}/></Route>
<Route path="*" element={<Navigate to={user?home[user.role]:'/login'} replace/>}/></Routes></Suspense>}
