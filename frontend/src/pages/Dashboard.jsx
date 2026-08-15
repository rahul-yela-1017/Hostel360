import { useEffect, useState } from 'react'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  ArrowRight, BedDouble, BellRing, Building2, CalendarCheck2, ChevronRight, Clock3,
  DoorOpen, MoonStar, ShieldAlert, Sparkles, SunMedium, Sunrise, Users
} from 'lucide-react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api'
import { useAuth } from '../AuthContext'
import { Badge, Card, Empty, ErrorState, Loading, PageTitle, Progress, StatCard } from '../components/UI'
import MenuEditor from './MenuEditor'

const fmt = n => new Intl.NumberFormat('en-IN').format(n ?? 0)
const mealIcons = { breakfast: Sunrise, lunch: SunMedium, snacks: Sparkles, dinner: MoonStar }
const todayLabel = () => new Date().toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'}).toUpperCase()

function OperationsDashboard({ role }) {
  const [summary, setSummary] = useState(null)
  const [attendance, setAttendance] = useState([])
  const [error, setError] = useState('')
  const load = () => { setError(''); Promise.all([api.get('/dashboard/summary'), api.get('/attendance/today?limit=7')])
    .then(([a,b]) => { setSummary(a.data); setAttendance(b.data) }).catch(e=>setError(errorMessage(e))) }
  useEffect(load, [])
  if (error) return <ErrorState message={error} retry={load}/>
  if (!summary) return <Loading/>
  const occupancy = [{name:'Occupied',value:summary.occupied_beds,color:'#13a888'},{name:'Vacant',value:summary.vacant_beds,color:'#dfe7ee'}]
  const admin = role === 'ADMIN'
  const root = admin ? '/admin' : '/warden'
  const safePercent = value => summary.total_students ? Math.round(value/summary.total_students*100) : 0
  return <>
    <PageTitle eyebrow={`${admin?'SYSTEM OVERVIEW':'HOSTEL OPERATIONS'} · ${todayLabel()}`} title={admin?'Malla Reddy Boys Hostel':'Hostel operations'}
      subtitle="Live information calculated from your real student, room and attendance records."
      actions={<Link className="btn primary" to={`${root}/students`}>Manage students <ArrowRight/></Link>}/>
    <div className="stats-grid">
      <StatCard label="Total students" value={fmt(summary.total_students)} hint="Active residents" icon={Users} tone="blue"/>
      <StatCard label="Occupied beds" value={fmt(summary.occupied_beds)} hint={`${summary.occupancy_percentage}% occupancy`} icon={BedDouble} tone="mint" delay={.04}/>
      <StatCard label="Present today" value={fmt(summary.present)} hint={`${summary.attendance_percentage}% attendance`} icon={CalendarCheck2} tone="violet" delay={.08}/>
      <StatCard label="Late entries" value={fmt(summary.late)} hint="After gate closing time" icon={ShieldAlert} tone="amber" delay={.12}/>
    </div>
    {summary.total_students===0 && <Card className="onboarding-card"><span><Users/></span><div><span className="card-eyebrow">READY FOR REAL DATA</span><h2>Add your first student</h2><p>The hostel starts clean with 431 empty rooms. Create students and assign vacant beds; dashboards and reports update automatically.</p></div><Link className="btn primary" to={`${root}/students`}>Add student <ArrowRight/></Link></Card>}
    <div className="dashboard-grid">
      <Card className="chart-card span-2">
        <div className="card-head"><div><span className="card-eyebrow">ATTENDANCE PULSE</span><h3>Last seven days</h3></div></div>
        <div className="chart-kpi"><strong>{summary.attendance_percentage}%</strong><span>today’s recorded attendance</span></div>
        <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={summary.trend} margin={{left:-20,right:8,top:10}}>
          <defs><linearGradient id="areaMint" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#12a989" stopOpacity=".25"/><stop offset="1" stopColor="#12a989" stopOpacity="0"/></linearGradient></defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8edf2"/><XAxis dataKey="date" axisLine={false} tickLine={false}/><YAxis domain={[0,100]} axisLine={false} tickLine={false}/>
          <Tooltip contentStyle={{border:'0',borderRadius:12,boxShadow:'0 10px 30px #132a4430'}}/><Area type="monotone" dataKey="attendance" stroke="#12a989" strokeWidth={3} fill="url(#areaMint)" dot={{fill:'#fff',stroke:'#12a989',strokeWidth:2,r:4}}/></AreaChart></ResponsiveContainer></div>
      </Card>
      <Card className="occupancy-card">
        <div className="card-head"><div><span className="card-eyebrow">CAPACITY</span><h3>Bed occupancy</h3></div><Link to={`${root}/rooms`}><ArrowRight/></Link></div>
        <div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={occupancy} dataKey="value" innerRadius={68} outerRadius={87} startAngle={90} endAngle={-270} paddingAngle={2}>{occupancy.map(x=><Cell key={x.name} fill={x.color}/>)}</Pie></PieChart></ResponsiveContainer><div><strong>{summary.occupancy_percentage}%</strong><span>occupied</span></div></div>
        <div className="occupancy-legend"><div><i className="mint-dot"/><span>Occupied</span><strong>{fmt(summary.occupied_beds)}</strong></div><div><i/><span>Available</span><strong>{fmt(summary.vacant_beds)}</strong></div></div>
      </Card>
      <Card className="span-2">
        <div className="card-head"><div><span className="card-eyebrow">ENTRY RECORDS</span><h3>Recent attendance</h3></div><Link to={`${root}/attendance`}>View register <ArrowRight/></Link></div>
        {attendance.length?<div className="mini-table"><div className="table-row table-label"><span>STUDENT</span><span>ROOM</span><span>TIME</span><span>STATUS</span></div>
          {attendance.map(a=><div className="table-row" key={a.id}><span className="person-cell"><i>{a.name.split(' ').map(x=>x[0]).slice(0,2)}</i><b>{a.name}<small>{a.roll_no}</small></b></span><span>Room {a.room}</span><span>{a.time}</span><span><Badge>{a.status}</Badge></span></div>)}
        </div>:<Empty title="No attendance recorded today" message="Verified entry records will appear here."/>}
      </Card>
      <Card className="quick-card">
        <div className="card-head"><div><span className="card-eyebrow">TODAY</span><h3>Attendance status</h3></div></div>
        <div className="status-stack"><div><i className="mint"><CalendarCheck2/></i><span><strong>{fmt(summary.present)}</strong> Present</span><b>{safePercent(summary.present)}%</b></div>
          <div><i className="red"><ShieldAlert/></i><span><strong>{fmt(summary.absent)}</strong> Absent</span><b>{safePercent(summary.absent)}%</b></div>
          <div><i className="gray"><Clock3/></i><span><strong>{fmt(summary.not_recorded)}</strong> Not recorded</span><b>{safePercent(summary.not_recorded)}%</b></div></div>
        <Link className="text-link" to={`${root}/attendance`}>Open attendance register <ArrowRight/></Link>
      </Card>
    </div>
  </>
}

function MealPreview({ menu }) {
  return <div className="meal-preview-grid">{['breakfast','lunch','snacks','dinner'].map((meal,i)=>{
    const Icon=mealIcons[meal]; return <div className={`meal-preview meal-${i}`} key={meal}><span><Icon/></span><div><small>{meal.toUpperCase()} · {menu[`${meal}_time`]}</small><strong>{menu[meal]}</strong></div></div>})}</div>
}

function StudentDashboard() {
  const { user } = useAuth()
  const [data,setData]=useState(null); const [error,setError]=useState('')
  const load=async()=>{try{const results=await Promise.allSettled([api.get('/student/profile'),api.get('/student/attendance'),api.get('/menu/today'),api.get('/notices'),api.get('/hostel/timings')]);
    const value=(i,fallback)=>results[i].status==='fulfilled'?results[i].value.data:fallback
    setData({profile:value(0,{}),attendance:value(1,{overall:0,present:0,absent:0,late:0,history:[]}),menu:value(2,null),notices:value(3,[]),timings:value(4,[])})
  }catch(e){setError(errorMessage(e))}}
  useEffect(()=>{load()},[])
  if(error)return <ErrorState message={error} retry={load}/>; if(!data)return <Loading/>
  const a=data.attendance, profile=data.profile, notice=data.notices[0]
  return <>
    <div className="student-welcome"><div><span>MALLA REDDY BOYS HOSTEL</span><h1>Welcome, {user.name.split(' ')[0]}.</h1><p>Your room, attendance and hostel information.</p></div><div className="room-ticket"><small>YOUR ROOM</small><strong>{user.room??'—'}</strong><span>{user.bed?`Bed ${user.bed}`:'Not assigned'}</span><DoorOpen/></div></div>
    <div className="student-grid">
      <Card className="student-attendance"><div className="card-head"><div><span className="card-eyebrow">MY ATTENDANCE</span><h3>{a.history.length?'Current attendance record':'No attendance records yet'}</h3></div><Link to="/student/attendance"><ChevronRight/></Link></div>
        <div className="attendance-score"><strong>{a.overall}<sup>%</sup></strong><div><span>Overall attendance</span><Progress value={a.overall}/><small>{a.present} present · {a.late} late · {a.absent} absent</small></div></div>
      </Card>
      {notice?<Card className="notice-highlight"><span className="notice-icon"><BellRing/></span><div><small>{notice.priority} NOTICE</small><h3>{notice.title}</h3><p>{notice.message}</p><Link to="/student/notices">Read all notices <ArrowRight/></Link></div></Card>:<Card><Empty title="No hostel notices" message="New notices will appear here."/></Card>}
      <Card className="span-2 menu-home"><div className="card-head"><div><span className="card-eyebrow">MAIN MESS</span><h3>Today’s menu</h3></div>{data.menu&&<div className="updated">Updated {new Date(data.menu.updated_at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}</div>}</div>{data.menu?<MealPreview menu={data.menu}/>:<Empty title="Menu not published" message="The Cook or Warden can publish today’s menu."/>}</Card>
      <Card className="timing-home"><div className="card-head"><div><span className="card-eyebrow">HOSTEL TIMINGS</span><h3>Daily schedule</h3></div><Link to="/student/timings"><ArrowRight/></Link></div>
        {data.timings.slice(0,4).map((t,i)=><div className="timing-line" key={t.id}><i className={i===1?'amber':''}></i><span>{t.label}</span><strong>{t.value}</strong></div>)}
      </Card>
      <Card className="profile-home"><div className="profile-illustration"><Building2/></div><span className="card-eyebrow">MY HOSTEL RECORD</span><h3>Room {user.room??'Unassigned'} {user.bed?`· Bed ${user.bed}`:''}</h3><p>Roll number: {profile.roll_no||user.roll_no}<br/>{profile.branch||'Branch not set'} · Year {profile.year||'—'}</p></Card>
    </div>
  </>
}

export default function Dashboard() {
  const { user }=useAuth()
  if(user.role==='STUDENT') return <StudentDashboard/>
  if(user.role==='COOK') return <MenuEditor cookMode/>
  return <OperationsDashboard role={user.role}/>
}
