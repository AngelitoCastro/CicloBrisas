import { initialData } from './demo'
import type { Data, Knowledge, Schedule } from '../types'
import { loadPointRules } from './pointRules'

// Claves separadas: DEMO_KEY solo almacena datos ficticios de demostración;
// PREFS_KEY guarda únicamente preferencias locales (horarios, tarifas y base de conocimiento).
export const DEMO_KEY = 'ecoconecta-v2-demo'
export const PREFS_KEY = 'ecoconecta-v2-prefs'

export type LocalPreferences = {
  schedules: Record<'organico' | 'reciclable', Schedule>
  rates: Record<string, number>
  knowledge: Knowledge[]
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const BACKEND_CODE_RE = /^ECO-\d{4}-\d+/i

export function containsRealBackendData(candidate: unknown): boolean {
  if (!candidate || typeof candidate !== 'object') return false
  const record = candidate as Partial<Data>
  if (
    Array.isArray(record.requests) &&
    record.requests.some(
      r =>
        typeof r?.backendId === 'number' ||
        (typeof r?.id === 'string' && BACKEND_CODE_RE.test(r.id)),
    )
  ) {
    return true
  }
  if (
    Array.isArray(record.members) &&
    record.members.some(m => typeof m?.id === 'string' && UUID_RE.test(m.id))
  ) {
    return true
  }
  if (
    Array.isArray(record.messages) &&
    record.messages.some(
      msg => typeof msg?.requestId === 'string' && BACKEND_CODE_RE.test(msg.requestId),
    )
  ) {
    return true
  }
  return false
}

function defaultPreferences(): LocalPreferences {
  const base = structuredClone(initialData)
  return {
    schedules: base.schedules,
    rates: base.rates,
    knowledge: base.knowledge,
  }
}

function extractPreferences(candidate: unknown): LocalPreferences {
  const defaults = defaultPreferences()
  if (!candidate || typeof candidate !== 'object') return defaults
  const record = candidate as Partial<LocalPreferences>
  return {
    schedules:
      record.schedules &&
      typeof record.schedules === 'object' &&
      record.schedules.organico &&
      record.schedules.reciclable
        ? record.schedules
        : defaults.schedules,
    rates:
      record.rates && typeof record.rates === 'object' && !Array.isArray(record.rates)
        ? record.rates
        : defaults.rates,
    knowledge: Array.isArray(record.knowledge) ? record.knowledge : defaults.knowledge,
  }
}

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSetItem(key: string, value: string): void {
  localStorage.setItem(key, value)
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch {
    // Sin acceso a localStorage
  }
}

export const repository = {
  loadPreferences(): LocalPreferences {
    const raw = safeGetItem(PREFS_KEY)
    if (!raw) return defaultPreferences()
    try {
      return extractPreferences(JSON.parse(raw))
    } catch {
      safeRemoveItem(PREFS_KEY)
      return defaultPreferences()
    }
  },

  savePreferences(prefs: LocalPreferences): void {
    const clean: LocalPreferences = {
      schedules: prefs.schedules,
      rates: prefs.rates,
      knowledge: prefs.knowledge,
    }
    safeSetItem(PREFS_KEY, JSON.stringify(clean))
  },

  /** Elimina de localStorage cualquier copia anterior contaminada con datos reales de la API. */
  purgeRealDataFromStorage(): boolean {
    const raw = safeGetItem(DEMO_KEY)
    if (!raw) return false
    try {
      const parsed = JSON.parse(raw) as unknown
      if (containsRealBackendData(parsed)) {
        if (!safeGetItem(PREFS_KEY)) {
          try {
            repository.savePreferences(extractPreferences(parsed))
          } catch {
            // Ignorar cuota llena al migrar preferencias
          }
        }
        safeRemoveItem(DEMO_KEY)
        return true
      }
      return false
    } catch {
      safeRemoveItem(DEMO_KEY)
      return true
    }
  },

  /** Devuelve un estado limpio sin solicitudes ni contactos reales, conservando solo preferencias locales. */
  createCleanWorkspace(): Data {
    repository.purgeRealDataFromStorage()
    const prefs = repository.loadPreferences()
    return {
      pointRules: loadPointRules(undefined),
      intakeRecords: [],
      requests: [],
      members: [],
      schedules: prefs.schedules,
      rates: prefs.rates,
      messages: [],
      knowledge: prefs.knowledge,
    }
  },

  load(): Data {
    repository.purgeRealDataFromStorage()
    const prefs = repository.loadPreferences()
    try {
      const raw = safeGetItem(DEMO_KEY)
      if (!raw) {
        const base = structuredClone(initialData)
        return { ...base, ...prefs }
      }
      const previous = JSON.parse(raw) as Data
      if (containsRealBackendData(previous)) {
        safeRemoveItem(DEMO_KEY)
        const base = structuredClone(initialData)
        return { ...base, ...prefs }
      }
      return {
        ...previous,
        schedules: prefs.schedules,
        rates: prefs.rates,
        knowledge: prefs.knowledge,
        intakeRecords: Array.isArray(previous.intakeRecords) ? previous.intakeRecords : [],
        pointRules: loadPointRules(previous.pointRules),
      }
    } catch {
      safeRemoveItem(DEMO_KEY)
      const base = structuredClone(initialData)
      return { ...base, ...prefs }
    }
  },

  save(data: Data): void {
    repository.savePreferences({
      schedules: data.schedules,
      rates: data.rates,
      knowledge: data.knowledge,
    })
    if (containsRealBackendData(data)) {
      safeRemoveItem(DEMO_KEY)
      return
    }
    safeSetItem(DEMO_KEY, JSON.stringify(data))
  },

  reset(): Data {
    safeRemoveItem(DEMO_KEY)
    safeRemoveItem(PREFS_KEY)
    return structuredClone(initialData)
  },
}
