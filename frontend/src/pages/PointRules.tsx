import { useState, type FormEvent } from 'react'
import { Leaf, Recycle, Save } from 'lucide-react'
import { type EcoPointRules, type Flow, type Generator } from '../types'
import { isValidPointAmount, maxPointRuleValue, pointRuleFields, pointRuleFlows, pointRuleGenerators } from '../services/pointRules'

const flows = {
    organico: { title: 'Huerta', icon: Leaf },
    reciclable: { title: 'Reciclaje', icon: Recycle },
}
const generatorLabels = { Hogar: 'Hogar', Comercio: 'Unidad productiva' }
const fieldLabels = { base: 'Puntos base', perKg: 'Puntos por kg' }

type Props = {
    rules: EcoPointRules
    save: (rules: EcoPointRules) => boolean
}

export default function PointRulesPage({ rules, save }: Props) {
    const [feedback, setFeedback] = useState('')
    const [failed, setFailed] = useState(false)

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        const form = new FormData(event.currentTarget)
        const next = structuredClone(rules)
        for (const flow of pointRuleFlows) {
            for (const generator of pointRuleGenerators) {
                for (const field of pointRuleFields) {
                    const input = form.get(fieldName(flow, generator, field))
                    const value = typeof input === 'string' && input.trim() ? Number(input) : NaN
                    if (!isValidPointAmount(value)) {
                        setFailed(true)
                        setFeedback('Ingresa valores desde cero y con hasta dos decimales.')
                        return
                    }
                    next[flow][generator][field] = value
                }
            }
        }
        const saved = save(next)
        setFailed(!saved)
        setFeedback(saved ? 'Reglas guardadas en este navegador.' : 'No se pudieron guardar las reglas en este navegador.')
    }

    return <section aria-labelledby="point-rules-title">
        <h1 id="point-rules-title">Reglas de EcoPuntos</h1>
        <p className="muted mt-1 mb-4">Configura los puntos base por solicitud y los puntos por kilo para cada flujo y tipo de generador.</p>
        <form className="space-y-4" onSubmit={submit} onChange={() => setFeedback('')}>
            <div className="grid gap-4 lg:grid-cols-2">
                {pointRuleFlows.map(flow => {
                    const { title, icon: Icon } = flows[flow]
                    return <section className="panel" key={flow} aria-labelledby={'point-rules-' + flow}>
                        <header className="panel-head"><Icon aria-hidden="true" /><h2 id={'point-rules-' + flow}>{title}</h2></header>
                        <div className="panel-body space-y-4">
                            {pointRuleGenerators.map(generator => (
                                <fieldset className="min-w-0 rounded-xl border border-[#d9e1d7] px-3 pb-3" key={generator}>
                                    <legend className="px-1 font-semibold text-forest">{generatorLabels[generator]}</legend>
                                    <div className="grid grid-cols-2 gap-3">
                                        {pointRuleFields.map(field => {
                                            const name = fieldName(flow, generator, field)
                                            return <label className="field" key={name}>{fieldLabels[field]}
                                                <input name={name} type="number" inputMode="decimal" min="0"
                                                    max={maxPointRuleValue} step="0.01" required defaultValue={rules[flow][generator][field]} />
                                            </label>
                                        })}
                                    </div>
                                </fieldset>
                            ))}
                        </div>
                    </section>
                })}
            </div>
            <p className="note">Cálculo parametrizable sujeto a validación FSD. Los cambios se aplican en futuros cierres con peso aceptado. Cada cierre conserva la regla aplicada.</p>
            <div className="flex flex-wrap items-center gap-3">
                <button className="btn primary"><Save size={18} aria-hidden="true" /> Guardar reglas</button>
                <p className={failed ? 'error' : 'muted'} role="status">{feedback}</p>
            </div>
        </form>
    </section>
}

function fieldName(flow: Flow, generator: Generator, field: typeof pointRuleFields[number]) {
    return flow + '.' + generator + '.' + field
}
