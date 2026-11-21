import { describe, it, beforeEach } from 'node:test'
import assert from 'node:assert/strict'

// Entorno mínimo de navegador en Node para probar persistencia, sesión y cancelación en vuelo.
const localMap = new Map<string, string>()
const sessionMap = new Map<string, string>()

function makeStorage(map: Map<string, string>) {
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => {
      map.set(key, String(value))
    },
    removeItem: (key: string) => {
      map.delete(key)
    },
    clear: () => {
      map.clear()
    },
  }
}

;(globalThis as unknown as { localStorage: ReturnType<typeof makeStorage> }).localStorage =
  makeStorage(localMap)
;(globalThis as unknown as { sessionStorage: ReturnType<typeof makeStorage> }).sessionStorage =
  makeStorage(sessionMap)

import {
  DEMO_KEY,
  PREFS_KEY,
  containsRealBackendData,
  repository,
} from '../src/services/repository'
import {
  api,
  ApiError,
  getStoredToken,
  setUnauthorizedHandler,
  type UsuarioApi,
} from '../src/services/api'
import { loadBackendForAuthenticatedUser } from '../src/services/backendBridge'

const FAKE_COORD: UsuarioApi = {
  id: '00000000-0000-4000-8000-000000000101',
  nombre: 'Coordinación Huerta Piloto',
  telefono: '+573000000101',
  rol: 'COORD_HUERTEROS',
  direccion: null,
  sector_manzana: null,
  es_piloto: false,
  puntos_acumulados: 0,
  activo: true,
  creado_en: '2026-11-21T00:00:00+00:00',
}

function assertNoRealDataInLocalStorage() {
  const dump = [...localMap.entries()].map(([k, v]) => `${k}=${v}`).join('\n')
  assert.equal(localStorage.getItem(DEMO_KEY), null)
  for (const forbidden of [
    'Vecino Real Confidencial',
    'Hogar Real Privado',
    'Huertero Real',
    'Reciclador Real',
    '+573112223344',
    '+573001234567',
    '+573115556677',
    'Calle Real 123',
    'ECO-2026-000042',
    'ECO-2026-000009',
    'backendId',
  ]) {
    assert.ok(!dump.includes(forbidden), `Dato real encontrado en localStorage: ${forbidden}`)
  }
}

describe('Aislamiento de localStorage, cierre de sesión y respuestas pendientes', () => {
  beforeEach(() => {
    localMap.clear()
    sessionMap.clear()
    setUnauthorizedHandler(null)
  })

  it('limpia copias anteriores contaminadas en localStorage y conserva solo preferencias locales', () => {
    const tainted = {
      requests: [
        {
          id: 'ECO-2026-000042',
          backendId: 42,
          flow: 'organico',
          name: 'Vecino Real Confidencial',
          phone: '+573112223344',
          address: 'Calle Real 123',
        },
      ],
      members: [
        {
          id: '550e8400-e29b-41d4-a716-446655440000',
          name: 'Huertero Real',
          phone: '+573115556677',
          flow: 'organico',
          group: 'Colectivo Huerta',
          active: true,
        },
      ],
      schedules: repository.loadPreferences().schedules,
      rates: { Cartón: 950 },
      knowledge: [{ id: 'k1', question: 'Q', answer: 'A' }],
      messages: [],
      intakeRecords: [],
    }
    localStorage.setItem(DEMO_KEY, JSON.stringify(tainted))

    const purged = repository.purgeRealDataFromStorage()
    assert.equal(purged, true)
    assertNoRealDataInLocalStorage()

    const prefsRaw = localStorage.getItem(PREFS_KEY) ?? ''
    assert.ok(prefsRaw.includes('"Cartón":950'))
  })

  it('impide persistir solicitudes o contactos reales en localStorage incluso tras cerrar sesión', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (input: string | URL) => {
      const url = String(input)
      if (url.includes('/api/auth/login')) {
        return new Response(
          JSON.stringify({
            access_token: 'jwt-prueba-real',
            token_type: 'bearer',
            expira_en_segundos: 3600,
            usuario: FAKE_COORD,
          }),
          { status: 200 },
        )
      }
      if (url.includes('/api/solicitudes/42/historial')) {
        return new Response(JSON.stringify([]), { status: 200 })
      }
      if (url.includes('/api/solicitudes')) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 42,
                codigo_publico: 'ECO-2026-000042',
                flujo: 'ORGANICO',
                subtipo_material: 'Cáscaras',
                cantidad_estimada_kg: 3.5,
                cantidad_real_kg: null,
                disponibilidad_usuario: 'Mañanas',
                observaciones: 'Portería',
                estado: 'RECIBIDA',
                solicitante: {
                  id: '00000000-0000-4000-8000-000000000108',
                  nombre: 'Vecino Real Confidencial',
                  rol: 'HOGAR',
                  telefono: '+573112223344',
                  direccion: 'Calle Real 123',
                  sector_manzana: 'Manzana B',
                  es_piloto: true,
                },
                coordinador: null,
                recolector: null,
                fecha_programada: null,
                hora_programada: null,
                puntos_otorgados: 0,
                regla_puntos_id: null,
                origen_canal: 'WHATSAPP',
                creado_en: '2026-11-21T01:00:00+00:00',
                actualizado_en: '2026-11-21T01:00:00+00:00',
              },
            ],
            total: 1,
            limit: 100,
            offset: 0,
          }),
          { status: 200 },
        )
      }
      if (url.includes('/api/recolectores')) {
        return new Response(
          JSON.stringify([
            {
              id: '550e8400-e29b-41d4-a716-446655440000',
              nombre: 'Huertero Real',
              rol: 'HUERTERO',
              telefono: '+573115556677',
              activo: true,
            },
          ]),
          { status: 200 },
        )
      }
      if (url.includes('/api/reglas-puntos')) {
        return new Response(JSON.stringify([]), { status: 200 })
      }
      return new Response('{}', { status: 404 })
    }) as typeof fetch

    try {
      const auth = await api.login('+573000000101', 'clave')
      const clean = repository.createCleanWorkspace()
      const snapshot = await loadBackendForAuthenticatedUser(auth.usuario, clean)
      assert.equal(snapshot.requests.length, 1)
      assert.equal(snapshot.members.length, 1)
      assert.equal(containsRealBackendData(snapshot), true)

      // Guardar preferencias locales durante la sesión no debe tocar datos reales
      repository.savePreferences({
        schedules: clean.schedules,
        rates: { Cartón: 820 },
        knowledge: clean.knowledge,
      })

      // Simular intento accidental de guardar estado real + cierre de sesión
      repository.save({ ...clean, requests: snapshot.requests, members: snapshot.members })
      api.logout()
      repository.purgeRealDataFromStorage()
      const afterLogout = repository.createCleanWorkspace()

      assert.equal(getStoredToken(), null)
      assert.deepEqual(afterLogout.requests, [])
      assert.deepEqual(afterLogout.members, [])
      assert.deepEqual(afterLogout.messages, [])
      assertNoRealDataInLocalStorage()
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('aborta respuestas en vuelo al cerrar sesión y limpia sesión ante token expirado (401)', async () => {
    const originalFetch = globalThis.fetch
    let unauthorizedCalls = 0
    setUnauthorizedHandler(() => {
      unauthorizedCalls += 1
    })

    // 1. Petición en vuelo cancelada con AbortController al cerrar sesión
    globalThis.fetch = ((_input: string | URL, init?: RequestInit) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'))
        })
      })) as typeof fetch

    try {
      const controller = new AbortController()
      const pending = api.listarSolicitudes({ limit: 10 }, controller.signal)
      controller.abort()
      await assert.rejects(pending, (err: unknown) => {
        return err instanceof ApiError && err.codigo === 'ABORTADO'
      })
      assert.equal(unauthorizedCalls, 0)

      // 2. Expiración de token (401 TOKEN_EXPIRADO) dispara limpieza y borra el JWT
      sessionMap.set('ecoconecta_access_token', 'jwt-expirado')
      globalThis.fetch = (async () =>
        new Response(
          JSON.stringify({
            detail: { codigo: 'TOKEN_EXPIRADO', mensaje: 'Token expirado.' },
          }),
          { status: 401 },
        )) as typeof fetch

      await assert.rejects(api.me(), (err: unknown) => {
        return err instanceof ApiError && err.status === 401 && err.codigo === 'TOKEN_EXPIRADO'
      })
      assert.equal(getStoredToken(), null)
      assert.equal(unauthorizedCalls, 1)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})
