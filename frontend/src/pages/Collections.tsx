import { useEffect, useRef, useState, type FormEvent } from 'react'
import { CalendarDays, Clock, CheckCircle2, MapPin, Plus, MessageCircle, Scale, ShieldCheck, Check, Sun, Sunrise, Sunset, ClipboardList, House, Layers, Phone, Search, Sprout, Star, Store } from 'lucide-react'
import { type Data, type Flow, type Request, type Status, type MaterialLine, type IntakeRecord, type CollectionConfirmation, dayNames, kgOf, money, valueOf, isRecyclerValuePending } from '../types'
import { Badge, Empty, Modal } from '../components/UI'
import Avisos from '../components/Avisos'
import NewRequest from '../components/NewRequest'
import RecordsPanel from '../components/RecordsPanel'
import RecyclingBreakdown from '../components/RecyclingBreakdown'
import { closeCollection } from '../services/collectionClosure'
import { collectionSlotKey, getCollectionClock, getNextCollectionAvailability, isCollectionDayAvailable, isCollectionSlotAvailable } from '../services/collectionSchedule'
type Props = { flow: Flow; data: Data; update: (r: Request, notifications?: { name: string; phone: string; text: string }[], reply?: { name: string; phone: string; text: string }, expectedStatus?: Status) => void; notify: (text: string) => void; onSaveRecord: (record: IntakeRecord) => void; linkedDemo?: boolean }
const views = {
    pending: { label: 'Por programar', icon: Clock, tone: 'amber' },
    scheduled: { label: 'Programadas', icon: CalendarDays, tone: 'teal' },
    completed: { label: 'Recolectadas', icon: CheckCircle2, tone: 'green' },
    rejected: { label: 'Rechazadas', icon: null, tone: 'neutral' },
}
type RequestView = keyof typeof views
type View = RequestView | 'records'

function requestView(status: Request['status']): RequestView {
    switch (status) {
        case 'programada': return 'scheduled'
        case 'completada': return 'completed'
        case 'rechazada': return 'rejected'
        default: return 'pending'
    }
}

export default function Collections({ flow, data, update, notify, onSaveRecord, linkedDemo = false }: Props) {
    const [view, setView] = useState<View>(() => {
        const request = linkedDemo ? data.requests.find(item => item.flow === flow) : undefined
        return request ? requestView(request.status) : 'pending'
    })
    const [selection, setSelection] = useState('')
    const [creatingRequest, setCreatingRequest] = useState(false)
    const [reschedule, setReschedule] = useState(false)
    const [search, setSearch] = useState('')
    const [generator, setGenerator] = useState('')
    const [date, setDate] = useState('')
    const [filtersOpen, setFiltersOpen] = useState(false)
    const detailTitle = useRef<HTMLHeadingElement>(null)
    const recycling = flow === 'reciclable'
    const own = data.requests.filter(r => r.flow === flow)
    const available: RequestView[] = ['pending', 'scheduled', 'completed']
    const visible = own.filter(r => requestView(r.status) === view &&
        (!generator || (generator === 'pilot' ? r.pilot && r.generator === 'Comercio' : r.generator === generator)) &&
        (!date || (r.date || r.created.slice(0, 10)) === date) &&
        [r.name, r.id, r.description, r.address].some(value => value.toLowerCase().includes(search.trim().toLowerCase())))

    const selected = view === 'records' ? own.find(r => r.id === selection) : visible.find(r => r.id === selection) ?? visible[0]

    function clearSelection() {
        setSelection('')
        setReschedule(false)
    }

    function selectView(next: View) {
        setView(next)
        clearSelection()
    }

    function selectGenerator(next: string) {
        setGenerator(next)
        clearSelection()
    }

    const onUpdate: Props['update'] = (request, messages, reply, expectedStatus) => {
        update(request, messages, reply, expectedStatus)
        if (request.flow !== flow) {
            clearSelection()
            return
        }
        if (request.status !== selected?.status) {
            setView(requestView(request.status))
            setSelection(request.id)
            setReschedule(false)
            if (date && (request.date || request.created.slice(0, 10)) !== date) setDate('')
        }
    }

    function open(request: Request) {
        setReschedule(false)
        setSelection(request.id)
        if (view !== 'records' && window.matchMedia('(max-width: 760px)').matches) {
            requestAnimationFrame(() => {
                detailTitle.current?.focus({ preventScroll: true })
                detailTitle.current?.scrollIntoView({ block: 'start' })
            })
        }
    }

    return <div className="collections">
        <div className="flex flex-wrap justify-between items-end gap-3 mb-5">
            <div>
                {linkedDemo ? <h2>Panel de recolecciones · {recycling ? 'Reciclaje' : 'Huerta'}</h2> : <h1>Panel de recolecciones</h1>}
                <p className="muted mt-1">{linkedDemo && own.length === 0
                    ? 'Envía una solicitud desde la vista Habitante para verla en Por programar.'
                    : 'Elige una solicitud y organiza su recolección en tres pasos.'}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
                <span className="line"><CalendarDays size={16} aria-hidden="true" />
                    {new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'long', timeZone: 'America/Bogota' }).format(new Date())}
                </span>
                {!linkedDemo && <button className="btn" onClick={() => setCreatingRequest(true)}>
                    <Plus size={18} aria-hidden="true" /> Nueva solicitud
                </button>}
            </div>
        </div>
        <div className="stat-grid collection-stages" role="group" aria-label="Etapas de recolección">
            {available.map((id, index) => {
                const { label, icon: Icon, tone } = views[id]
                const count = own.filter(r => requestView(r.status) === id).length
                return <button key={id} aria-pressed={view === id} className={'stat ' + tone + (view === id ? ' active' : '')}
                    onClick={() => selectView(id)}>
                    {Icon && <span className="stat-icon"><Icon aria-hidden="true" /></span>}
                    <div><strong className="num">{count}</strong><div className="stat-label font-bold mt-1">{index + 1}. {label}</div></div>
                    {view === id && <CheckCircle2 aria-hidden="true" size={17} className="absolute right-3 top-3" />}
                </button>
            })}
        </div>
        {view === 'records' && <div className="flex justify-end mb-3">
            <button className="btn" onClick={() => selectView('pending')}>
                <ClipboardList size={18} aria-hidden="true" /> Volver a recolecciones
            </button>
        </div>}
        {!linkedDemo && recycling && <div hidden={view !== 'records'}><RecordsPanel data={data} onSave={onSaveRecord} notify={notify} /></div>}
        {!recycling && view === 'records' && <section className="panel" aria-labelledby="organic-records-title">
            <header className="panel-head">
                <Scale aria-hidden="true" size={26} /><h2 id="organic-records-title">Registro de materiales recibidos</h2>
            </header>
            <div className="panel-body space-y-3">
                <p className="muted">Consulta el peso por material registrado al confirmar las recolecciones de huerta.</p>
                {!own.some(r => r.status === 'completada' && kgOf(r) > 0) && <Empty>Aún no hay pesajes registrados.</Empty>}
                {own.filter(r => r.status === 'completada' && kgOf(r) > 0).map(r => (
                    <button className="request-card" key={r.id} onClick={() => open(r)}>
                        <span className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{r.name}</strong><strong>{kgOf(r).toLocaleString('es-CO')} kg</strong>
                        </span>
                        <span className="muted block">{r.id} · {r.date || r.created.slice(0, 10)}</span>
                        <span className="block mt-2">{r.lines?.map(line => line.material + ' · ' + line.kg.toLocaleString('es-CO') + ' kg').join(' / ')}</span>
                    </button>
                ))}
            </div>
        </section>}
        {view !== 'records' && <>
            <div className="collection-toolbar">
                <div className="collection-chips" role="group" aria-label="Tipo de generador">
                    {generatorOptions.map(({ value, label, icon: Icon }) => (
                        <button key={value} type="button" className={'btn pill' + (generator === value ? ' dark' : '')}
                            aria-pressed={generator === value} onClick={() => selectGenerator(value)}>
                            <Icon size={16} aria-hidden="true" /> {label}
                        </button>
                    ))}
                </div>
                <div className="collection-tools">
                    {!linkedDemo && <button className="btn pill" onClick={() => selectView('records')}>
                        <Scale size={16} aria-hidden="true" /> Registros de materiales
                    </button>}
                    <button className="btn pill" aria-expanded={filtersOpen} onClick={() => setFiltersOpen(!filtersOpen)}>
                        <Search size={16} aria-hidden="true" /> Buscar y filtrar
                    </button>
                    <button className={'btn pill' + (view === 'rejected' ? ' dark' : '')}
                        aria-pressed={view === 'rejected'} onClick={() => selectView(view === 'rejected' ? 'pending' : 'rejected')}>
                        Rechazadas
                    </button>
                </div>
                {filtersOpen && <div className="collection-filters panel p-3 grid gap-3 sm:grid-cols-3">
                    <label className="field">Buscar solicitud<input type="search" value={search}
                        onChange={e => { setSearch(e.target.value); clearSelection() }} placeholder="Nombre, código o dirección" /></label>
                    <label className="field">Tipo de generador<select value={generator} onChange={e => selectGenerator(e.target.value)}>
                        {generatorOptions.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
                        <option value="Comercio">Todas las unidades productivas</option>
                    </select></label>
                    <label className="field">Fecha de recepción o visita<input type="date" value={date}
                        onChange={e => { setDate(e.target.value); clearSelection() }} /></label>
                </div>}
            </div>
            <div className="collection-workspace">
                <section aria-labelledby="collection-list">
                    <div className="collection-list-heading">
                        <h2 id="collection-list">{view === 'pending' ? '¿Quién solicita recolección?' : views[view].label}</h2>
                        <span className="collection-count" aria-label={visible.length + ' solicitudes'}>{visible.length}</span>
                    </div>
                    {visible.length === 0 ? <div className="panel"><Empty>No hay solicitudes en esta sección con los filtros elegidos.</Empty></div> :
                        <div className="collection-list">
                            {visible.map(request => <RequestCard key={request.id} request={request}
                                selected={selected?.id === request.id} onSelect={() => open(request)} />)}
                        </div>}
                </section>
                <section className="panel collection-detail" aria-labelledby="collection-detail-title">
                    <header className="panel-head">
                        <ClipboardList size={21} aria-hidden="true" />
                        <h2 id="collection-detail-title" ref={detailTitle} tabIndex={-1}>
                            {selected ? (reschedule ? 'Reprogramar recolección' : requestAction[selected.status]) : 'Detalle de la solicitud'}
                        </h2>
                        {selected?.status === 'programada' && <button className="btn collection-reschedule"
                            aria-pressed={reschedule} onClick={() => setReschedule(!reschedule)}>
                            {reschedule ? 'Volver al cierre' : 'Reprogramar'}
                        </button>}
                    </header>
                    {selected ? <div className="panel-body">
                        <Detail key={selected.id + selected.status + reschedule} r={selected}
                            data={data} update={onUpdate} notify={notify} reschedule={reschedule} linkedDemo={linkedDemo}
                            onRescheduled={() => setReschedule(false)} />
                    </div> : <Empty>Selecciona una solicitud para ver los detalles.</Empty>}
                </section>
            </div>
        </>}
        {view === 'records' && selected && <Modal title={requestAction[selected.status] + ' · ' + selected.id} onClose={clearSelection}>
            <Detail key={selected.id + selected.status} r={selected} data={data} update={onUpdate} notify={notify} />
        </Modal>}
        {creatingRequest && <NewRequest flow={flow} onClose={() => setCreatingRequest(false)} onSave={request => {
            update(request)
            setCreatingRequest(false)
            selectView('pending')
            setSelection(request.id)
            setSearch('')
            setGenerator('')
            setDate('')
            notify('Solicitud registrada en Por programar.')
        }} />}
    </div>
}

const requestAction: Record<Request['status'], string> = {
    pendiente: 'Revisar solicitud', autorizada: 'Programar recolección en 3 pasos', programada: 'Recolección programada',
    completada: 'Ver cierre', rechazada: 'Ver solicitud',
}


const generatorOptions = [
    { value: '', label: 'Todos', icon: Layers },
    { value: 'pilot', label: 'Comercios piloto', icon: Store },
    { value: 'Hogar', label: 'Hogares', icon: House },
]

function RequestCard({ request, selected, onSelect }: { request: Request; selected: boolean; onSelect: () => void }) {
    const r = request
    const GeneratorIcon = r.generator === 'Comercio' ? Store : House
    const quantity = r.kind === 'donacion'
        ? (r.receivedUnits ?? r.units) + ' unidades'
        : r.status === 'completada'
            ? kgOf(r).toLocaleString('es-CO') + ' kg'
            : r.estKg > 0 ? r.estKg.toLocaleString('es-CO') + ' kg estimados' : ''
    return <button className={'request-card collection-card' + (selected ? ' selected' : '')}
        type="button" aria-pressed={selected} onClick={onSelect}>
        <span className="collection-card-heading">
            <span className={'mini-icon' + (r.generator === 'Hogar' ? ' collection-home-icon' : '')}>
                <GeneratorIcon size={20} aria-hidden="true" />
            </span>
            <span>
                <strong className="collection-name">{r.name}</strong>
                {r.pilot ? <span className="collection-pilot"><Star size={12} aria-hidden="true" /> Piloto</span> :
                    <span className="muted block">{r.generator === 'Hogar' ? 'Hogar' : 'Unidad productiva'}</span>}
            </span>
            {selected && <CheckCircle2 className="collection-selected-icon" size={17} aria-hidden="true" />}
        </span>
        <span className="collection-card-summary">
            <span className="collection-card-material">{r.description}</span>
            {quantity && <span className="muted">{quantity}</span>}
        </span>
        {r.status === 'programada' && r.date && <span className="line">
            <CalendarDays size={14} aria-hidden="true" />{formatCollectionDate(r.date)}{r.time && ' · ' + r.time}
        </span>}
        {r.delivery === 'entrega' && r.status !== 'completada' && <span className="line">
            <Sprout size={14} aria-hidden="true" /> Entrega en la huerta
        </span>}
    </button>
}

const collectionDayFormat = new Intl.DateTimeFormat('es-CO', {
    day: 'numeric', month: 'short', timeZone: 'America/Bogota',
})

function formatCollectionDate(date: string) {
    const instant = new Date(date + 'T12:00:00-05:00')
    return Number.isNaN(instant.getTime()) ? date : collectionDayFormat.format(instant)
}

function Detail({ r, data, update, notify, reschedule = false, onRescheduled, linkedDemo = false }: { r: Request; data: Data; update: Props['update']; notify: Props['notify']; reschedule?: boolean; onRescheduled?: () => void; linkedDemo?: boolean }) {
    const members = data.members.filter(member => member.flow === r.flow && member.active)
    const assigned = data.members.find(member => member.id === r.assignee && member.flow === r.flow)
    const schedule = data.schedules[r.flow]
    const [clock, setClock] = useState(getCollectionClock)
    const [initial] = useState(() => getNextCollectionAvailability(schedule, clock))
    const [assignee, setAssignee] = useState(r.assignee || members[0]?.id || '')
    const [date, setDate] = useState(r.date || initial.date)
    const [slot, setSlot] = useState(r.time || initial.slot)
    const [comment, setComment] = useState(r.note || '')
    const [reason, setReason] = useState('')
    const [reviewed, setReviewed] = useState(false)
    const [error, setError] = useState('')
    const [closureMode, setClosureMode] = useState<CollectionConfirmation['source'] | null>(null)
    const [demoMessage, setDemoMessage] = useState('')
    const [manualQuantity, setManualQuantity] = useState('')
    const [manualReason, setManualReason] = useState('')
    const [closureConfirmed, setClosureConfirmed] = useState(false)
    const [rerouting, setRerouting] = useState(false)
    const { today, tomorrow } = clock
    const [customDateOpen, setCustomDateOpen] = useState(date !== today && date !== tomorrow)
    const donation = r.kind === 'donacion'
    const quantityLabel = donation ? 'Unidades recibidas' : 'Peso total aceptado (kg)'
    const replyExample = 'LISTO ' + r.id + (donation ? ' 2' : ' 8')
    const scheduling = r.status === 'autorizada' || reschedule
    const recyclerValuePending = isRecyclerValuePending(r)

    useEffect(() => {
        if (!scheduling) return
        const interval = window.setInterval(() => setClock(getCollectionClock()), 15_000)
        return () => window.clearInterval(interval)
    }, [scheduling])

    const destination = r.flow === 'organico' ? 'Reciclaje' : 'Huerta'
    const quickNotes = [
        r.flow === 'organico' ? 'Llevar baldes extra' : 'Llevar costales extra',
        'Preguntar en local',
        r.delivery === 'entrega' ? 'Recibir en huerta' : 'Llamar al llegar',
    ]
    const member = members.find(m => m.id === assignee)
    const dateAllowed = isCollectionDayAvailable(schedule, date, clock)
    const slotAllowed = isCollectionSlotAvailable(schedule, date, slot, clock)

    function changeDate(day: string) {
        const now = getCollectionClock()
        setClock(now)
        setDate(day)
        setError('')
        if (!isCollectionSlotAvailable(schedule, day, slot, now)) {
            const next = schedule.slots.find(option => isCollectionSlotAvailable(schedule, day, collectionSlotKey(option), now))
            setSlot(next ? collectionSlotKey(next) : '')
        }
    }

    function pickDate(day: string) {
        changeDate(day)
        setCustomDateOpen(false)
    }

    const messages = (text: string) => [{ name: r.name, phone: r.phone, text }]
    const patch = (patch: Partial<Request>, history: string, notices?: { name: string; phone: string; text: string }[], reply?: { name: string; phone: string; text: string }) => update({ ...r, ...patch, history: [...r.history, history] }, notices, reply)
    function authorize() { if (!reviewed || !r.description.trim()) { setError('Confirma la revisión de la descripción o evidencia.'); return } patch({ status: 'autorizada', note: comment }, 'Coordinador autorizó la solicitud', messages(`Hola ${r.name}, tu solicitud ${r.id} fue autorizada. Te confirmaremos la asignación.`)); notify('Solicitud autorizada · aviso simulado.') }
    function program() {
        const now = getCollectionClock()
        setClock(now)
        if (!scheduling || !member || !isCollectionSlotAvailable(schedule, date, slot, now)) {
            setError('Selecciona un responsable y una franja que todavía esté disponible.')
            return
        }
        const location = r.delivery === 'entrega' ? 'Recepción en huerta' : 'Dirección: ' + r.address
        const instructions = 'Al finalizar, responde LISTO ' + r.id + ' seguido de ' + (donation ? 'las unidades recibidas' : 'los kilos aceptados') + '.'
        const text = 'Solicitud ' + r.id + ': ' + r.description + '. ' + location + '. ' + date + ', ' + slot +
            '. Nota: ' + (comment || 'Sin indicaciones') + '. ' + instructions + ' Ejemplo: ' + replyExample + '.'
        patch({ status: 'programada', assignee, date, time: slot, note: comment }, 'Programada con ' + member.name, [
            { name: member.name, phone: member.phone, text },
            { name: r.name, phone: r.phone, text: 'Tu solicitud ' + r.id + ' está programada para ' +
                date + ', ' + slot + '. Responsable: ' + member.name + ', contacto ' + member.phone + '.' },
        ])
        if (!r.backendId) notify(reschedule ? 'Cita reprogramada. Dos avisos simulados.' : 'Programación guardada. Dos avisos simulados.')
        if (reschedule) onRescheduled?.()
    }

    function chooseClosure(mode: CollectionConfirmation['source']) {
        setClosureMode(current => current === mode ? null : mode)
        setError('')
    }

    function finish(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        if (!closureMode) return
        const result = closeCollection(data, r, {
            source: closureMode,
            text: closureMode === 'whatsapp-demo' ? demoMessage : manualQuantity,
            confirmed: closureConfirmed,
            reason: manualReason,
        })
        if (!result.ok) {
            setError(result.error)
            return
        }
        update(result.request, result.notifications, result.reply, 'programada')
        const formattedPoints = result.request.ecoPoints?.toLocaleString('es-CO')
        if (!r.backendId) notify(formattedPoints === undefined ? 'Cierre registrado.' : 'Cierre registrado · ' + formattedPoints + ' EcoPuntos de demostración.')
    }

    function saveBreakdown(lines: MaterialLine[]) {
        if (!recyclerValuePending) return
        patch({ lines }, 'Desglose de reciclables registrado para calcular el valor en COP.')
        notify('Desglose registrado.')
    }

    function reject() { if (!reason.trim()) { setError('Escribe el motivo del rechazo.'); return } patch({ status: 'rechazada', rejected: reason }, `Solicitud rechazada: ${reason}`, messages(`No podemos gestionar la solicitud ${r.id}: ${reason}`)); notify('Solicitud rechazada · aviso simulado.') }
    return <section className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
            <div><h3>{r.name}</h3><p className="muted">{r.id}</p></div>
            <Badge status={r.status} />
        </div>
        <div className="collection-request-summary">
            <div className="min-w-0">
                <p className="muted">{donation ? 'Donación' : 'Material'}</p>
                <p className="font-semibold wrap-break-word">{r.description}</p>
            </div>
            {r.status !== 'completada' && (donation || r.estKg > 0) && <p className="muted">
                {donation ? r.units + ' unidades' : r.estKg.toLocaleString('es-CO') + ' kg estimados'}
            </p>}
            {r.delivery === 'entrega' && <p className="line">
                <Sprout size={15} aria-hidden="true" /> Entrega en la huerta
            </p>}
            {r.evidence && <img src={r.evidence} alt="Foto de la solicitud" className="evidence" />}
        </div>
        <details className="collection-disclosure">
            <summary>Contacto y otros datos</summary>
            <div className="collection-disclosure-body">
                <dl className="collection-request-data">
                    <div><dt><MapPin size={15} aria-hidden="true" /> Dirección</dt><dd>{r.address || 'Pendiente de registrar'}</dd></div>
                    {r.phone && <div><dt><Phone size={15} aria-hidden="true" /> Teléfono</dt><dd>{r.phone}</dd></div>}
                    <div><dt>Origen</dt><dd>{r.source === 'WhatsApp' ? 'WhatsApp simulado' : 'Registro manual'}</dd></div>
                    <div><dt>Modalidad</dt><dd>{r.delivery === 'entrega' ? 'Entrega en la huerta' : 'Recoger en dirección'}</dd></div>
                    {r.preference && <div><dt>Preferencia de visita</dt><dd>{r.preference}</dd></div>}
                    {r.note && <div><dt>Nota de la solicitud</dt><dd>{r.note}</dd></div>}
                </dl>
            </div>
        </details>
        {r.status === 'pendiente' && <>
            <div className="space-y-2">
                <h3>Revisar material</h3>
                <label className="checkline"><input type="checkbox" checked={reviewed}
                    onChange={e => setReviewed(e.target.checked)} /> Revisé la información y autorizo la solicitud.</label>
                <button className="btn primary w-full" disabled={!reviewed} onClick={authorize}>
                    <ShieldCheck size={19} aria-hidden="true" /> Autorizar solicitud
                </button>
            </div>
            <details className="collection-disclosure">
                <summary>Más acciones</summary>
                <div className="collection-disclosure-body space-y-3">
                    <button className="btn" onClick={() => {
                        patch({}, 'Se solicitó evidencia adicional', messages(
                            'Hola ' + r.name + ', ¿puedes enviar una foto o ampliar la descripción del material de ' + r.id + '?',
                        ))
                        notify('Solicitud de evidencia simulada.')
                    }}><MessageCircle size={17} aria-hidden="true" /> Solicitar foto o más información</button>
                    {!linkedDemo && r.kind === 'residuo' && <button className="btn" aria-expanded={rerouting}
                        onClick={() => setRerouting(!rerouting)}>Cambiar categoría</button>}
                    {rerouting && <div className="note space-y-2">
                        <p>La solicitud {r.id} pasará a Por programar del panel de {destination}.</p>
                        <button className="btn" onClick={() => {
                            patch({ flow: r.flow === 'organico' ? 'reciclable' : 'organico', delivery: 'recoger' }, 'Solicitud remitida a ' + destination)
                            notify('Solicitud remitida a ' + destination + '.')
                        }}>Confirmar traslado a {destination}</button>
                    </div>}
                    <label className="field">Comentario del coordinador<textarea value={comment}
                        onChange={e => setComment(e.target.value)} placeholder="Indicaciones para el equipo" /></label>
                    <div className="stepsection">
                        <label className="field">Motivo del rechazo<input value={reason}
                            onChange={e => setReason(e.target.value)} placeholder="Ej. falta información esencial" /></label>
                        <button className="btn danger mt-2" onClick={reject}>Rechazar solicitud</button>
                    </div>
                </div>
            </details>
        </>}
        {scheduling && <>
            <div>
                <div className="step"><b>1</b><h3>{r.delivery === 'entrega' ? '¿Quién recibe en la huerta?' : '¿Quién va a recoger?'}</h3></div>
                <div className="collection-choices">
                    {members.map(m => <button key={m.id} className={'btn flex-col items-start! text-left ' + (assignee === m.id ? 'selected' : '')}
                        aria-pressed={assignee === m.id} onClick={() => setAssignee(m.id)}>
                        <span className="avatar">{m.name.split(' ').map(name => name[0]).slice(0, 2).join('')}</span>
                        <strong>{m.name}</strong>
                        <small>{data.requests.filter(q => q.assignee === m.id && q.date === date && q.status === 'programada').length} asignadas ese día</small>
                    </button>)}
                </div>
                {!members.length && <p className="error">No hay miembros activos. Pide a Administración que actualice el equipo.</p>}
            </div>
            <div>
                <div className="step"><b>2</b><h3>¿Cuándo va?</h3></div>
                <div className="collection-choices collection-date-buttons mb-2">
                    <button className={'btn ' + (!customDateOpen && date === today ? 'selected' : '')}
                        aria-pressed={!customDateOpen && date === today} disabled={!isCollectionDayAvailable(schedule, today, clock)} onClick={() => pickDate(today)}>Hoy</button>
                    <button className={'btn ' + (!customDateOpen && date === tomorrow ? 'selected' : '')}
                        aria-pressed={!customDateOpen && date === tomorrow} disabled={!isCollectionDayAvailable(schedule, tomorrow, clock)} onClick={() => pickDate(tomorrow)}>Mañana</button>
                    <button className={'btn ' + (customDateOpen ? 'selected' : '')} aria-expanded={customDateOpen}
                        onClick={() => setCustomDateOpen(!customDateOpen)}><CalendarDays size={15} aria-hidden="true" /> Otro día</button>
                </div>
                {customDateOpen && <>
                    <label className="field mb-2">Elegir fecha<input type="date" min={today} value={date} onChange={e => changeDate(e.target.value)} /></label>
                    <p className="muted mb-2">Días configurados: {schedule.days.map(d => dayNames[d]).join(', ')}</p>
                </>}
                {!dateAllowed && <p className="error mb-2">Selecciona un día con franjas de recolección disponibles.</p>}
                <div className="collection-choices">
                    {schedule.slots.map((s, index) => {
                        const time = collectionSlotKey(s)
                        const Icon = [Sunrise, Sun, Sunset][index % 3]
                        return <button className={'btn flex-col items-start! ' + (slot === time ? 'selected' : '')}
                            key={time} aria-pressed={slot === time} disabled={!isCollectionSlotAvailable(schedule, date, time, clock)} onClick={() => setSlot(time)}>
                            <Icon size={18} aria-hidden="true" /><strong>{s.label}</strong><small>{time}</small>
                        </button>
                    })}
                </div>
            </div>
            <div>
                <div className="step"><b>3</b><h3>Nota rápida <span className="muted font-normal">(opcional)</span></h3></div>
                <div className="collection-choices mb-2">
                    {quickNotes.map(note => <button key={note} className="btn" onClick={() => setComment(text => text ? text + ' · ' + note : note)}>{note}</button>)}
                </div>
                <textarea className="control" value={comment} onChange={e => setComment(e.target.value)}
                    aria-label="Nota para el responsable" placeholder="Nota para el responsable" />
            </div>
            <button className="btn primary w-full min-h-[56px]" onClick={program} disabled={!member || !dateAllowed || !slotAllowed}>
                <MessageCircle size={19} aria-hidden="true" /><Check size={17} aria-hidden="true" />
                {reschedule ? 'Reprogramar y avisar por WhatsApp' : r.flow === 'reciclable' ? 'Asignar y enviar a WhatsApp' : 'Programar y avisar por WhatsApp'}
            </button>
            <p className="muted text-center">Demostración: los avisos se guardan como simulaciones.</p>
        </>}
        {r.status === 'programada' && !reschedule && <section className="space-y-4" aria-labelledby="waiting-confirmation">
            <div className="note space-y-2">
                <div className="flex items-center gap-2">
                    <Clock size={19} aria-hidden="true" /><h3 id="waiting-confirmation">Esperando confirmación del recolector</h3>
                </div>
                <p><strong>{assigned?.name ?? 'Sin responsable registrado'}</strong> · {r.date} · {r.time}</p>
                <p>El responsable informa {donation ? 'las unidades recibidas' : 'el peso aceptado'} con el código de la solicitud.</p>
            </div>
            {linkedDemo && <p className="muted">Envía la confirmación desde la vista Recolector.</p>}
            <div className="flex flex-wrap gap-2">
                {!linkedDemo && !r.backendId && <button className="btn" aria-expanded={closureMode === 'whatsapp-demo'}
                    onClick={() => chooseClosure('whatsapp-demo')}><MessageCircle size={18} aria-hidden="true" /> Simular respuesta</button>}
                <button className="btn" aria-expanded={closureMode === 'manual'}
                    onClick={() => chooseClosure('manual')}><Scale size={18} aria-hidden="true" /> Cierre manual de respaldo</button>
            </div>
            {closureMode && <form onSubmit={finish} className="rounded-xl border border-[#d4dfd4] p-3 space-y-3">
                {closureMode === 'whatsapp-demo' ? <>
                    <h3>Respuesta de WhatsApp simulada</h3>
                    <p className="muted">Remitente: {assigned?.name ?? 'Sin responsable'}. Ejemplo: <strong>{replyExample}</strong></p>
                    <label className="field">Mensaje recibido<input value={demoMessage}
                        placeholder={replyExample} onChange={e => { setDemoMessage(e.target.value); setError('') }} required /></label>
                </> : <>
                    <h3>Registrar cierre de respaldo</h3>
                    <label className="field">{quantityLabel}<input type="number" min="0" step={donation ? 1 : '0.01'}
                        max={donation ? r.units : 999_999.99} value={manualQuantity} required
                        onChange={e => { setManualQuantity(e.target.value); setError('') }} /></label>
                    <label className="field">Motivo del cierre manual<textarea value={manualReason} required
                        onChange={e => { setManualReason(e.target.value); setError('') }} /></label>
                    <label className="checkline"><input type="checkbox" checked={closureConfirmed}
                        onChange={e => setClosureConfirmed(e.target.checked)} required /> Confirmo la cantidad recibida.</label>
                </>}
                <button className="btn primary min-h-[56px]" type="submit">
                    {closureMode === 'whatsapp-demo' ? 'Procesar respuesta simulada' : 'Registrar cierre manual'}
                </button>
            </form>}
        </section>}
        {r.status === 'completada' && <div className="space-y-3">
            {r.confirmation && <div className="note space-y-1">
                <h3>{(donation ? r.receivedUnits : kgOf(r)) === 0 ? 'Cierre sin material aceptado' :
                    r.confirmation.source === 'whatsapp-demo' ? 'Confirmación simulada del recolector' : 'Cierre manual de respaldo'}</h3>
                <p>{r.confirmation.confirmedBy} · <time dateTime={r.confirmation.at}>
                    {new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' }).format(new Date(r.confirmation.at))}
                </time></p>
            </div>}
            <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl bg-[#e6efdf] p-4">
                    <small>{r.kind === 'donacion' ? 'Unidades recibidas' : 'Peso total registrado'}</small>
                    <p className="text-xl font-bold">{r.kind === 'donacion' ? r.receivedUnits : kgOf(r).toLocaleString('es-CO') + ' kg'}</p>
                </div>
                {r.flow === 'reciclable' && r.kind === 'residuo' && <div className="rounded-xl bg-[#e6efdf] p-4">
                    <small>Valor para el reciclador</small>
                    <p className="text-lg font-bold">{recyclerValuePending ? 'Pendiente de desglose' : money(valueOf(r))}</p>
                </div>}
            </div>
            {recyclerValuePending && <details className="rounded-xl border border-[#d4dfd4] p-3">
                <summary className="cursor-pointer font-semibold text-forest">Registrar desglose por material</summary>
                <div className="mt-3"><RecyclingBreakdown request={r} rates={data.rates} onSave={saveBreakdown} /></div>
            </details>}
            {r.lines?.map((line, index) => <p key={index} className="line">
                {line.material} · {line.kg.toLocaleString('es-CO')} kg {r.flow === 'reciclable' ? '· ' + money(line.rate) + '/kg' : ''}
            </p>)}
            <div className="note">
                <h3>EcoPuntos del habitante</h3>
                {r.ecoPoints === undefined ? <p>Este cierre no tiene EcoPuntos registrados.</p> : <>
                    <p className="text-xl font-bold text-forest">{r.ecoPoints.toLocaleString('es-CO')} EcoPuntos{r.backendId ? '' : ' de demostración'}</p>
                    {r.ecoPointRule && <p>Regla aplicada: {r.ecoPointRule.base.toLocaleString('es-CO')} base + {r.ecoPointRule.perKg.toLocaleString('es-CO')} por kg.</p>}
                    <p>Cálculo parametrizable sujeto a validación FSD.</p>
                </>}
            </div>
        </div>}
        {r.rejected && r.status !== 'programada' && <p className="note">Material rechazado / motivo: {r.rejected}</p>}{error && <p className="error" role="alert">{error}</p>}
        <details className="collection-disclosure">
            <summary>Seguimiento y avisos</summary>
            <div className="collection-disclosure-body space-y-2">
                {r.backendId && <Avisos key={r.backendId} solicitud={r.backendId} />}
                {r.history.map((entry, index) => <p key={index} className="line">
                    <CheckCircle2 size={15} aria-hidden="true" />{entry}
                </p>)}
                {!r.backendId && data.messages.filter(message => message.requestId === r.id).map(message => <div key={message.id} className="note">
                    <strong>{message.direction === 'in' ? 'De ' : 'Para '}{message.name} · WhatsApp simulado</strong>
                    <p>{message.text}</p>
                </div>)}
                <div className="flex flex-wrap items-end gap-2">
                    <label className="field flex-1 min-w-[150px]">Comentario interno
                        <input value={comment} onChange={e => setComment(e.target.value)} />
                    </label>
                    <button className="btn" disabled={!comment.trim()} onClick={() => {
                        patch({ note: comment }, 'Comentario: ' + comment)
                        notify('Comentario guardado.')
                    }}>Guardar comentario</button>
                </div>
            </div>
        </details>
    </section>
}
