import type { FormEvent } from 'react'
import { Scale } from 'lucide-react'
import { materials, money, type Data } from '../types'

export default function RecyclingRates({ rates, save }: { rates: Data['rates']; save?: (rates: Data['rates']) => void }) {
    return <section className="panel" aria-labelledby="recycling-rates">
        <header className="panel-head">
            <Scale aria-hidden="true" /><h2 id="recycling-rates">{save ? 'Tarifas para el reciclador' : 'Tarifas vigentes'}</h2>
        </header>
        <div className="panel-body space-y-3">
            <p className="muted">Valor por kilogramo aceptado en pesos colombianos.</p>
            {save ? <RecyclingRatesForm rates={rates} save={save} /> : <>
                <dl className="divide-y divide-[#e2e9e0]">
                    {materials.reciclable.map(material => <div key={material} className="flex flex-wrap justify-between gap-x-3 py-2">
                        <dt>{material}</dt><dd className="font-semibold">{money(rates[material] ?? 0)} por kg</dd>
                    </div>)}
                </dl>
                <p className="note">Administración actualiza estas tarifas. Se aplica la tarifa vigente al registrar el pesaje.</p>
            </>}
        </div>
    </section>
}

function RecyclingRatesForm({ rates, save }: { rates: Data['rates']; save: (rates: Data['rates']) => void }) {
    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        const entries = new FormData(event.currentTarget)
        const next = { ...rates }
        for (const material of materials.reciclable) {
            const value = entries.get(material)
            if (typeof value !== 'string' || value.trim() === '') return
            const rate = Number(value)
            if (!Number.isFinite(rate) || rate < 0) return
            next[material] = rate
        }
        save(next)
    }

    return <form className="space-y-3" onSubmit={submit}>
        {materials.reciclable.map(material => <label className="field" key={material}>
            {material} · COP/kg
            <input name={material} type="number" min="0" step="0.01" defaultValue={rates[material] ?? 0} required />
        </label>)}
        <button className="btn primary w-full" type="submit">Guardar tarifas</button>
        <p className="note">Cada pesaje conserva la tarifa aplicada al registrarlo.</p>
    </form>
}
