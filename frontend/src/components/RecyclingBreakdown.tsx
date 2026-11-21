import { useState, type FormEvent } from 'react'
import { Plus, Save, Trash2 } from 'lucide-react'
import { isRecyclerValuePending, materials, money, uid, type Data, type MaterialLine, type Request } from '../types'

type Props = {
    request: Request
    rates: Data['rates']
    onSave: (lines: MaterialLine[]) => void
}

type DraftLine = { id: string; material: string; weight: string }
const formatKg = (kg: number) => kg.toLocaleString('es-CO', { maximumFractionDigits: 2 }) + ' kg'

export default function RecyclingBreakdown({ request, rates, onSave }: Props) {
    const [draft, setDraft] = useState<DraftLine[]>([{ id: 'initial', material: '', weight: '' }])
    if (!isRecyclerValuePending(request)) return null

    const acceptedHundredths = Math.round((request.acceptedKg ?? 0) * 100)
    const lines = draft.map(({ material, weight }) => ({ material, kg: Number(weight), rate: rates[material] }))
    const validWeights = lines.every(line => Number.isFinite(line.kg) && line.kg > 0 &&
        line.kg <= acceptedHundredths / 100 && Number(line.kg.toFixed(2)) === line.kg)
    const knownMaterials = lines.every(line => materials.reciclable.includes(line.material))
    const distinctMaterials = new Set(lines.map(line => line.material)).size === lines.length
    const configuredRates = lines.every(line => Number.isFinite(line.rate) && line.rate >= 0)
    const totalHundredths = lines.reduce((sum, line) => sum + Math.round(line.kg * 100), 0)
    const value = lines.reduce((sum, line) => sum + line.kg * line.rate, 0)
    const complete = validWeights && knownMaterials && distinctMaterials && configuredRates &&
        totalHundredths === acceptedHundredths && Number.isFinite(value)

    function edit(id: string, changes: Partial<Pick<DraftLine, 'material' | 'weight'>>) {
        setDraft(current => current.map(line => line.id === id ? { ...line, ...changes } : line))
    }

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        if (complete) onSave(lines)
    }

    return <form className="space-y-3" onSubmit={submit} aria-label="Desglose de reciclables">
        <p className="muted">Distribuye los {formatKg(acceptedHundredths / 100)} aceptados entre los materiales pesados.</p>
        {draft.map((line, index) => (
            <div key={line.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2 rounded-lg border border-[#d4dfd4] p-3 sm:grid-cols-[minmax(0,1fr)_7rem_auto]">
                <label className="field col-span-2 min-w-0 sm:col-span-1">Material
                    <select required value={line.material} onChange={event => edit(line.id, { material: event.target.value })}>
                        <option value="">Selecciona un material</option>
                        {materials.reciclable.map(material => (
                            <option key={material} disabled={draft.some(other => other.id !== line.id && other.material === material)}>
                                {material}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="field min-w-0">Peso (kg)
                    <input required type="number" min="0.01" max={acceptedHundredths / 100} step="0.01" inputMode="decimal"
                        value={line.weight} onChange={event => edit(line.id, { weight: event.target.value })} />
                </label>
                <button type="button" className="btn icon-btn" disabled={draft.length === 1} aria-label={'Quitar material ' + (index + 1)}
                    onClick={() => setDraft(current => current.filter(other => other.id !== line.id))}>
                    <Trash2 size={17} aria-hidden="true" />
                </button>
            </div>
        ))}
        <p className="muted" role="status">
            {complete ? 'Valor estimado para el reciclador: ' + money(value) :
                validWeights && knownMaterials && !configuredRates ? 'Pide a Administración que revise las tarifas de los materiales.' :
                validWeights && knownMaterials && totalHundredths > acceptedHundredths ? 'El desglose supera el peso aceptado.' :
                'Registra pesos positivos con hasta dos decimales. La suma debe ser igual al peso aceptado.'}
        </p>
        <div className="flex flex-wrap gap-2">
            <button type="button" className="btn" disabled={draft.length >= materials.reciclable.length}
                onClick={() => setDraft(current => [...current, { id: uid(), material: '', weight: '' }])}>
                <Plus size={18} aria-hidden="true" /> Agregar material
            </button>
            <button type="submit" className="btn primary" disabled={!complete}>
                <Save size={18} aria-hidden="true" /> Guardar desglose
            </button>
        </div>
    </form>
}
