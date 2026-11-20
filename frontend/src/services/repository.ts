import { initialData } from './demo'
import type { Data } from '../types'
// Único punto de persistencia del prototipo. Sustituir por consultas Supabase con RLS.
const KEY = 'ecoconecta-v2-demo'
export const repository = { load(): Data { try { const raw = localStorage.getItem(KEY); return raw ? JSON.parse(raw) : structuredClone(initialData) } catch { return structuredClone(initialData) } }, save(data: Data) { localStorage.setItem(KEY, JSON.stringify(data)) }, reset() { localStorage.removeItem(KEY); return structuredClone(initialData) } }
