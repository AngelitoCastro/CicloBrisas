import { uid, type Data, type Message, type Request, type Status } from '../types'

export type DemoNotice = { name: string; phone: string; text: string }

export function applyRequestUpdate(
    data: Data,
    request: Request,
    notifications: DemoNotice[] = [],
    reply?: DemoNotice,
    expectedStatus?: Status,
): Data {
    const existing = data.requests.find(item => item.id === request.id)
    if (expectedStatus && existing?.status !== expectedStatus) return data

    const firstMessage = !existing && request.source === 'WhatsApp'
        ? { name: request.name, phone: request.phone, text: request.description }
        : undefined
    const inbound = reply ?? firstMessage
    const at = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Bogota' })

    const log = (notice: DemoNotice, direction: Message['direction']): Message => ({
        ...notice,
        id: uid(),
        flow: request.flow,
        direction,
        at,
        requestId: request.id,
    })

    return {
        ...data,
        requests: existing
            ? data.requests.map(item => item.id === request.id ? request : item)
            : [request, ...data.requests],
        messages: [
            ...data.messages,
            ...(inbound ? [log(inbound, 'in')] : []),
            ...notifications.map(notice => log(notice, 'out')),
        ],
    }
}
