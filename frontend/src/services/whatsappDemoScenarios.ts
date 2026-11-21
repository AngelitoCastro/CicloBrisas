import type { Data, Flow, Request } from '../types'
import { getCollectionClock } from './collectionSchedule'
import { initialData } from './demo'

const examples = {
    organico: {
        requestId: 'DEMO-H01',
        residentName: 'Lucía Romero',
        address: 'Torre de ejemplo A, piso 2, apartamento 204',
        material: 'cáscaras de frutas y verduras',
        kg: 8,
        previousBalance: 25,
        phone: '3005550990',
    },
    reciclable: {
        requestId: 'DEMO-R01',
        residentName: 'Valeria Torres',
        address: 'Torre de ejemplo B, piso 3, apartamento 302',
        material: 'cartón y botellas de plástico',
        kg: 12.5,
        previousBalance: 60,
        phone: '3005550991',
    },
} satisfies Record<Flow, {
    requestId: string
    residentName: string
    address: string
    material: string
    kg: number
    previousBalance: number
    phone: string
}>

export function getWhatsAppDemoExample(flow: Flow) {
    return examples[flow]
}

export function createWhatsAppDemoData(): Data {
    return { ...structuredClone(initialData), requests: [], messages: [], intakeRecords: [] }
}

export function createWhatsAppDemoRequest(flow: Flow): { request: Request; message: string; receipt: string } {
    const { requestId, residentName, phone, address, material, kg } = getWhatsAppDemoExample(flow)
    const request: Request = {
        id: requestId,
        flow,
        kind: 'residuo',
        name: residentName,
        phone,
        address,
        generator: 'Hogar',
        pilot: false,
        description: material,
        evidence: '',
        estKg: kg,
        units: 0,
        delivery: 'recoger',
        preference: '',
        status: 'pendiente',
        source: 'WhatsApp',
        history: ['Solicitud recibida por WhatsApp simulado'],
        created: getCollectionClock().today,
    }
    const message = 'Hola, soy ' + residentName + '. Quiero solicitar una recolección de ' + material + '. La dirección es ' + address + '.'
    const receipt = 'Recibimos tu solicitud ' + requestId + '. Te avisaremos por aquí cuando el coordinador programe la visita.'
    return { request, message, receipt }
}
