import {useState,type FormEvent} from 'react'
import {Users,Plus,CalendarDays,BookOpen,MessageCircle,Send,Download,Scale,Gift,Settings,Trash2} from 'lucide-react'
import {type Data,type Flow,type Member,type Knowledge,type Request,dayNames,flows,materials,kgOf,valueOf,isRecyclerValuePending,money,statuses,uid,isoDate} from '../types'
import {Badge,Empty,Modal} from '../components/UI'
type Props={data:Data;setData:(fn:(d:Data)=>Data)=>void;notify:(s:string)=>void;flow?:Flow}
export function Team({data,setData,notify,flow}:Props){const [open,setOpen]=useState(false);const [editing,setEditing]=useState<Member|null>(null);const [chosen,setChosen]=useState<Flow>(flow||'organico');const list=data.members.filter(m=>!flow||m.flow===flow);function save(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);const m:Member={id:editing?.id||uid(),name:String(f.get('name')).trim(),phone:String(f.get('phone')).trim(),group:String(f.get('group')).trim(),flow:chosen,active:editing?.active??true};if(!m.name||!m.phone||!m.group)return;setData(d=>({...d,members:editing?d.members.map(x=>x.id===m.id?m:x):[...d.members,m]}));setOpen(false);notify('Miembro guardado.')}return <><div className="flex justify-between flex-wrap gap-3 mb-5"><div><h1>Equipo de trabajo</h1><p className="muted">Gestiona responsables y grupos de recolección.</p></div><button className="btn primary" onClick={()=>{setEditing(null);setChosen(flow||'organico');setOpen(true)}}><Plus size={18}/> Agregar miembro</button></div><div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">{list.map(m=><section className="panel p-5 space-y-3" key={m.id}><div className="flex items-center gap-3"><span className="avatar">{m.name.split(' ').map(x=>x[0]).slice(0,2).join('')}</span><div className="flex-1"><h3>{m.name}</h3><p className="muted">{m.group} · {m.flow==='organico'?'Huertero':'Reciclador'}</p></div><span className="status">{m.active?'Activo':'Inactivo'}</span></div><p className="line"><MessageCircle size={16}/>{m.phone}</p><p className="muted">{data.requests.filter(r=>r.assignee===m.id&&r.status==='programada').length} solicitudes programadas</p><div className="flex flex-wrap gap-2"><button className="btn" onClick={()=>{setEditing(m);setChosen(m.flow);setOpen(true)}}>Editar</button><button className="btn" onClick={()=>{setData(d=>({...d,members:d.members.map(x=>x.id===m.id?{...x,active:!x.active}:x)}));notify('Disponibilidad actualizada.')}}>{m.active?'Desactivar':'Activar'}</button></div></section>)}</div>{open&&<Modal title={editing?'Editar miembro':'Agregar miembro'} onClose={()=>setOpen(false)}><form className="form-grid" onSubmit={save}><label className="field full">Nombre<input name="name" defaultValue={editing?.name} required/></label><label className="field">Teléfono<input name="phone" type="tel" defaultValue={editing?.phone} required/></label><label className="field">Grupo<input name="group" defaultValue={editing?.group} required/></label><label className="field full">Categoría<select disabled={!!flow||!!editing} value={chosen} onChange={e=>setChosen(e.target.value as Flow)}>{Object.entries(flows).map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label><button className="btn primary full">Guardar</button></form></Modal>}</>}
export function SettingsPage({data,setData,notify,flow}:Props){const [chosen,setChosen]=useState<Flow>(flow||'organico');const [draft,setDraft]=useState(()=>structuredClone(data.schedules[flow||'organico']));const [rates,setRates]=useState({...data.rates});const [error,setError]=useState('');return <><h1>Horarios y configuración</h1><p className="muted mb-5">Calendarios independientes para cada actividad.</p><div className="grid grid-cols-1 lg:grid-cols-2 gap-4"><section className="panel"><div className="panel-head"><CalendarDays/><h2>Días y franjas de recolección</h2></div><div className="panel-body space-y-4">{!flow&&<label className="field">Categoría<select value={chosen} onChange={e=>{const f=e.target.value as Flow;setChosen(f);setDraft(structuredClone(data.schedules[f]))}}>{Object.entries(flows).map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></label>}<div className="flex flex-wrap gap-2">{dayNames.map((n,i)=><button key={n} className={'btn '+(draft.days.includes(i)?'selected':'')} onClick={()=>setDraft(d=>({...d,days:d.days.includes(i)?d.days.filter(x=>x!==i):[...d.days,i].sort()}))}>{n}</button>)}</div>{draft.slots.map((s,i)=><div className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 items-end" key={i}><label className="field">Nombre<input value={s.label} onChange={e=>setDraft(d=>({...d,slots:d.slots.map((x,j)=>j===i?{...x,label:e.target.value}:x)}))}/></label>{(['start','end'] as const).map(k=><label className="field" key={k}>{k==='start'?'Inicio':'Fin'}<input type="time" value={s[k]} onChange={e=>setDraft(d=>({...d,slots:d.slots.map((x,j)=>j===i?{...x,[k]:e.target.value}:x)}))}/></label>)}<button className="icon-btn" aria-label="Quitar horario" onClick={()=>setDraft(d=>({...d,slots:d.slots.filter((_,j)=>j!==i)}))}><Trash2 size={18}/></button></div>)}<button className="btn" onClick={()=>setDraft(d=>({...d,slots:[...d.slots,{label:'Nueva franja',start:'08:00',end:'10:00'}]}))}><Plus size={18}/> Añadir franja</button>{error&&<p className="error">{error}</p>}<button className="btn primary w-full" onClick={()=>{if(!draft.days.length||!draft.slots.length||draft.slots.some(s=>!s.label.trim()||!s.start||!s.end||s.start>=s.end)){setError('Define al menos un día y una franja válida. La hora final debe ser posterior.');return}setError('');setData(d=>({...d,schedules:{...d.schedules,[chosen]:structuredClone(draft)}}));notify('Horario guardado.')}}>Guardar horario</button><p className="note">Los cambios aplican a las nuevas programaciones. Las solicitudes ya programadas conservan su horario.</p></div></section>{flow!=='organico'&&<section className="panel"><div className="panel-head"><Scale/><h2>Tarifas para el reciclador</h2></div><div className="panel-body space-y-3"><p className="muted">Valor por kilogramo aceptado. No representa un pago al habitante.</p>{materials.reciclable.map(m=><label className="field" key={m}>{m} · COP/kg<input type="number" min="0" step="0.01" value={rates[m]??0} onChange={e=>setRates(r=>({...r,[m]:Number(e.target.value)}))}/></label>)}<button className="btn primary w-full" onClick={()=>{if(Object.values(rates).some(n=>!Number.isFinite(n)||n<0)){notify('Ingresa tarifas válidas.');return}setData(d=>({...d,rates}));notify('Tarifas guardadas.')}}>Guardar tarifas</button><p className="note">Tarifa inicial de demostración: $80 COP/kg. Se conserva la tarifa usada en cada pesaje.</p></div></section>}</div></>}
export function Messages({data,setData,notify,flow}:Props){const [picked,setPicked]=useState(''),[text,setText]=useState('');const visible=data.messages.filter(m=>!flow||m.flow===flow);const contacts=Array.from(new Map(visible.map(m=>[m.flow+'|'+m.phone,m])).values());const selected=contacts.find(m=>m.flow+'|'+m.phone===picked)||contacts[0];const thread=selected?visible.filter(m=>m.phone===selected.phone&&m.flow===selected.flow):[];function send(){if(!selected||!text.trim())return;setData(d=>({...d,messages:[...d.messages,{id:uid(),flow:selected.flow,name:selected.name,phone:selected.phone,text:text.trim(),direction:'out',at:new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'}),requestId:selected.requestId}]}));setText('');notify('Mensaje guardado en la bandeja simulada.')}return <><h1>Mensajes de WhatsApp</h1><p className="muted mb-5">Conversaciones de habitantes y equipo · entorno simulado.</p><div className="split"><section className="panel p-3 space-y-2">{contacts.map(m=><button key={m.flow+'|'+m.phone} className={'request-card '+(m.phone===selected?.phone&&m.flow===selected?.flow?'selected':'')} onClick={()=>{setPicked(m.flow+'|'+m.phone);setText('')}}><h3>{m.name}</h3><small>{m.phone} · {m.requestId||'Conversación'}</small><p className="text-sm truncate mt-1">{m.text}</p></button>)}{!contacts.length&&<Empty>No hay conversaciones.</Empty>}</section><section className="panel"><div className="panel-head"><MessageCircle/><h2>{selected?.name||'Conversación'}</h2></div><div className="bg-[#e9eee5] p-4 space-y-3 min-h-[320px] max-h-[520px] overflow-auto">{thread.map(m=><div key={m.id} className={'p-3 rounded-xl max-w-[87%] text-sm shadow-sm '+(m.direction==='out'?'ml-auto bg-[#d9f1ce]':'bg-white')}><p className="whitespace-pre-wrap">{m.text}</p><small className="block text-right mt-2">{m.at}{m.direction==='out'?' · Simulado':''}</small></div>)}</div>{selected&&<div className="p-3 flex gap-2"><input className="control" value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')send()}} placeholder="Escribir respuesta"/><button className="btn primary" disabled={!text.trim()} onClick={send}><Send size={18}/> Enviar</button></div>}</section></div></>}
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
export function Training(){return <><h1>Aprende a usar EcoConecta</h1><p className="muted mb-5">Guías cortas para las actividades diarias del coordinador.</p><div className="grid grid-cols-1 md:grid-cols-2 gap-4">{[{t:'Revisar y autorizar una solicitud',steps:['Entra a Recolecciones y selecciona una solicitud pendiente.','Lee la descripción y revisa la foto si existe.','Solicita información adicional si hace falta.','Confirma la revisión y autoriza o rechaza con motivo.']},{t:'Programar y avisar al equipo',steps:['Abre una solicitud autorizada.','Elige al responsable, fecha y franja disponible.','Agrega una nota y pulsa Programar y avisar por WhatsApp.','En el prototipo, los mensajes aparecen en la bandeja simulada.']},{t:'Registrar el pesaje',steps:['Selecciona una solicitud programada.','Registra los materiales realmente aceptados y sus pesos.','Anota el material no aceptado.','Confirma el registro. En reciclaje se calcula el valor por kg para el reciclador.']},{t:'Gestionar horarios y mensajes',steps:['Abre Configuración para modificar días y franjas de tu actividad.','En Mensajes puedes revisar y contestar conversaciones.','En Equipo añade o desactiva responsables.','En Historial consulta y exporta registros.']}].map((x,i)=><section className="panel p-5" key={x.t}><div className="flex items-center gap-3 mb-3"><span className="mini-icon"><BookOpen/></span><h2>{x.t}</h2></div><ol className="list-decimal pl-5 space-y-2 text-sm text-[#465b4c]">{x.steps.map(s=><li key={s}>{s}</li>)}</ol></section>)}</div></>}
