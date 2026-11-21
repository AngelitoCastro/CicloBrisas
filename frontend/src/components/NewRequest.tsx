import { useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Modal } from './UI'
import { type Flow, type Request, isoDate, uid } from '../types'

type Props = {
    flow: Flow
    onClose: () => void
    onSave: (request: Request) => void
    source?: Request['source']
}

export default function NewRequest({ flow, onClose, onSave, source = 'Manual' }: Props) {
    const [kind, setKind] = useState<Request['kind']>('residuo')
    const [generator, setGenerator] = useState<Request['generator']>('Hogar')
    const [delivery, setDelivery] = useState<Request['delivery']>('recoger')
    const [evidence, setEvidence] = useState('')
    const [error, setError] = useState('')
    const optionalFields = useRef<HTMLDetailsElement>(null)
    const huerta = flow === 'organico'
    const donation = huerta && kind === 'donacion'

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        const fields = new FormData(event.currentTarget)
        const get = (key: string) => String(fields.get(key) ?? '').trim()
        if (!get('name') || !get('description') || !get('address') || !get('phone')) {
            setError('Completa los datos del solicitante y la descripción.')
            return
        }

        onSave({
            id: 'EC-' + uid().slice(0, 8).toUpperCase(),
            flow,
            kind: donation ? 'donacion' : 'residuo',
            name: get('name'),
            phone: get('phone'),
            address: get('address'),
            generator,
            pilot: generator === 'Comercio' && fields.get('pilot') === 'on',
            description: get('description'),
            evidence,
            estKg: donation ? 0 : Number(get('kg') || 0),
            units: donation ? Number(get('units')) : 0,
            delivery: huerta ? delivery : 'recoger',
            preference: get('preference'),
            note: get('note'),
            status: 'pendiente',
            source,
            created: isoDate(),
            history: [
                source === 'Manual' ? 'Solicitud registrada manualmente por el coordinador' : 'Solicitud recibida por WhatsApp (simulada)',
            ],
        })
    }

    function readEvidence(event: ChangeEvent<HTMLInputElement>) {
        const file = event.currentTarget.files?.[0]
        if (!file) {
            setEvidence('')
            return
        }
        if (file.size > 1_000_000) {
            setError('La foto supera 1 MB.')
            event.currentTarget.value = ''
            setEvidence('')
            return
        }
        setError('')
        const reader = new FileReader()
        reader.onload = () => setEvidence(String(reader.result))
        reader.readAsDataURL(file)
    }

    return <Modal
        title={source === 'Manual' ? 'Nueva solicitud manual' : 'Simular solicitud entrante de WhatsApp'}
        onClose={onClose}
    >
        <form
            className="form-grid"
            onSubmit={submit}
            onInvalidCapture={event => {
                if (optionalFields.current?.contains(event.target as Node)) optionalFields.current.open = true
            }}
        >
            <label className="field">Tipo de solicitante
                <select value={generator} onChange={event => setGenerator(event.target.value as Request['generator'])}>
                    <option>Hogar</option>
                    <option value="Comercio">Unidad productiva</option>
                </select>
            </label>
            {huerta && <label className="field">Tipo de solicitud
                <select value={kind} onChange={event => setKind(event.target.value as Request['kind'])}>
                    <option value="residuo">Residuos orgánicos</option>
                    <option value="donacion">Donación para huerta</option>
                </select>
            </label>}
            <label className="field">Nombre
                <input name="name" required />
            </label>
            <label className="field">Teléfono o WhatsApp
                <input name="phone" type="tel" required />
            </label>
            <label className="field">Dirección
                <input name="address" required />
            </label>
            {huerta && <label className="field">Modalidad
                <select value={delivery} onChange={event => setDelivery(event.target.value as Request['delivery'])}>
                    <option value="recoger">Recoger en dirección</option>
                    <option value="entrega">Entrega en la huerta</option>
                </select>
            </label>}
            <label className="field full">{donation ? '¿Qué vas a donar?' : '¿Qué material van a recoger?'}
                <textarea name="description" required />
            </label>
            {donation && <label className="field">Unidades
                <input name="units" type="number" min={1} step={1} required />
            </label>}

            <details ref={optionalFields} className="collection-disclosure full">
                <summary>Datos opcionales</summary>
                <div className="collection-disclosure-body form-grid">
                    {generator === 'Comercio' && <label className="checkline full">
                        <input type="checkbox" name="pilot" /> Comercio piloto
                    </label>}
                    {!donation && <label className="field">Peso estimado (kg)
                        <input name="kg" type="number" min={0} step="0.01" />
                    </label>}
                    <label className="field">Horario preferido
                        <input name="preference" placeholder="Ej. viernes por la mañana" />
                    </label>
                    <label className="field full">Foto (máximo 1 MB)
                        <input type="file" accept="image/*" onChange={readEvidence} />
                    </label>
                    {evidence && <img className="evidence full" src={evidence} alt="Evidencia de la solicitud" />}
                    <label className="field full">Comentarios
                        <input name="note" placeholder="Indicaciones adicionales" />
                    </label>
                </div>
            </details>

            {error && <p className="error full" role="alert">{error}</p>}
            <button className="btn primary full" type="submit">Registrar solicitud</button>
        </form>
    </Modal>
}
