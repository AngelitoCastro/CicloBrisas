import type { CollectionConfirmation, Data, Request } from '../types'
import { calculateEcoPoints, isValidPointAmount } from './pointRules'

type ClosureInput = {
    source: CollectionConfirmation['source']
    text: string
    confirmed?: boolean
    reason?: string
    now?: Date
    notifyCollector?: boolean
}

type Notice = { name: string; phone: string; text: string }

type ClosureResult =
    | { ok: false; error: string }
    | { ok: true; request: Request; notifications: Notice[]; reply?: Notice }

export function closeCollection(data: Data, request: Request, input: ClosureInput): ClosureResult {
    const r = data.requests.find(item => item.id === request.id && item.flow === request.flow)
    if (!r || r.status !== 'programada') {
        return { ok: false, error: 'La solicitud debe estar programada para registrar el cierre.' }
    }

    const simulated = input.source === 'whatsapp-demo'
    const assigned = data.members.find(member => member.id === r.assignee && member.flow === r.flow)
    const donation = r.kind === 'donacion'
    const submitted = input.text.trim()
    const reason = input.reason?.trim() ?? ''
    const replyMatch = simulated ? /^LISTO\s+(\S+)\s+(\d+(?:[.,]\d{1,2})?)$/i.exec(submitted) : null
    if (simulated && !assigned?.phone) {
        return { ok: false, error: 'La solicitud debe tener un responsable asignado con teléfono.' }
    }
    if (simulated && replyMatch?.[1].toUpperCase() !== r.id.toUpperCase()) {
        const example = 'LISTO ' + r.id + (donation ? ' 2' : ' 8')
        return { ok: false, error: 'Usa el código de esta solicitud. Ejemplo: ' + example + '.' }
    }
    if (!simulated && (!input.confirmed || !reason)) {
        return { ok: false, error: 'Confirma la cantidad e indica por qué registras el cierre manual.' }
    }

    const amount = replyMatch ? replyMatch[2].replace(',', '.') : submitted
    const quantity = amount ? Number(amount) : NaN
    const validQuantity = donation ? Number.isInteger(quantity) && quantity <= r.units :
        Number.isFinite(quantity) && quantity <= 999_999.99 && Number(quantity.toFixed(2)) === quantity
    if (!validQuantity || quantity < 0 || (simulated && quantity === 0)) {
        return {
            ok: false,
            error: donation ? 'Registra una cantidad válida de unidades.' : 'Registra un peso válido con hasta dos decimales.',
        }
    }

    const rule = !donation && quantity > 0 ? data.pointRules[r.flow][r.generator] : undefined
    const ecoPoints = rule ? calculateEcoPoints(Math.round(quantity * 100), rule) : undefined
    if (ecoPoints !== undefined && !isValidPointAmount(ecoPoints)) {
        return {
            ok: false,
            error: 'El total de EcoPuntos supera el máximo permitido. Revisa el peso o pide a Administración que revise la regla.',
        }
    }
    const confirmedBy = simulated && assigned ? assigned.name : r.flow === 'organico' ? 'Coordinador de Huerta' : 'Coordinador de Reciclaje'
    const at = (input.now ?? new Date()).toISOString()
    const result = quantity === 0 ? 'Sin material aceptado' :
        quantity.toLocaleString('es-CO') + (donation ? ' unidades recibidas' : ' kg aceptados')
    const formattedPoints = ecoPoints?.toLocaleString('es-CO')
    const receipt = 'Solicitud ' + r.id + ' finalizada. ' + result + '.' +
        (formattedPoints === undefined ? '' : ' EcoPuntos de demostración para el habitante: ' + formattedPoints + '.')
    const history = [...r.history, simulated ? 'Confirmación simulada por WhatsApp de ' + confirmedBy + ' · ' + result :
        'Cierre manual · ' + result + ' · Motivo: ' + reason]
    if (formattedPoints !== undefined) history.push('EcoPuntos de demostración para el habitante: ' + formattedPoints)
    const notifications = [{ name: r.name, phone: r.phone, text: receipt }]
    if (simulated && assigned && input.notifyCollector) {
        notifications.push({
            name: assigned.name, phone: assigned.phone,
            text: 'Registramos tu confirmación para la solicitud ' + r.id + '. ' + result + '.',
        })
    }

    return {
        ok: true,
        request: {
            ...r,
            status: 'completada',
            confirmation: { source: input.source, at, confirmedBy },
            acceptedKg: donation ? undefined : quantity,
            lines: [],
            receivedUnits: donation ? quantity : undefined,
            ecoPoints,
            ecoPointRule: rule && { ...rule },
            rejected: !simulated && quantity === 0 ? reason : undefined,
            history,
        },
        notifications,
        reply: simulated && assigned ? { name: assigned.name, phone: assigned.phone, text: submitted } : undefined,
    }
}
