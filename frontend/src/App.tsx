import { useState, useEffect } from 'react'
import { Sprout, Recycle, Shield, ClipboardList, Users, MessageCircle, History, Settings, BookOpen, LogOut, Scale, LayoutDashboard, BrainCircuit, Award } from 'lucide-react'
import { Brand, InstitutionalLogos } from './components/UI'
import { repository } from './services/repository'
import { applyRequestUpdate, type DemoNotice } from './services/requestUpdates'
import { type Role, type Flow, type Data, type Request, type Status, kgOf } from './types'
import Collections from './pages/Collections'
import PointRulesPage from './pages/PointRules'
import { Team, SettingsPage, Reports, KnowledgePage, Training } from './pages/Management'
function saveAdminSettings(data: Data, settings: Partial<Pick<Data, 'pointRules' | 'rates'>>, setData: (next: Data) => void) {
    const next = { ...data, ...settings }
    try {
        repository.save(next)
        setData(next)
        return true
    } catch {
        return false
    }
}

const roles = [{ id: 'huerta' as const, title: 'Coordinador de Huerta', desc: 'Orgánicos, entregas directas y donaciones', icon: Sprout }, { id: 'reciclaje' as const, title: 'Coordinador de Reciclaje', desc: 'Aprovechables, recolecciones y tarifas', icon: Recycle }, { id: 'admin' as const, title: 'Administrador', desc: 'Gestión general, horarios y resultados', icon: Shield }]
export default function App() { const [data, setData] = useState<Data>(() => repository.load()), [role, setRole] = useState<Role | null>(null), [page, setPage] = useState('Recolecciones'), [toast, setToast] = useState(''); useEffect(() => { try { repository.save(data) } catch { setToast('No se pudo guardar localmente. El almacenamiento puede estar lleno.') } }, [data]); useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 4500); return () => clearTimeout(t) }, [toast]); const notify = (s: string) => setToast(s); const flow: Flow | undefined = role === 'huerta' ? 'organico' : role === 'reciclaje' ? 'reciclable' : undefined; function update(r: Request, notifications?: DemoNotice[], reply?: DemoNotice, expectedStatus?: Status) {
    setData(current => applyRequestUpdate(current, r, notifications, reply, expectedStatus))
} const props = { data, setData: (fn: (d: Data) => Data) => setData(fn), notify, flow }; const current = roles.find(r => r.id === role); const nav = role === 'admin' ? [{ n: 'Resumen', i: LayoutDashboard }, { n: 'Equipo', i: Users }, { n: 'Reglas de EcoPuntos', i: Award }, { n: 'Base de conocimiento', i: BrainCircuit }, { n: 'Capacitación', i: BookOpen }] : [{ n: 'Recolecciones', i: ClipboardList }, { n: 'Equipo', i: Users }, { n: 'Historial', i: History }, { n: 'Métricas', i: Settings }, { n: 'Capacitación', i: BookOpen }]; const total = data.requests.filter(r => r.status === 'completada' && (!flow || r.flow === flow)).reduce((s, r) => s + kgOf(r), 0); return <>{!role ? <main className="login"><section className="panel login-card"><div className="flex justify-center mb-5"><Brand /></div><h1 className="text-center">Gestión comunitaria</h1><p className="text-center muted mt-2 mb-6">Acceso interno</p><div className="space-y-3">{roles.map(r => <button key={r.id} className="request-card flex! gap-3 items-center" onClick={() => { setRole(r.id); setPage(r.id === 'admin' ? 'Resumen' : 'Recolecciones') }}><span className="mini-icon"><r.icon /></span><div className="flex-1"><h3>{r.title}</h3><p className="muted">{r.desc}</p></div><span className="text-xl text-[#527b43]">›</span></button>)}</div><a className="btn w-full mt-5" href="?vista=whatsapp">
    <MessageCircle size={18} aria-hidden="true" /> Ver recorrido por WhatsApp
</a><p className="note mt-5">Acceso de demostración, sin contraseña. Solo personal interno en el diseño; la autenticación y permisos reales se implementarán con Supabase.</p><div className="mt-5 border-t border-[#d9e1d7] pt-4"><InstitutionalLogos /></div></section></main> : <><header className="topbar"><Brand /><div className="top-info"><strong>{current?.title}{flow === 'organico' ? ' (Orgánicos)' : flow === 'reciclable' ? ' (Aprovechables)' : ''}</strong><p>Villas de San Pablo · Fundación Santo Domingo</p></div><div className="top-total"><Scale size={23} color="#b5d99b" /> Total recolectado: <strong className="text-xl">{total.toLocaleString('es-CO')} kg</strong></div><button className="icon-btn border-[#638177]!" title="Cambiar perfil" aria-label="Cambiar perfil" onClick={() => setRole(null)}><LogOut size={21} /></button></header><nav className="nav" aria-label="Navegación principal">{nav.map(({ n, i: Icon }) => <button key={n} className={page === n ? 'active' : ''} onClick={() => setPage(n)}><Icon size={18} />{n}</button>)}</nav><main className="main" key={role + page}>{page === 'Recolecciones' && flow ? <Collections flow={flow} data={data} update={update} notify={notify} onSaveRecord={record => setData(d => ({ ...d, intakeRecords: [record, ...d.intakeRecords] }))} /> : role === 'admin' && page === 'Reglas de EcoPuntos' ? <PointRulesPage rules={data.pointRules} save={pointRules => saveAdminSettings(data, { pointRules }, setData)}
    rates={data.rates} saveRates={rates => notify(saveAdminSettings(data, { rates }, setData)
        ? 'Tarifas guardadas.' : 'No se pudieron guardar las tarifas en este navegador.')} /> : page === 'Equipo' ? <Team {...props} role={role} /> : page === 'Métricas' && flow ? <SettingsPage {...props} flow={flow} /> : page === 'Base de conocimiento' ? <KnowledgePage {...props} /> : page === 'Capacitación' ? <Training /> : <Reports {...props} />}<footer className="app-footer">
    <InstitutionalLogos />
    <div className="app-footer-copy">
        <p>EcoConecta · Prototipo local · WhatsApp simulado</p>
        <p>EcoPuntos de demostración sujetos a validación FSD.</p>
    </div>
</footer></main></>}{toast && <div className="toast" role="status">{toast}</div>}</> }
