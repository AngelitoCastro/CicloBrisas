import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, CalendarDays, CheckCheck, ClipboardList, Clock3, Leaf, MessageCircle, Recycle, RotateCcw, Send, Truck, UserRound, Wallet } from 'lucide-react'
import { Badge, Brand } from '../components/UI'
import { closeCollection } from '../services/collectionClosure'
import { applyRequestUpdate } from '../services/requestUpdates'
import { createWhatsAppDemoData, createWhatsAppDemoRequest, getWhatsAppDemoExample } from '../services/whatsappDemoScenarios'
import { kgOf, type Data, type Flow, type Request, type Status } from '../types'
import Collections from './Collections'
import './WhatsAppDemo.css'

type Audience = 'resident' | 'coordinator' | 'collector'

const audiences = [
    { id: 'resident', name: 'Habitante', icon: UserRound },
    { id: 'coordinator', name: 'Coordinador', icon: ClipboardList },
    { id: 'collector', name: 'Recolector', icon: Truck },
] as const

const stages = [
    { name: 'Solicitud', icon: Clock3 },
    { name: 'Programación', icon: CalendarDays },
    { name: 'Confirmación', icon: CheckCheck },
] as const

const sessionKey = 'ecoconecta-whatsapp-recorrido-v1'
const balanceQuestion = '¿Cuál es mi saldo de EcoPuntos?'
const number = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 })
const dateText = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeZone: 'America/Bogota' })

function loadWorkspace(): Data {
    try {
        const saved = sessionStorage.getItem(sessionKey)
        if (saved) {
            const data = JSON.parse(saved) as Data | null
            if (data && Array.isArray(data.requests) && Array.isArray(data.messages) && Array.isArray(data.members) &&
                data.schedules && data.pointRules) return data
        }
    } catch {
        // The demonstration can continue in memory if browser storage is unavailable.
    }
    return createWhatsAppDemoData()
}

function stageOf(status?: Status) {
    if (status === 'completada') return 2
    if (status === 'programada') return 1
    return 0
}

function formatVisit(request: Request) {
    if (!request.date) return ''
    return dateText.format(new Date(request.date + 'T12:00:00-05:00')) + (request.time ? ' · ' + request.time : '')
}

export default function WhatsAppDemoPage() {
    const [data, setData] = useState(loadWorkspace)
    const [audience, setAudience] = useState<Audience>('resident')
    const [flow, setFlow] = useState<Flow>('organico')
    const [reply, setReply] = useState<string | null>(null)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const transcript = useRef<HTMLDivElement>(null)
    const example = getWhatsAppDemoExample(flow)
    const request = data.requests.find(item => item.id === example.requestId)
    const assigned = data.members.find(member => member.id === request?.assignee && member.flow === flow)
    const step = stageOf(request?.status)
    const isResident = audience === 'resident'
    const personName = isResident ? example.residentName : assigned?.name
    const phone = isResident ? example.phone : assigned?.phone
    const visibleRequest = request && (isResident || assigned) ? request : undefined
    const messages = visibleRequest && phone ? data.messages.filter(
        message => message.requestId === visibleRequest.id && message.phone === phone,
    ) : []
    const completed = request?.status === 'completada'
    const balance = Math.round((example.previousBalance + (request?.ecoPoints ?? 0)) * 100) / 100
    const suggestedReply = 'LISTO ' + example.requestId + ' ' + number.format(example.kg)
    const balanceAsked = messages.some(message => message.direction === 'in' && message.text === balanceQuestion)

    useEffect(() => {
        try { sessionStorage.setItem(sessionKey, JSON.stringify(data)) } catch { /* The current tab remains usable. */ }
    }, [data])

    useEffect(() => {
        const body = transcript.current
        if (body) body.scrollTop = body.scrollHeight
    }, [messages.length, flow, audience])

    useEffect(() => {
        if (!notice) return
        const timer = window.setTimeout(() => setNotice(''), 4500)
        return () => window.clearTimeout(timer)
    }, [notice])

    function selectAudience(next: Audience) {
        setAudience(next)
        setError('')
    }

    function selectFlow(next: Flow) {
        if (flow === next) return
        setFlow(next)
        setReply(null)
        setError('')
    }

    function sendRequest() {
        const { request: incoming, message, receipt } = createWhatsAppDemoRequest(flow)
        const participant = { name: incoming.name, phone: incoming.phone }
        setData(current => current.requests.some(item => item.id === incoming.id) ? current :
            applyRequestUpdate(current, incoming, [{ ...participant, text: receipt }], { ...participant, text: message }))
    }

    function sendConfirmation(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        if (!request || !assigned) return
        const result = closeCollection(data, request, { source: 'whatsapp-demo', text: reply ?? suggestedReply, notifyCollector: true })
        if (!result.ok) {
            setError(result.error)
            return
        }
        setError('')
        setReply(null)
        setData(current => applyRequestUpdate(current, result.request, result.notifications, result.reply, 'programada'))
    }

    function askBalance() {
        if (request?.status !== 'completada' || balanceAsked) return
        const participant = { name: request.name, phone: request.phone }
        setData(current => {
            if (current.messages.some(message =>
                message.requestId === request.id && message.direction === 'in' && message.text === balanceQuestion,
            )) return current
            return applyRequestUpdate(current, request, [
                { ...participant, text: 'Tu saldo de demostración es de ' + number.format(balance) + ' EcoPuntos.' },
            ], { ...participant, text: balanceQuestion }, 'completada')
        })
    }

    function resetExample() {
        setData(current => ({
            ...current,
            requests: current.requests.filter(item => item.id !== example.requestId),
            messages: current.messages.filter(message => message.requestId !== example.requestId),
        }))
        setReply(null)
        setError('')
        setNotice('')
        setAudience('resident')
    }

    return <div className="demo-wa-page">
        <header className="demo-wa-header">
            <div className="demo-wa-shell demo-wa-header-inner">
                <Brand />
                <a href={import.meta.env.BASE_URL} className="btn demo-wa-back">
                    <ArrowLeft size={17} aria-hidden="true" /> Volver al acceso
                </a>
            </div>
        </header>

        <main className="demo-wa-shell demo-wa-main">
            <div className="demo-wa-intro">
                <div>
                    <h1>Una recolección por WhatsApp</h1>
                    <p>Cambia de rol para seguir la misma solicitud desde el chat hasta el panel.</p>
                </div>
                <p className="demo-wa-label"><MessageCircle size={17} aria-hidden="true" /> Demostración con datos ficticios</p>
            </div>

            <div className="demo-wa-controls">
                <fieldset>
                    <legend>Ver como</legend>
                    <div className="demo-wa-options">
                        {audiences.map(({ id, name, icon: Icon }) => (
                            <button key={id} className="btn" aria-pressed={audience === id} onClick={() => selectAudience(id)}>
                                <Icon size={17} aria-hidden="true" /> {name}
                            </button>
                        ))}
                    </div>
                </fieldset>
                <fieldset>
                    <legend>Tipo de recolección</legend>
                    <div className="demo-wa-options">
                        <button className="btn" aria-pressed={flow === 'organico'} onClick={() => selectFlow('organico')}>
                            <Leaf size={17} aria-hidden="true" /> Huerta
                        </button>
                        <button className="btn" aria-pressed={flow === 'reciclable'} onClick={() => selectFlow('reciclable')}>
                            <Recycle size={17} aria-hidden="true" /> Reciclaje
                        </button>
                    </div>
                </fieldset>
                {(completed || request?.status === 'rechazada') && <button className="btn demo-wa-reset" onClick={resetExample}>
                    <RotateCcw size={16} aria-hidden="true" /> Reiniciar este ejemplo
                </button>}
            </div>

            <ol className="demo-wa-stages" aria-label="Progreso de la solicitud">
                {stages.map(({ name, icon: Icon }, index) => <li key={name}>
                    <span className="demo-wa-stage" aria-current={step === index ? 'step' : undefined}>
                        <span className="demo-wa-stage-icon"><Icon size={19} aria-hidden="true" /></span>
                        <span>{name}</span>
                    </span>
                </li>)}
            </ol>

            {audience === 'coordinator' ? <div className="demo-wa-coordinator">
                <Collections key={flow} flow={flow} data={data} linkedDemo
                    update={(next, notifications, incoming, expectedStatus) => setData(current =>
                        applyRequestUpdate(current, next, notifications, incoming, expectedStatus))}
                    notify={setNotice}
                    onSaveRecord={record => setData(current => ({ ...current, intakeRecords: [record, ...current.intakeRecords] }))} />
            </div> : <div className="demo-wa-workspace">
                <section className="demo-wa-chat" aria-labelledby="demo-wa-chat-title">
                    <header className="demo-wa-chat-header">
                        <span className="demo-wa-chat-icon"><MessageCircle size={21} aria-hidden="true" /></span>
                        <div>
                            <h2 id="demo-wa-chat-title">Conversación con EcoConecta</h2>
                            <p>{personName ? 'Vista de ' + personName : 'Vista del recolector'}</p>
                        </div>
                        {visibleRequest && <span className="demo-wa-chat-status" role="status"><Badge status={visibleRequest.status} /></span>}
                    </header>

                    <div className="demo-wa-transcript" ref={transcript} tabIndex={0} aria-label="Mensajes de ejemplo">
                        {messages.length ? <ol>
                            {messages.map(message => <li key={message.id}
                                className={'demo-wa-message ' + (message.direction === 'in' ? 'person' : 'system')}>
                                <p className="demo-wa-author">{message.direction === 'in' ? personName : 'EcoConecta'}</p>
                                <p className="demo-wa-text">{message.text}</p>
                                <p className="demo-wa-time">{message.at}</p>
                            </li>)}
                        </ol> : <div className="demo-wa-chat-empty">
                            <Clock3 size={28} aria-hidden="true" />
                            <p>{isResident ? 'Solicita una recolección de ' + example.material + ' para iniciar el recorrido.' :
                                'El recolector recibe su primer mensaje cuando el coordinador programa la visita.'}</p>
                        </div>}
                    </div>

                    <footer className="demo-wa-chat-footer">
                        {isResident && !request && <button className="btn primary" onClick={sendRequest}>
                            <Send size={16} aria-hidden="true" /> Solicitar recolección
                        </button>}
                        {isResident && request?.status === 'pendiente' && <button className="btn" onClick={() => selectAudience('coordinator')}>
                            <ClipboardList size={16} aria-hidden="true" /> Abrir panel del coordinador
                        </button>}
                        {isResident && request?.status === 'autorizada' && <button className="btn" onClick={() => selectAudience('coordinator')}>
                            <CalendarDays size={16} aria-hidden="true" /> Ir a programación
                        </button>}
                        {isResident && request?.status === 'programada' && <button className="btn" onClick={() => selectAudience('collector')}>
                            <Truck size={16} aria-hidden="true" /> Ver conversación del recolector
                        </button>}
                        {isResident && completed && !balanceAsked && <button className="btn" onClick={askBalance}>
                            <Wallet size={16} aria-hidden="true" /> Consultar saldo
                        </button>}
                        {!isResident && request?.status === 'programada' && assigned && <form className="demo-wa-reply" onSubmit={sendConfirmation}>
                            <label className="field">
                                Confirmación del recolector
                                <input value={reply ?? suggestedReply} required aria-describedby="demo-wa-reply-example"
                                    onChange={event => { setReply(event.target.value); setError('') }} />
                                <span id="demo-wa-reply-example" className="muted">Ejemplo: {suggestedReply}</span>
                            </label>
                            <button type="submit" className="btn primary"><Send size={16} aria-hidden="true" /> Simular respuesta</button>
                            {error && <p role="alert" className="error">{error}</p>}
                        </form>}
                        {!isResident && completed && <button className="btn" onClick={() => selectAudience('resident')}>
                            <UserRound size={16} aria-hidden="true" /> Ver resultado del habitante
                        </button>}
                        {!messages.length && !isResident && <button className="btn" onClick={() => selectAudience(request ? 'coordinator' : 'resident')}>
                            {request ? 'Abrir panel del coordinador' : 'Ir a Habitante'}
                        </button>}
                        {isResident && request?.status === 'rechazada' && <p className="muted">Puedes reiniciar este ejemplo para probar otra vez.</p>}
                        {isResident && completed && balanceAsked && <p className="muted">Saldo consultado en el chat.</p>}
                    </footer>
                </section>

                <aside className="demo-wa-summary" aria-labelledby="demo-wa-summary-title">
                    <div className="demo-wa-summary-title">
                        <h2 id="demo-wa-summary-title">Detalle de la solicitud</h2>
                        {visibleRequest && <strong>{visibleRequest.id}</strong>}
                    </div>
                    {visibleRequest ? <dl>
                        <div><dt>Solicita</dt><dd>{visibleRequest.name}</dd></div>
                        {assigned && visibleRequest.date && <>
                            <div><dt>Responsable</dt><dd>{assigned.name}</dd></div>
                            <div><dt>Visita</dt><dd>{formatVisit(visibleRequest)}</dd></div>
                            {!isResident && <div><dt>Dirección de recogida</dt><dd>{visibleRequest.address}</dd></div>}
                        </>}
                        {completed && <div><dt>Peso confirmado</dt><dd>{number.format(kgOf(visibleRequest))} kg</dd></div>}
                    </dl> : <p className="demo-wa-summary-note">
                        {isResident ? 'El código aparecerá aquí cuando hagas la solicitud.' : 'Los datos de la visita aparecerán al programar la recolección.'}
                    </p>}
                    {isResident && completed && <div className="demo-wa-points">
                        <p><Wallet size={19} aria-hidden="true" /> Saldo de EcoPuntos</p>
                        <strong>{number.format(balance)}</strong>
                        <p>Ganaste {number.format(request.ecoPoints ?? 0)} en esta recolección.</p>
                        <small>Cálculo parametrizable sujeto a validación FSD.</small>
                    </div>}
                </aside>
            </div>}
        </main>
        {notice && <div className="toast" role="status">{notice}</div>}
    </div>
}
