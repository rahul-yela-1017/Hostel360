import { motion } from 'framer-motion'
import { AlertCircle, ArrowDownRight, ArrowUpRight, CheckCircle2, LoaderCircle } from 'lucide-react'

export function Logo({ compact = false, light = false }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`}>
    <div className="brand-mark"><span></span><span></span><span></span></div>
    {!compact && <div><strong>MRBH</strong><small>BOYS HOSTEL</small></div>}
  </div>
}

export function PageTitle({ eyebrow, title, subtitle, actions }) {
  return <div className="page-heading">
    <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
    {actions && <div className="heading-actions">{actions}</div>}
  </div>
}

export function Card({ children, className = '', delay = 0 }) {
  return <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .35, delay }} className={`card ${className}`}>{children}</motion.section>
}

export function StatCard({ label, value, hint, icon: Icon, tone = 'mint', trend, delay = 0 }) {
  const up = trend?.startsWith?.('+')
  return <Card className="stat-card" delay={delay}>
    <div className={`stat-icon ${tone}`}><Icon size={20}/></div>
    <div className="stat-copy"><span>{label}</span><strong>{value}</strong>
      <small>{trend && <b className={up ? 'up' : 'down'}>{up ? <ArrowUpRight/> : <ArrowDownRight/>}{trend}</b>} {hint}</small>
    </div>
  </Card>
}

export function Badge({ children, tone }) {
  const computed = tone || String(children).toLowerCase().replaceAll('_', '-')
  return <span className={`badge ${computed}`}>{String(children).replaceAll('_', ' ')}</span>
}

export function Progress({ value, tone = 'mint' }) {
  return <div className="progress"><span className={tone} style={{ width: `${Math.min(100, Math.max(0, value || 0))}%` }}/></div>
}

export function Loading({ label = 'Loading live hostel data…' }) {
  return <div className="state"><LoaderCircle className="spin"/><strong>{label}</strong></div>
}

export function Empty({ title = 'Nothing here yet', message = 'New information will appear here.' }) {
  return <div className="state empty"><div className="state-orb">·</div><strong>{title}</strong><span>{message}</span></div>
}

export function ErrorState({ message, retry }) {
  return <div className="state error"><AlertCircle/><strong>We couldn't load this view</strong><span>{message}</span>{retry && <button className="btn secondary" onClick={retry}>Try again</button>}</div>
}

export function Toast({ toast, onClose }) {
  if (!toast) return null
  return <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className={`toast ${toast.type || 'success'}`}>
    <CheckCircle2/><div><strong>{toast.title || 'Done'}</strong><span>{toast.message}</span></div><button onClick={onClose}>×</button>
  </motion.div>
}
