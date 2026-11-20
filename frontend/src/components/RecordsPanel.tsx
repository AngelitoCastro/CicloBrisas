import { useState } from 'react'
import { BookOpen, CheckCircle2, ChevronDown, ClipboardList, GlassWater, Layers, Minus, Package, Plus, Save, UserRound, Wrench } from 'lucide-react'
import { type Data, type IntakeLine, type IntakeRecord, isoDate, money, uid } from '../types'
import { intakeCatalog } from '../services/materialCatalog'

interface Props {
  data: Data
  onSave: (record: IntakeRecord) => void
  notify: (message: string) => void
}
const icons = { paper: BookOpen, plastic: Package, metal: Wrench, glass: GlassWater, other: Layers }
const formatKg = (n: number) => n.toLocaleString('es-CO', { maximumFractionDigits: 2 })
const round = (n: number) => Math.round(n * 100) / 100

export default function RecordsPanel({ data, onSave, notify }: Props) {
  const members = data.members.filter(m => m.flow === 'reciclable' && m.active)
  const [memberId, setMemberId] = useState('')
  const [category, setCategory] = useState('')
  const [weights, setWeights] = useState<Record<string, string>>({})
  const [packs, setPacks] = useState<Record<string, string>>({})
  const [showPacks, setShowPacks] = useState(false)
  const [date, setDate] = useState(isoDate)
  const [provider, setProvider] = useState('')
  const [ticket, setTicket] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState<IntakeRecord | null>(null)
  const [historyId, setHistoryId] = useState('')
  const [historyOpen, setHistoryOpen] = useState(false)
  const member = members.find(m => m.id === memberId)
  const active = intakeCatalog.find(c => c.id === category)
  const rateFor = (name: string, key: string) => data.rates[name] ?? data.rates[key] ?? 0
  const lines: IntakeLine[] = intakeCatalog.flatMap(c => c.items.map(item => ({
    material: item.name,
    kg: Number(weights[item.name] || 0),
    rate: rateFor(item.name, item.rateKey),
    packs: packs[item.name] ? Number(packs[item.name]) : undefined,
  }))).filter(l => l.kg > 0)
  const total = round(lines.reduce((sum, l) => sum + l.kg, 0))
  const value = lines.reduce((sum, l) => sum + l.kg * l.rate, 0)
  const records = data.intakeRecords
  const history = records.find(r => r.id === historyId)
  const invalid = Object.values(weights).some(v => !Number.isFinite(Number(v)) || Number(v) < 0 || Math.abs(Number(v) - round(Number(v))) > 1e-8)
    || Object.entries(packs).some(([name,v]) => !Number.isInteger(Number(v)) || Number(v) < 0 || (Number(v)>0 && !(Number(weights[name])>0)))

  // Los botones suman o restan un kilo; el campo permite pesos decimales.
  function adjust(name: string, step: number) {
    setWeights(prev => ({ ...prev, [name]: String(Math.max(0, round((Number(prev[name]) || 0) + step))) }))
    setError('')
  }
  function reset() {
    setWeights({}); setPacks({}); setProvider(''); setTicket(''); setNotes('')
    setCategory(''); setMemberId(''); setDate(isoDate()); setShowPacks(false); setError('')
  }
  function save() {
    if (!member || !date || date > isoDate() || invalid || !lines.length || !Number.isFinite(total) || !Number.isFinite(value)) {
      setError('Selecciona un reciclador, una fecha válida y registra al menos un peso positivo. Revisa los decimales y las pacas.'); return
    }
    if (ticket.trim() && records.some(r => r.ticketNumber.toLowerCase() === ticket.trim().toLowerCase())) {
      setError('Este número de tiquete ya está registrado. Revisa el historial antes de guardar.'); return
    }
    const record: IntakeRecord = { id: uid(), memberId: member.id, memberName: member.name,
      providerName: provider.trim() || member.name, ticketNumber: ticket.trim(), date,
      notes: notes.trim(), lines, created: new Date().toISOString() }
    onSave(record); setSaved(record); setHistoryId(record.id); reset(); notify('Registro de materiales guardado en el prototipo.')
  }

  return (
    <section className="panel intake-panel">
      <header className="panel-head"><ClipboardList size={26}/><h2>Registro de materiales recibidos</h2></header>
      <div className="panel-body space-y-6">
        <p className="intake-intro">Selecciona a quien entrega el material, elige una categoría y registra los kilos pesados.</p>
        {saved && <div className="intake-success" role="status"><CheckCircle2 size={28}/><div><strong>¡Registro guardado!</strong><p>{saved.memberName} · {formatKg(saved.lines.reduce((s,l)=>s+l.kg,0))} kg. Puedes crear otro registro o consultar el historial.</p></div><button className="btn intake-touch" onClick={()=>setSaved(null)}>Cerrar</button></div>}
        <div>
          <div className="step"><b>1</b><h3 className="intake-heading">¿Qué reciclador entrega los materiales?</h3></div>
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
            {members.map(m => <button type="button" key={m.id} aria-pressed={memberId===m.id} className={'intake-choice '+(memberId===m.id?'chosen':'')} onClick={()=>{setMemberId(m.id);setSaved(null);setError('')}}>
              <span className="intake-person"><UserRound size={30}/></span><strong>{m.name}</strong><small>{m.group}</small>{memberId===m.id&&<CheckCircle2 className="intake-check" size={21}/>}
            </button>)}
          </div>
          {!members.length && <p className="note mt-3">No hay recicladores activos. Agrega uno desde Equipo.</p>}
        </div>
        {member && <>
          <div className="intake-details">
            <label className="field">Fecha de pesaje<input type="date" max={isoDate()} value={date} onChange={e=>setDate(e.target.value)}/></label>
            <label className="field">Proveedor (opcional)<input value={provider} placeholder={member.name} onChange={e=>setProvider(e.target.value)}/></label>
            <label className="field">N.º de tiquete (opcional)<input value={ticket} placeholder="Ej. 38298" onChange={e=>setTicket(e.target.value)}/></label>
          </div>
          <div>
            <div className="step"><b>2</b><h3 className="intake-heading">¿Qué tipo de material trae?</h3></div>
            <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3">
              {intakeCatalog.map(c => { const Icon=icons[c.icon]; const kg=c.items.reduce((s,m)=>s+(Number(weights[m.name])||0),0); return <button type="button" key={c.id} aria-expanded={category===c.id} className={'intake-choice category '+(category===c.id?'chosen':'')} onClick={()=>setCategory(category===c.id?'':c.id)}><Icon size={30}/><strong>{c.name}</strong><span>{formatKg(kg)} kg <ChevronDown size={18} className={category===c.id?'rotate-180':''}/></span></button> })}
            </div>
            {active && <div className="intake-materials mt-4">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4"><h3 className="intake-heading">{active.name}</h3><label className="checkline intake-packs"><input type="checkbox" checked={showPacks} onChange={e=>setShowPacks(e.target.checked)}/> Registrar pacas</label></div>
              <p className="intake-intro mb-3">Usa + o − para ajustar de 1 kg en 1 kg, o toca el número para escribir el peso exacto.</p>
              {active.items.map(item => <div className="intake-row" key={item.name}>
                <strong>{item.name}</strong>
                <div className="intake-counter">
                  <button type="button" aria-label={'Restar un kilo de '+item.name} disabled={!(Number(weights[item.name])>0)} onClick={()=>adjust(item.name,-1)}><Minus size={26}/></button>
                  <label className="intake-weight"><input aria-label={'Peso en kilogramos de '+item.name} type="number" inputMode="decimal" min="0" step="0.01" value={weights[item.name]??'0'} onFocus={e=>e.target.select()} onChange={e=>{setWeights(p=>({...p,[item.name]:e.target.value}));setError('')}}/><span>kg</span></label>
                  <button type="button" aria-label={'Sumar un kilo de '+item.name} onClick={()=>adjust(item.name,1)}><Plus size={26}/></button>
                </div>
                {showPacks&&<label className="field intake-pack-field">N.º pacas<input type="number" min="0" step="1" inputMode="numeric" value={packs[item.name]??''} onChange={e=>setPacks(p=>({...p,[item.name]:e.target.value}))}/></label>}
              </div>)}
            </div>}
          </div>
          <div className="intake-summary">
            <div className="step"><b>3</b><h3 className="intake-heading">Revisa y guarda</h3></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4"><div><p>En total</p><strong className="intake-total">{formatKg(total)} kg</strong></div><div><p>Valor para {member.name}</p><strong className="intake-total">{money(value)}</strong></div></div>
            {lines.map(l=><div key={l.material} className="intake-summary-line"><span>{l.material}{l.packs!==undefined?` · ${l.packs} pacas`:''}</span><strong>{formatKg(l.kg)} kg</strong><small>{money(l.kg*l.rate)}</small></div>)}
            <label className="field mt-4">Observaciones (opcional)<textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Algo importante sobre la entrega"/></label>
            {error&&<p className="error mt-3" role="alert">{error}</p>}
            <button type="button" className="btn primary w-full intake-save mt-4" disabled={!lines.length||invalid} onClick={save}><Save size={24}/> Guardar registro</button>
            {invalid&&<p className="error mt-2">Ingresa pesos no negativos de hasta dos decimales y pacas enteras asociadas a un peso.</p>}
            <p className="muted mt-2">Este registro es una recepción física independiente; no crea una solicitud ni suma por segunda vez el peso de una recolección.</p>
          </div>
        </>}
        <div className="stepsection">
          <button type="button" aria-expanded={historyOpen} className="btn intake-touch w-full justify-between!" onClick={()=>setHistoryOpen(!historyOpen)}><span className="flex gap-2 items-center"><ClipboardList/> Ver registros guardados ({records.length})</span><ChevronDown className={historyOpen?'rotate-180':''}/></button>
          {historyOpen&&<div className="mt-3 space-y-3">{!records.length&&<p className="muted">Todavía no hay registros.</p>}{records.map(r=><button type="button" key={r.id} className={'request-card '+(historyId===r.id?'selected':'')} onClick={()=>setHistoryId(historyId===r.id?'':r.id)}><div className="flex flex-wrap justify-between gap-2"><strong>{r.memberName}</strong><strong>{formatKg(r.lines.reduce((s,l)=>s+l.kg,0))} kg</strong></div><p className="muted">{r.date} · {r.ticketNumber?`Tiquete ${r.ticketNumber}`:'Sin tiquete'} · {r.providerName}</p></button>)}
            {history&&<div className="intake-summary"><h3 className="intake-heading">Detalle de {history.memberName}</h3>{history.lines.map(l=><div key={l.material} className="intake-summary-line"><span>{l.material}{l.packs!==undefined?` · ${l.packs} pacas`:''}</span><strong>{formatKg(l.kg)} kg</strong><small>{money(l.kg*l.rate)}</small></div>)}<p className="mt-3 font-bold">Valor para el reciclador: {money(history.lines.reduce((s,l)=>s+l.kg*l.rate,0))}</p>{history.notes&&<p className="mt-2">Observaciones: {history.notes}</p>}</div>}
          </div>}
        </div>
      </div>
    </section>
  )
}
