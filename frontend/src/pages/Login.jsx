import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Building2, Check, CookingPot, Eye, EyeOff, GraduationCap, LockKeyhole, Mail, Phone, ShieldCheck, Sparkles, UserCog, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { Logo, Loading } from '../components/UI'
import api, { errorMessage } from '../api'

const home = { ADMIN: '/admin/dashboard', WARDEN: '/warden/dashboard', COOK: '/cook/dashboard', STUDENT: '/student/dashboard' }
const roles = [
  { id:'ADMIN', label:'Administrator', description:'Full hostel management', icon:ShieldCheck },
  { id:'WARDEN', label:'Warden', description:'Students, rooms and attendance', icon:UserCog },
  { id:'COOK', label:'Cook', description:'Daily mess menu', icon:CookingPot },
  { id:'STUDENT', label:'Student', description:'Personal hostel dashboard', icon:GraduationCap },
]

export default function Login() {
  const { login, loading, user } = useAuth()
  const navigate = useNavigate()
  const [setupRequired, setSetupRequired] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [selectedRole, setSelectedRole] = useState('ADMIN')
  const [error, setError] = useState('')
  const [setup, setSetup] = useState({ name: '', email: '', phone: '', password: '', confirm: '' })
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (user) navigate(home[user.role], { replace: true })
    else api.get('/auth/setup/status').then(r => setSetupRequired(r.data.setup_required)).catch(e => setError(errorMessage(e)))
  }, [user])

  const submit = async e => {
    e.preventDefault(); setError('')
    try { const next = await login(email, password); navigate(home[next.role], { replace: true }) }
    catch (err) { setError(errorMessage(err)) }
  }
  const createAdmin = async e => {
    e.preventDefault(); setError('')
    if (setup.password !== setup.confirm) return setError('Passwords do not match')
    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}/.test(setup.password)) {
      return setError('Password must have at least 10 characters, including upper-case, lower-case, a number and a symbol.')
    }
    setCreating(true)
    try {
      await api.post('/auth/setup/admin', { name: setup.name, email: setup.email, phone: setup.phone, password: setup.password })
      const next = await login(setup.email, setup.password)
      navigate(home[next.role], { replace: true })
    } catch (err) { setError(errorMessage(err)) }
    finally { setCreating(false) }
  }
  if (setupRequired === null && !error) return <Loading label="Checking hostel setup…"/>

  return <div className="login-page">
    <section className="login-brand-panel">
      <div className="login-brand-inner">
        <Logo light/>
        <div className="login-hero-copy">
          <motion.div initial={{opacity:0,y:15}} animate={{opacity:1,y:0}} className="hero-kicker"><Sparkles size={15}/> SECURE HOSTEL OPERATIONS</motion.div>
          <motion.h1 initial={{opacity:0,y:18}} animate={{opacity:1,y:0}} transition={{delay:.08}}>Malla Reddy<br/><em>Boys Hostel.</em></motion.h1>
          <motion.p initial={{opacity:0}} animate={{opacity:1}} transition={{delay:.18}}>Secure room allocation, attendance, mess operations and student services in one reliable system.</motion.p>
          <div className="login-proof">
            <div><span><Building2/></span><strong>431 rooms ready</strong><small>1,724 managed beds</small></div>
            <div><span><ShieldCheck/></span><strong>Role-based security</strong><small>Private data stays protected</small></div>
          </div>
        </div>
      </div>
      <div className="brand-decoration deco-one"></div><div className="brand-decoration deco-two"></div>
    </section>
    <section className="login-form-panel">
      <div className="mobile-login-logo"><Logo/></div>
      <div className="login-form-wrap">
        {setupRequired ? <>
          <div className="form-heading"><span>FIRST-TIME SETUP</span><h2>Create the administrator</h2><p>No sample users were added. Create the real account that will manage this hostel.</p></div>
          <form onSubmit={createAdmin}>
            <label>Administrator name<div className="input-wrap"><UserRound/><input value={setup.name} onChange={e=>setSetup({...setup,name:e.target.value})} required autoFocus/></div></label>
            <label>Phone number<div className="input-wrap"><Phone/><input value={setup.phone} onChange={e=>setSetup({...setup,phone:e.target.value})} required/></div></label>
            <label>Email address<div className="input-wrap"><Mail/><input type="email" value={setup.email} onChange={e=>setSetup({...setup,email:e.target.value})} required/></div></label>
            <label>Password<div className="input-wrap"><LockKeyhole/><input type={show?'text':'password'} value={setup.password} onChange={e=>setSetup({...setup,password:e.target.value})} required minLength="10"/><button type="button" onClick={()=>setShow(!show)}>{show?<EyeOff/>:<Eye/>}</button></div></label>
            <label>Confirm password<div className="input-wrap"><LockKeyhole/><input type={show?'text':'password'} value={setup.confirm} onChange={e=>setSetup({...setup,confirm:e.target.value})} required minLength="10"/></div></label>
            <p className="password-help">Use at least 10 characters with upper-case, lower-case, a number and a symbol.</p>
            <AnimatePresence>{error && <motion.div initial={{opacity:0,height:0}} animate={{opacity:1,height:'auto'}} className="login-error">{error}</motion.div>}</AnimatePresence>
            <button className="btn primary login-submit" disabled={creating}>{creating?'Creating secure account…':<>Complete setup <ArrowRight/></>}</button>
          </form>
        </> : <>
          <div className="form-heading"><span>SECURE ACCESS</span><h2>Welcome back</h2><p>Select your role and sign in with the account created by the Administrator.</p></div>
          <div className="role-grid">{roles.map(role=>{const Icon=role.icon;return <button type="button" key={role.id} className={selectedRole===role.id?'selected':''} onClick={()=>setSelectedRole(role.id)}><span className="role-check">{selectedRole===role.id&&<Check/>}</span><Icon className="role-main-icon"/><strong>{role.label}</strong><small>{role.description}</small></button>})}</div>
          <form onSubmit={submit}>
            <label>Email address<div className="input-wrap"><Mail/><input type="email" value={email} onChange={e=>setEmail(e.target.value)} required autoFocus/></div></label>
            <label>Password<div className="input-wrap"><LockKeyhole/><input type={show?'text':'password'} value={password} onChange={e=>setPassword(e.target.value)} required minLength="8"/><button type="button" onClick={()=>setShow(!show)}>{show?<EyeOff/>:<Eye/>}</button></div></label>
            <AnimatePresence>{error && <motion.div initial={{opacity:0,height:0}} animate={{opacity:1,height:'auto'}} className="login-error">{error}</motion.div>}</AnimatePresence>
            <button className="btn primary login-submit" disabled={loading}>{loading?'Opening workspace…':<>Sign in as {roles.find(r=>r.id===selectedRole)?.label} <ArrowRight/></>}</button>
          </form>
        </>}
        <p className="login-foot"><ShieldCheck/> Malla Reddy Boys Hostel · Authorised access only</p>
      </div>
    </section>
  </div>
}
