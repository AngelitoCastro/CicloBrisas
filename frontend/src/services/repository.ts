import { initialData } from './demo'
import type { Data } from '../types'

// Único punto de persistencia del prototipo. Sustituir por Supabase con RLS.
// Conservamos la clave de V2 para no perder las solicitudes ni la configuración.
const KEY = 'ecoconecta-v2-demo'
export const repository = {
  load(): Data {
    try {
      const raw = localStorage.getItem(KEY)
      if (!raw) return structuredClone(initialData)
      const previous = JSON.parse(raw) as Data
      return { ...previous, intakeRecords: Array.isArray(previous.intakeRecords) ? previous.intakeRecords : [] }
    } catch {
      return structuredClone(initialData)
    }
  },
  save(data: Data) { localStorage.setItem(KEY, JSON.stringify(data)) },
  reset() { localStorage.removeItem(KEY); return structuredClone(initialData) },
}
