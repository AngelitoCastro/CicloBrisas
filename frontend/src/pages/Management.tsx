import {useState,type FormEvent} from 'react'
import {Users,Plus,CalendarDays,BookOpen,MessageCircle,Download,Gift,Settings,Trash2,Award} from 'lucide-react'
import {type Data,type Flow,type Role,type Member,type Knowledge,type Request,dayNames,flows,materials,kgOf,valueOf,isRecyclerValuePending,money,statuses,uid,isoDate} from '../types'
import {Badge,Empty,Modal} from '../components/UI'
import RecyclingRates from '../components/RecyclingRates'
import { pointRuleGenerators } from '../services/pointRules'
type Props={data:Data;setData:(fn:(d:Data)=>Data)=>void;notify:(s:string)=>void;flow?:Flow}
export function Team({ data, setData, notify, role }: Omit<Props, 'flow'> & { role: Role }) {
    const canManage = role === 'admin'
    const flow = role === 'huerta' ? 'organico' : 'reciclable'
    const [open, setOpen] = useState(false)
    const [editing, setEditing] = useState<Member | null>(null)
    const [chosen, setChosen] = useState<Flow>('organico')
    const members = canManage ? data.members : data.members.filter(member => member.flow === flow)

    function openEditor(member: Member | null) {
        if (!canManage) return
        setEditing(member)
        setChosen(member?.flow ?? 'organico')
        setOpen(true)
    }

    function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        if (!canManage) return
        const fields = new FormData(event.currentTarget)
        const member: Member = {
            id: editing?.id ?? uid(),
            name: String(fields.get('name') ?? '').trim(),
            phone: String(fields.get('phone') ?? '').trim(),
            group: String(fields.get('group') ?? '').trim(),
            flow: editing?.flow ?? chosen,
            active: editing?.active ?? true,
        }
        if (!member.name || !member.phone || !member.group) return
        setData(current => ({
            ...current,
            members: editing ? current.members.map(item => item.id === member.id ? member : item) : [...current.members, member],
        }))
        setOpen(false)
        notify('Miembro guardado.')
    }

    function toggleAvailability(id: string) {
        if (!canManage) return
        setData(current => ({
            ...current,
            members: current.members.map(member => member.id === id ? { ...member, active: !member.active } : member),
        }))
        notify('Disponibilidad actualizada.')
    }

    return <>
        <div className="flex justify-between flex-wrap gap-3 mb-5">
            <div>
                <h1>Equipo de trabajo</h1>
                <p className="muted">{canManage ? 'Gestiona responsables y grupos de recolección.' : 'Consulta los miembros y la disponibilidad de tu equipo.'}</p>
            </div>
            {canManage && <button className="btn primary" onClick={() => openEditor(null)}>
                <Plus size={18} aria-hidden="true" /> Agregar miembro
            </button>}
        </div>

        {members.length === 0 ? <div className="panel"><Empty>No hay miembros registrados.</Empty></div> :
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {members.map(member => <section className="panel p-5 space-y-3" key={member.id}>
                    <div className="flex items-center gap-3">
                        <span className="avatar" aria-hidden="true">{member.name.split(' ').map(word => word[0]).slice(0, 2).join('')}</span>
                        <div className="flex-1 min-w-0">
                            <h3>{member.name}</h3>
                            <p className="muted">{member.group} · {member.flow === 'organico' ? 'Huertero' : 'Reciclador'}</p>
                        </div>
                        <span className="status">{member.active ? 'Activo' : 'Inactivo'}</span>
                    </div>
                    <p className="line"><MessageCircle size={16} aria-hidden="true" />{member.phone}</p>
                    <p className="muted">{data.requests.filter(request => request.assignee === member.id && request.status === 'programada').length} solicitudes programadas</p>
                    {canManage && <div className="flex flex-wrap gap-2">
                        <button className="btn" onClick={() => openEditor(member)}>Editar</button>
                        <button className="btn" onClick={() => toggleAvailability(member.id)}>{member.active ? 'Desactivar' : 'Activar'}</button>
                    </div>}
                </section>)}
            </div>}

        {canManage && open && <Modal title={editing ? 'Editar miembro' : 'Agregar miembro'} onClose={() => setOpen(false)}>
            <form className="form-grid" onSubmit={save}>
                <label className="field full">Nombre<input name="name" defaultValue={editing?.name} required /></label>
                <label className="field">Teléfono<input name="phone" type="tel" defaultValue={editing?.phone} required /></label>
                <label className="field">Grupo<input name="group" defaultValue={editing?.group} required /></label>
                <label className="field full">Categoría
                    <select disabled={Boolean(editing)} value={chosen} onChange={event => setChosen(event.target.value as Flow)}>
                        {Object.entries(flows).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
                    </select>
                </label>
                <button className="btn primary full" type="submit">Guardar</button>
            </form>
        </Modal>}
    </>
}

export function SettingsPage({ data, setData, notify, flow }: Props & { flow: Flow }) {
    const [draft, setDraft] = useState(() => structuredClone(data.schedules[flow]))
    const [error, setError] = useState('')

    function updateSlot(index: number, field: 'label' | 'start' | 'end', value: string) {
        setDraft(current => ({
            ...current,
            slots: current.slots.map((slot, position) => position === index ? { ...slot, [field]: value } : slot),
        }))
    }

    function saveSchedule(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        if (!draft.days.length || !draft.slots.length || draft.slots.some(slot => !slot.label.trim() || !slot.start || !slot.end || slot.start >= slot.end)) {
            setError('Define al menos un día y una franja válida. La hora final debe ser posterior.')
            return
        }
        setError('')
        setData(current => ({ ...current, schedules: { ...current.schedules, [flow]: structuredClone(draft) } }))
        notify('Horario guardado.')
    }

    return <>
        <h1>Horarios y métricas</h1>
        <p className="muted mb-5">Calendario y valores vigentes de tu actividad.</p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <section className="panel min-w-0" aria-labelledby="collection-schedule">
                <header className="panel-head">
                    <CalendarDays aria-hidden="true" /><h2 id="collection-schedule">Días y franjas de recolección</h2>
                </header>
                <form className="panel-body space-y-4" onSubmit={saveSchedule}>
                    <div className="flex flex-wrap gap-2" role="group" aria-label="Días de recolección">
                        {dayNames.map((day, index) => <button key={day} type="button"
                            className={'btn ' + (draft.days.includes(index) ? 'selected' : '')}
                            aria-pressed={draft.days.includes(index)}
                            onClick={() => setDraft(current => ({
                                ...current,
                                days: current.days.includes(index)
                                    ? current.days.filter(item => item !== index)
                                    : [...current.days, index].sort((left, right) => left - right),
                            }))}>{day}</button>)}
                    </div>
                    {draft.slots.map((slot, index) => <div className="grid grid-cols-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto] gap-2 items-end" key={index}>
                        <label className="field col-span-2 sm:col-span-1 min-w-0">Nombre
                            <input value={slot.label} onChange={event => updateSlot(index, 'label', event.target.value)} />
                        </label>
                        {(['start', 'end'] as const).map(field => <label className="field min-w-0" key={field}>
                            {field === 'start' ? 'Inicio' : 'Fin'}
                            <input type="time" value={slot[field]} onChange={event => updateSlot(index, field, event.target.value)} />
                        </label>)}
                        <button type="button" className="icon-btn justify-self-start" aria-label={'Quitar franja ' + (index + 1)}
                            onClick={() => setDraft(current => ({ ...current, slots: current.slots.filter((_, position) => position !== index) }))}>
                            <Trash2 size={18} aria-hidden="true" />
                        </button>
                    </div>)}
                    <button type="button" className="btn" onClick={() => setDraft(current => ({
                        ...current,
                        slots: [...current.slots, { label: 'Nueva franja', start: '08:00', end: '10:00' }],
                    }))}><Plus size={18} aria-hidden="true" /> Añadir franja</button>
                    {error && <p className="error" role="alert">{error}</p>}
                    <button className="btn primary w-full" type="submit">Guardar horario</button>
                    <p className="note">Los cambios aplican a las nuevas programaciones. Las solicitudes ya programadas conservan su horario.</p>
                </form>
            </section>
            <div className="min-w-0 space-y-4 self-start">
                <CollectionPointRates rules={data.pointRules[flow]} />
                {flow === 'reciclable' && <RecyclingRates rates={data.rates} />}
            </div>
        </div>
    </>
}



function CollectionPointRates({ rules }: { rules: Data['pointRules'][Flow] }) {
    return <section className="panel" aria-labelledby="collection-point-rules">
        <header className="panel-head">
            <Award aria-hidden="true" /><h2 id="collection-point-rules">EcoPuntos vigentes</h2>
        </header>
        <div className="panel-body space-y-3">
            <div className="table-wrap">
                <table className="w-full" aria-labelledby="collection-point-rules">
                    <thead>
                        <tr className="text-left">
                            <th scope="col" className="whitespace-normal">Tipo de solicitante</th>
                            <th scope="col" className="whitespace-normal text-right">EcoPuntos por kg</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pointRuleGenerators.map(generator => <tr key={generator}>
                            <th scope="row" className="whitespace-normal bg-transparent font-normal">
                                {generator === 'Hogar' ? 'Hogar' : 'Unidad productiva'}
                            </th>
                            <td className="text-right font-semibold tabular-nums">
                                {rules[generator].perKg.toLocaleString('es-CO', { maximumFractionDigits: 2 })}
                            </td>
                        </tr>)}
                    </tbody>
                </table>
            </div>
            <p className="note">
                Administración define las reglas. Los EcoPuntos se aplican al confirmar el peso.
                {' '}Cálculo parametrizable sujeto a validación FSD.
            </p>
        </div>
    </section>
}

export function Reports({ data, flow }: Props) {
    const [category, setCategory] = useState('all')
    const [material, setMaterial] = useState('all')
    const [start, setStart] = useState('')
    const [end, setEnd] = useState('')
    const [person, setPerson] = useState('all')
    const [min, setMin] = useState('')

    const rows = data.requests.filter(request =>
        (!flow || request.flow === flow) &&
        (category === 'all' || request.flow === category) &&
        (material === 'all' || request.lines?.some(line => line.material === material)) &&
        (person === 'all' || request.assignee === person) &&
        (!start || (request.date || request.created) >= start) &&
        (!end || (request.date || request.created) <= end) &&
        (!min || kgOf(request) >= Number(min)))
    const complete = rows.filter(request => request.status === 'completada')
    const total = complete.reduce((sum, request) => sum + kgOf(request), 0)
    const recycled = complete.filter(request => request.flow === 'reciclable' && request.kind === 'residuo')
    const pendingCount = recycled.filter(isRecyclerValuePending).length
    const value = recycled.reduce((sum, request) => sum + valueOf(request), 0)
    const allMaterials = [...materials.organico, ...materials.reciclable]
    const materialOptions = flow ? materials[flow] : category === 'all' ? allMaterials : materials[category as Flow]
    const materialWeights = new Map<string, number>()
    for (const request of complete) {
        for (const line of request.lines ?? []) {
            materialWeights.set(line.material, (materialWeights.get(line.material) ?? 0) + line.kg)
        }
    }
    const breakdownWeight = [...materialWeights.values()].reduce((sum, kg) => sum + kg, 0)
    const unclassifiedWeight = Number((total - breakdownWeight).toFixed(2))
    const formatKg = (kg: number) => kg.toLocaleString('es-CO', { maximumFractionDigits: 2 }) + ' kg'

    function download() {
        const quote = (value: unknown) => '"' + String(value ?? '').replace(/^[=+\-@]/, "'$&").replaceAll('"', '""') + '"'
        const entries = rows.map(request => {
            const value = recyclerValueForReport(request)
            return [
                request.id, flows[request.flow], request.name, statuses[request.status],
                request.date || request.created, kgOf(request), typeof value === 'number' ? value : '',
                request.ecoPoints ?? '', value === 'pending' ? 'Pendiente de desglose' : value === null ? '' : 'Calculado',
            ]
        })
        const header = ['Código', 'Categoría', 'Solicitante', 'Estado', 'Fecha', 'Peso kg',
            'Valor reciclador COP', 'Puntos', 'Estado del valor para reciclador']
        const csv = [header, ...entries].map(row => row.map(quote).join(';')).join('\r\n')
        const url = URL.createObjectURL(new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }))
        const link = document.createElement('a')
        link.href = url
        link.download = 'ecoconecta-reporte.csv'
        link.click()
        URL.revokeObjectURL(url)
    }

    return <>
        <div className="flex justify-between flex-wrap gap-3 mb-5">
            <div><h1>{flow ? 'Historial y reportes' : 'Resumen administrativo'}</h1>
                <p className="muted">Consulta registros, materiales y resultados de la operación.</p>
            </div>
            <button className="btn dark" onClick={download}><Download size={18} aria-hidden="true" /> Exportar CSV</button>
        </div>
        <div className="panel p-4 mb-4 grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
            {!flow && <label className="field">Categoría<select value={category} onChange={event => {
                setCategory(event.target.value)
                setMaterial('all')
            }}>
                <option value="all">Todas</option>
                {Object.entries(flows).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>}
            <label className="field">Material<select value={material} onChange={event => setMaterial(event.target.value)}>
                <option value="all">Todos</option>
                {materialOptions.map(name => <option key={name}>{name}</option>)}
            </select></label>
            <label className="field">Responsable<select value={person} onChange={event => setPerson(event.target.value)}>
                <option value="all">Todos</option>
                {data.members.filter(member => !flow || member.flow === flow).map(member =>
                    <option key={member.id} value={member.id}>{member.name}</option>)}
            </select></label>
            <label className="field">Desde<input type="date" value={start} onChange={event => setStart(event.target.value)} /></label>
            <label className="field">Hasta<input type="date" value={end} onChange={event => setEnd(event.target.value)} /></label>
            <label className="field">Mínimo kg<input type="number" min="0" value={min} onChange={event => setMin(event.target.value)} /></label>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
            {[
                { label: 'Solicitudes', text: rows.length },
                { label: 'Peso recibido', text: formatKg(total) },
                { label: 'Valor calculado para recicladores', text: money(value) },
                { label: 'Donaciones recibidas', text: complete.reduce((sum, request) => sum + (request.receivedUnits ?? 0), 0) + ' uds.' },
            ].map(item => <div key={item.label} className="panel p-4">
                <small>{item.label}</small><p className="text-2xl font-extrabold text-[#164b38] mt-1">{item.text}</p>
                {item.label === 'Valor calculado para recicladores' && pendingCount > 0 &&
                    <p className="muted mt-1">{pendingCount} {pendingCount === 1 ? 'recolección pendiente' : 'recolecciones pendientes'} de desglose.</p>}
            </div>)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
            <div className="panel p-5">
                <h2>Material recuperado</h2>
                <div className="space-y-3 mt-4">
                    {[...materialWeights].map(([name, weight]) => weight > 0 && <div key={name}>
                        <div className="flex justify-between text-sm mb-1"><span>{name}</span><strong>{formatKg(weight)}</strong></div>
                        <div className="h-2 rounded bg-[#edf1e9]">
                            <div className="bg-[#629b45] h-2 rounded" style={{ width: (weight / breakdownWeight * 100) + '%' }} />
                        </div>
                    </div>)}
                    {breakdownWeight === 0 && <Empty>Aún no hay pesos por material para este filtro.</Empty>}
                    {unclassifiedWeight > 0 && <p className="muted">{formatKg(unclassifiedWeight)} confirmados sin desglose por material.</p>}
                </div>
            </div>
            <div className="panel p-5">
                <h2>Puntos comunitarios</h2>
                <p className="text-2xl font-bold mt-2">{complete.reduce((sum, request) => sum + (request.ecoPoints ?? 0), 0).toLocaleString('es-CO')} EcoPuntos de demostración</p>
                <p className="note mt-3">Incluye cierres de Huerta y Reciclaje con peso aceptado. Cálculo parametrizable sujeto a validación FSD.</p>
            </div>
        </div>
        <div className="panel table-wrap">
            <table>
                <thead><tr>{['Solicitud', 'Solicitante', 'Categoría', 'Estado', 'Peso aceptado', 'Valor reciclador', 'Responsable'].map(label =>
                    <th key={label} scope="col">{label}</th>)}</tr></thead>
                <tbody>{rows.map(request => {
                    const value = recyclerValueForReport(request)
                    return <tr key={request.id}>
                        <td>{request.id}</td><td>{request.name}</td><td>{flows[request.flow]}</td>
                        <td><Badge status={request.status} /></td><td>{formatKg(kgOf(request))}</td>
                        <td>{value === 'pending' ? <span className="status">Pendiente de desglose</span> : value === null ? '—' : money(value)}</td>
                        <td>{data.members.find(member => member.id === request.assignee)?.name || '—'}</td>
                    </tr>
                })}</tbody>
            </table>
            {!rows.length && <Empty>No hay registros con estos filtros.</Empty>}
        </div>
    </>
}

function recyclerValueForReport(request: Request) {
    if (request.flow !== 'reciclable' || request.kind !== 'residuo' || request.status !== 'completada') return null
    return isRecyclerValuePending(request) ? 'pending' : valueOf(request)
}
export function KnowledgePage({data,setData,notify}:Props){const [edit,setEdit]=useState<Knowledge|null>(null);return <><div className="flex justify-between gap-3 flex-wrap mb-5"><div><h1>Base de conocimiento</h1><p className="muted">Prepara las respuestas autorizadas del futuro asistente.</p></div><button className="btn primary" onClick={()=>setEdit({id:uid(),question:'',answer:''})}><Plus size={18}/> Nueva respuesta</button></div><div className="panel p-5 mb-4"><p className="font-semibold">El asistente no debe inventar tarifas, puntos ni asignaciones.</p><p className="muted mt-1">Esta base se almacena localmente. La IA y la API de WhatsApp aún no están conectadas.</p></div><div className="space-y-3">{data.knowledge.map(k=><div className="panel p-5" key={k.id}><h3>{k.question}</h3><p className="mt-2 text-sm text-[#506557]">{k.answer}</p><div className="flex gap-2 mt-3"><button className="btn" onClick={()=>setEdit(k)}>Editar</button><button className="btn danger" onClick={()=>{setData(d=>({...d,knowledge:d.knowledge.filter(x=>x.id!==k.id)}));notify('Respuesta eliminada.')}}>Eliminar</button></div></div>)}</div>{edit&&<Modal title="Respuesta autorizada" onClose={()=>setEdit(null)}><form className="space-y-3" onSubmit={e=>{e.preventDefault();if(!edit.question.trim()||!edit.answer.trim())return;setData(d=>({...d,knowledge:d.knowledge.some(x=>x.id===edit.id)?d.knowledge.map(x=>x.id===edit.id?edit:x):[...d.knowledge,edit]}));setEdit(null);notify('Respuesta guardada.')}}><label className="field">Pregunta<input required value={edit.question} onChange={e=>setEdit({...edit,question:e.target.value})}/></label><label className="field">Respuesta<textarea required value={edit.answer} onChange={e=>setEdit({...edit,answer:e.target.value})}/></label><button className="btn primary w-full">Guardar respuesta</button></form></Modal>}</>}
export function Training(){return <><h1>Aprende a usar EcoConecta</h1><p className="muted mb-5">Guías cortas para las actividades diarias del coordinador.</p><div className="grid grid-cols-1 md:grid-cols-2 gap-4">{[{t:'Revisar y autorizar una solicitud',steps:['Entra a Recolecciones y selecciona una solicitud pendiente.','Lee la descripción y revisa la foto si existe.','Solicita información adicional si hace falta.','Confirma la revisión y autoriza o rechaza con motivo.']},{t:'Programar y avisar al equipo',steps:['Abre una solicitud autorizada.','Elige al responsable, fecha y franja disponible.','Agrega una nota y pulsa Programar y avisar por WhatsApp.','Consulta los avisos simulados en el seguimiento de la solicitud.']},{t:'Registrar el pesaje',steps:['Selecciona una solicitud programada.','Registra los materiales realmente aceptados y sus pesos.','Anota el material no aceptado.','Confirma el registro. En reciclaje se calcula el valor por kg para el reciclador.']},{t:'Gestionar horarios y seguimiento',steps:['Abre Métricas para consultar los puntos y ajustar los días y franjas de tu actividad.','Abre el seguimiento de una solicitud para revisar sus avisos.','Consulta la disponibilidad de los responsables en Equipo. Administración puede agregar o desactivar miembros.','En Historial consulta y exporta registros.']}].map((x,i)=><section className="panel p-5" key={x.t}><div className="flex items-center gap-3 mb-3"><span className="mini-icon"><BookOpen/></span><h2>{x.t}</h2></div><ol className="list-decimal pl-5 space-y-2 text-sm text-[#465b4c]">{x.steps.map(s=><li key={s}>{s}</li>)}</ol></section>)}</div></>}
