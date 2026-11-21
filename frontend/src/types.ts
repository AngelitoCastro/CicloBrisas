export type Flow = 'organico' | 'reciclable'
export type Generator = 'Hogar' | 'Comercio'
export type Role = 'huerta' | 'reciclaje' | 'admin'
export type Status = 'pendiente' | 'autorizada' | 'programada' | 'completada' | 'rechazada'
export type MaterialLine = { material: string; kg: number; rate: number }
export type CollectionConfirmation = { source: 'whatsapp-demo' | 'manual'; at: string; confirmedBy: string }
export type Request = { id: string; backendId?: number; flow: Flow; kind: 'residuo' | 'donacion'; name: string; phone: string; address: string; generator: Generator; pilot: boolean; description: string; evidence: string; estKg: number; units: number; delivery: 'recoger' | 'entrega'; preference: string; status: Status; source: 'WhatsApp' | 'Manual'; assignee?: string; date?: string; time?: string; note?: string; lines?: MaterialLine[]; acceptedKg?: number; confirmation?: CollectionConfirmation; receivedUnits?: number; ecoPoints?: number; ecoPointRule?: EcoPointRule; rejected?: string; history: string[]; created: string }
export type Member = { id: string; name: string; phone: string; flow: Flow; group: string; active: boolean }
export type Schedule = { days: number[]; slots: { label: string; start: string; end: string }[] }
export type Message = { id: string; flow: Flow; name: string; phone: string; text: string; direction: 'in' | 'out'; at: string; requestId?: string }
export type Knowledge = { id: string; question: string; answer: string }
export type IntakeLine = MaterialLine & { packs?: number }
export type IntakeRecord = {
  id: string; memberId: string; memberName: string; providerName: string;
  ticketNumber: string; date: string; notes: string; lines: IntakeLine[];
  created: string;
}
export type EcoPointRule = { base: number; perKg: number }
export type EcoPointRules = Record<Flow, Record<Generator, EcoPointRule>>
export type Data = { pointRules: EcoPointRules; intakeRecords: IntakeRecord[]; requests: Request[]; members: Member[]; schedules: Record<Flow, Schedule>; rates: Record<string, number>; messages: Message[]; knowledge: Knowledge[] }
export const flows: Record<Flow, string> = { organico: 'Huerta · Orgánicos', reciclable: 'Reciclaje · Aprovechables' }
export const statuses: Record<Status, string> = { pendiente: 'Recibida', autorizada: 'Autorizada', programada: 'Programada', completada: 'Recolectada', rechazada: 'Rechazada' }
export const materials: Record<Flow, string[]> = { organico: ['Cáscaras de frutas y verduras', 'Restos de alimentos', 'Poda y hojas', 'Borra de café', 'Otros orgánicos'], reciclable: ['Cartón', 'Papel', 'Plástico', 'Vidrio', 'Metal', 'Otros aprovechables'] }
export const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
export const isoDate = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
export const money = (n: number) => n.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 2 })
export const kgOf = (r: Request) => r.acceptedKg ?? r.lines?.reduce((s, l) => s + l.kg, 0) ?? 0
export const isRecyclerValuePending = (r: Request) =>
    r.status === 'completada' && r.flow === 'reciclable' && r.kind === 'residuo' &&
    (r.acceptedKg ?? 0) > 0 && !r.lines?.length
export const valueOf = (r: Request) => r.lines?.reduce((s, l) => s + l.kg * l.rate, 0) ?? 0
export const uid = () => crypto.randomUUID()

export const defaultPointRule: Readonly<EcoPointRule> = { base: 10, perKg: 5 }
