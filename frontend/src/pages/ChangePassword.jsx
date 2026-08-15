import { useState } from 'react'
import { ArrowRight, LockKeyhole, ShieldCheck } from 'lucide-react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { Logo } from '../components/UI'
import { errorMessage } from '../api'

const home = { ADMIN: '/admin/dashboard', WARDEN: '/warden/dashboard', COOK: '/cook/dashboard', STUDENT: '/student/dashboard' }
export default function ChangePassword(){
  const {user,changePassword,logout}=useAuth(); const navigate=useNavigate()
  const [current,setCurrent]=useState(''),[next,setNext]=useState(''),[confirm,setConfirm]=useState(''),[error,setError]=useState(''),[saving,setSaving]=useState(false)
  if(!user)return <Navigate to="/login" replace/>
  const submit=async e=>{e.preventDefault();setError('');if(next!==confirm)return setError('New passwords do not match');setSaving(true);try{await changePassword(current,next);navigate(home[user.role],{replace:true})}catch(e){setError(errorMessage(e))}finally{setSaving(false)}}
  return <div className="password-page"><div className="password-panel"><Logo/><span className="password-icon"><ShieldCheck/></span><h1>Set your private password</h1><p>Your administrator issued a temporary password. Replace it before entering the hostel system.</p><form onSubmit={submit}><label>Current password<div className="input-wrap"><LockKeyhole/><input type="password" value={current} onChange={e=>setCurrent(e.target.value)} required/></div></label><label>New password<div className="input-wrap"><LockKeyhole/><input type="password" value={next} onChange={e=>setNext(e.target.value)} required minLength="10"/></div></label><label>Confirm new password<div className="input-wrap"><LockKeyhole/><input type="password" value={confirm} onChange={e=>setConfirm(e.target.value)} required minLength="10"/></div></label><small>At least 10 characters with upper-case, lower-case, a number and a symbol.</small>{error&&<div className="login-error">{error}</div>}<button className="btn primary full" disabled={saving}>{saving?'Saving…':<>Save password <ArrowRight/></>}</button><button type="button" className="password-signout" onClick={logout}>Sign out instead</button></form></div></div>
}
