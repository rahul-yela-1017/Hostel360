import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Check, ChefHat, Clock3, History, MoonStar, Save, Sparkles, SunMedium, Sunrise } from 'lucide-react'
import api, { errorMessage } from '../api'
import { useAuth } from '../AuthContext'
import { Card, Empty, ErrorState, Loading, PageTitle, Toast } from '../components/UI'

const localDate = () => { const d=new Date(); d.setMinutes(d.getMinutes()-d.getTimezoneOffset()); return d.toISOString().slice(0,10) }
const dateHeading = () => new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric'}).toUpperCase()
const meta = {
  breakfast: {label:'Breakfast', icon:Sunrise, shade:'peach'}, lunch:{label:'Lunch',icon:SunMedium,shade:'green'},
  snacks:{label:'Snacks',icon:Sparkles,shade:'yellow'}, dinner:{label:'Dinner',icon:MoonStar,shade:'blue'}
}
const newForm = () => ({ menu_date:localDate(), breakfast:'',breakfast_time:'08:00 AM – 09:30 AM',lunch:'',lunch_time:'12:30 PM – 02:00 PM',snacks:'',snacks_time:'04:30 PM – 05:30 PM',dinner:'',dinner_time:'07:30 PM – 09:30 PM',description:'' })

export function MenuView() {
  const [menu,setMenu]=useState(undefined); const [error,setError]=useState('')
  const load=()=>{setError('');setMenu(undefined);api.get('/menu/today').then(r=>setMenu(r.data)).catch(e=>{if(e.response?.status===404)setMenu(null);else setError(errorMessage(e))})}
  useEffect(load,[])
  if(error)return <ErrorState message={error} retry={load}/>; if(menu===undefined)return <Loading/>
  if(menu===null)return <><PageTitle eyebrow="MESS · TODAY" title="Today’s menu" subtitle="Published meals will appear here."/><Card><Empty title="Menu not published yet" message="Please check again after the Cook or Warden publishes today’s menu."/></Card></>
  return <><PageTitle eyebrow={`MESS · ${dateHeading()}`} title="Today’s menu" subtitle="Meals published by the authorised mess team."/>
    <div className="menu-banner"><div><span><ChefHat/></span><div><small>{dateHeading()}</small><h2>Malla Reddy Boys Hostel mess</h2>{menu.description&&<p>{menu.description}</p>}</div></div><div className="updated-box"><Check/><span>Published<small>Updated {new Date(menu.updated_at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}</small></span></div></div>
    <div className="menu-view-grid">{Object.entries(meta).map(([key,m],i)=>{const Icon=m.icon;return <Card className={`menu-view-card ${m.shade}`} delay={i*.05} key={key}>
      <div className="meal-head"><span><Icon/></span><div><small>{m.label.toUpperCase()}</small><strong>{menu[`${key}_time`]}</strong></div></div>
      <div className="food-list">{menu[key].split(' · ').map((food,index)=><div key={`${food}-${index}`}><i>{index+1}</i><span>{food}</span></div>)}</div>
    </Card>})}</div>
  </>
}

export default function MenuEditor({ cookMode=false }) {
  const {user}=useAuth(); const [form,setForm]=useState(newForm); const [loading,setLoading]=useState(true)
  const [saving,setSaving]=useState(false); const [error,setError]=useState(''); const [toast,setToast]=useState(null); const [history,setHistory]=useState([])
  const load=async()=>{setError('');setLoading(true);try{
    const [menuResult,historyResult]=await Promise.allSettled([api.get('/menu/today'),api.get('/menu/history')])
    if(menuResult.status==='fulfilled')setForm({...newForm(),...menuResult.value.data});else if(menuResult.reason?.response?.status!==404)throw menuResult.reason
    if(historyResult.status==='fulfilled')setHistory(historyResult.value.data);else throw historyResult.reason
  }catch(e){setError(errorMessage(e))}finally{setLoading(false)}}
  useEffect(()=>{load()},[])
  const set=(key,value)=>setForm(v=>({...v,[key]:value}))
  const complete=['breakfast','lunch','snacks','dinner'].every(k=>form[k].trim().length>=2)
  const publish=async()=>{if(!complete)return;setSaving(true);setError('');try{
    const endpoint=user.role==='WARDEN'?'/warden/menu':'/cook/menu'
    const payload={menu_date:form.menu_date,breakfast:form.breakfast,breakfast_time:form.breakfast_time,lunch:form.lunch,lunch_time:form.lunch_time,snacks:form.snacks,snacks_time:form.snacks_time,dinner:form.dinner,dinner_time:form.dinner_time,description:form.description||null,publish:true,hostel_id:1,reason:'Daily menu update'}
    const {data}=await api.put(endpoint,payload); setForm(v=>({...v,...data.menu}));setToast({title:'Menu published',message:'Students can see the updated menu now.'});load()
  }catch(e){setToast({type:'error',title:'Could not publish',message:errorMessage(e)})}finally{setSaving(false)}}
  if(loading)return <Loading/>; if(error)return <ErrorState message={error} retry={load}/>
  return <>
    <PageTitle eyebrow={`${cookMode?'MESS WORKSPACE':'HOSTEL MENU'} · ${dateHeading()}`} title="Today’s hostel menu"
      subtitle="Enter all four meals and publish them directly to student accounts."
      actions={<button className="btn primary" onClick={publish} disabled={saving||!complete}><Save/>{saving?'Publishing…':'Publish menu'}</button>}/>
    <div className="publish-note"><span><Check/></span><div><strong>Direct publishing</strong><p>Changes become visible to students immediately after you publish.</p></div></div>
    <div className="editor-layout"><div className="editor-grid">{Object.entries(meta).map(([key,m],i)=>{const Icon=m.icon;return <Card className="meal-editor" delay={i*.04} key={key}>
      <div className={`meal-editor-icon ${m.shade}`}><Icon/></div><div className="meal-editor-head"><div><small>MEAL {String(i+1).padStart(2,'0')}</small><h3>{m.label}</h3></div><label><Clock3/><input value={form[`${key}_time`]} onChange={e=>set(`${key}_time`,e.target.value)}/></label></div>
      <label className="editor-label">Food items <span>Separate with ·</span><textarea value={form[key]} onChange={e=>set(key,e.target.value)} rows="3" placeholder={`Enter ${m.label.toLowerCase()} items`} required/></label>
      <div className="item-chips">{form[key].split(' · ').filter(Boolean).map((x,index)=><span key={`${x}-${index}`}>{x}</span>)}</div>
    </Card>})}</div>
      <aside className="history-panel"><div className="card-head"><div><span className="card-eyebrow">MENU ARCHIVE</span><h3>Published menus</h3></div><History/></div>
        {history.length?history.slice(0,6).map(h=><div className="history-item" key={h.id}><div><strong>{new Date(h.menu_date+'T00:00:00').toLocaleDateString('en-IN',{day:'2-digit',month:'short'})}</strong><span>{new Date(h.menu_date+'T00:00:00').toLocaleDateString('en-IN',{weekday:'short'})}</span></div><p>{h.breakfast}<small>{h.dinner}</small></p></div>):<Empty title="No menus published"/>}
      </aside></div>
    <AnimatePresence><Toast toast={toast} onClose={()=>setToast(null)}/></AnimatePresence>
  </>
}
