import {
  api,
  ApiError,
  type EstadoSolicitud,
  type FlujoResiduo,
  type HistorialEstadoApi,
  type RecolectorCatalogoApi,
  type ReglaPuntosApi,
  type RolUsuario,
  type SolicitudApi,
  type TipoGenerador,
} from './api'
import { getCollectionClock } from './collectionSchedule'
import { loadPointRules } from './pointRules'
import type {
  Data,
  EcoPointRules,
  Flow,
  Generator,
  Member,
  Request,
  Role,
  Status,
} from '../types'

export const ROLE_TO_API_ROLE: Record<Role, RolUsuario> = {
  huerta: 'COORD_HUERTEROS',
  reciclaje: 'COORD_RECICLADORES',
  admin: 'ADMIN',
}

function apiFlowToUi(flujo: FlujoResiduo): Flow {
  return flujo === 'ORGANICO' ? 'organico' : 'reciclable'
}

function uiFlowToApi(flow: Flow): FlujoResiduo {
  return flow === 'organico' ? 'ORGANICO' : 'RECICLABLE'
}

function apiGeneratorToUi(rol: string): Generator {
  return rol === 'UNIDAD_PRODUCTIVA' ? 'Comercio' : 'Hogar'
}

function uiGeneratorToApi(generator: Generator): TipoGenerador {
  return generator === 'Comercio' ? 'UNIDAD_PRODUCTIVA' : 'HOGAR'
}

function apiStatusToUi(estado: EstadoSolicitud): Status {
  switch (estado) {
    case 'RECIBIDA':
      return 'pendiente'
    case 'EN_REVISION':
    case 'ASIGNADA':
      return 'autorizada'
    case 'PROGRAMADA':
      return 'programada'
    case 'RECOLECTADA':
      return 'completada'
    case 'CANCELADA':
      return 'rechazada'
  }
}

function formatBogotaDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Bogota',
  }).format(date)
}

function mapHistoryEntries(entries: HistorialEstadoApi[]): string[] {
  return entries.map(entry => {
    const actor = entry.actor?.nombre ? ` (${entry.actor.nombre})` : ''
    const note = entry.nota_operativa ? ` · ${entry.nota_operativa}` : ''
    return `${formatBogotaDateTime(entry.fecha_cambio)} · ${entry.estado_nuevo}${actor}${note}`
  })
}

export function mapSolicitudToRequest(
  s: SolicitudApi,
  historyEntries?: HistorialEstadoApi[],
  reglas?: ReglaPuntosApi[],
  previous?: Request,
): Request {
  const flow = apiFlowToUi(s.flujo)
  const status = apiStatusToUi(s.estado)
  const matchedRule = s.regla_puntos_id
    ? reglas?.find(r => r.id === s.regla_puntos_id)
    : undefined

  return {
    id: s.codigo_publico,
    backendId: s.id,
    flow,
    kind: 'residuo',
    name: s.solicitante.nombre,
    phone: s.solicitante.telefono ?? '',
    address:
      [s.solicitante.direccion, s.solicitante.sector_manzana]
        .filter(Boolean)
        .join(' · ') || 'Sin dirección registrada',
    generator: apiGeneratorToUi(s.solicitante.rol),
    pilot: Boolean(s.solicitante.es_piloto),
    description: s.subtipo_material || s.observaciones || 'Residuos para recolección',
    evidence: previous?.evidence ?? '',
    estKg: s.cantidad_estimada_kg ?? 0,
    units: 0,
    delivery: 'recoger',
    preference: s.disponibilidad_usuario,
    status,
    source: 'WhatsApp',
    assignee: s.recolector?.id ?? previous?.assignee,
    date: s.fecha_programada ?? undefined,
    time: s.hora_programada ?? undefined,
    note: s.observaciones ?? undefined,
    lines: previous?.lines ?? [],
    acceptedKg: s.cantidad_real_kg ?? undefined,
    confirmation:
      status === 'completada'
        ? previous?.confirmation ?? {
            source: 'manual',
            at: s.actualizado_en,
            confirmedBy:
              s.recolector?.nombre ?? s.coordinador?.nombre ?? 'Backend EcoConecta',
          }
        : undefined,
    ecoPoints: status === 'completada' ? s.puntos_otorgados : undefined,
    ecoPointRule: matchedRule
      ? {
          base: matchedRule.puntos_base_solicitud,
          perKg: matchedRule.puntos_por_kg,
        }
      : previous?.ecoPointRule,
    rejected: status === 'rechazada' ? previous?.rejected : undefined,
    history:
      historyEntries && historyEntries.length > 0
        ? mapHistoryEntries(historyEntries)
        : previous?.history?.length
          ? previous.history
          : [`Solicitud ${s.codigo_publico} (${s.estado})`],
    created: s.creado_en.slice(0, 10),
  }
}

export function mapRecolectoresToMembers(
  recolectores: RecolectorCatalogoApi[],
): Member[] {
  return recolectores.map(r => ({
    id: r.id,
    name: r.nombre,
    phone: r.telefono,
    flow: r.rol === 'HUERTERO' ? 'organico' : 'reciclable',
    group: r.rol === 'HUERTERO' ? 'Colectivo Huerta' : 'Colectivo Reciclaje',
    active: r.activo,
  }))
}

export function mapReglasToPointRules(reglas: ReglaPuntosApi[]): {
  pointRules: EcoPointRules
  ruleIds: Record<string, number>
} {
  const partial: Partial<
    Record<Flow, Partial<Record<Generator, { base: number; perKg: number }>>>
  > = {}
  const ruleIds: Record<string, number> = {}

  for (const r of reglas) {
    if (!r.activa) continue
    const flow = apiFlowToUi(r.flujo)
    const gen = apiGeneratorToUi(r.tipo_generador)
    partial[flow] = partial[flow] ?? {}
    partial[flow]![gen] = {
      base: r.puntos_base_solicitud,
      perKg: r.puntos_por_kg,
    }
    ruleIds[`${flow}:${gen}`] = r.id
  }

  return {
    pointRules: loadPointRules(partial),
    ruleIds,
  }
}

function addMinutes(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number)
  const total = Math.min(23 * 60 + 59, h * 60 + m + minutes)
  const nh = Math.floor(total / 60)
  const nm = total % 60
  return `${String(nh).padStart(2, '0')}:${String(nm).padStart(2, '0')}`
}

function extractApiTime(slotText: string | undefined, date: string): string {
  const matches = (slotText || '').match(/\d{2}:\d{2}/g) ?? []
  const start = matches[0] || '09:00'
  const end = matches[1]
  const clock = getCollectionClock()

  if (date === clock.today && start <= clock.time) {
    const bumped = addMinutes(clock.time, 5)
    if (end && bumped < end) return bumped
    if (end && end > clock.time) return end
    return bumped
  }
  return start
}

export interface BackendSnapshot {
  requests: Request[]
  members: Member[]
  pointRules: EcoPointRules
  ruleIds: Record<string, number>
  reglasRaw: ReglaPuntosApi[]
}

export async function loadBackendForRole(
  role: Role,
  previousData: Data,
): Promise<BackendSnapshot> {
  await api.demoLogin(ROLE_TO_API_ROLE[role])
  const [solicitudesRes, recolectores, reglas] = await Promise.all([
    api.listarSolicitudes({ limit: 100 }),
    api.listarRecolectores(),
    role === 'admin'
      ? api.adminListarReglas({ activa: true, limit: 100 })
      : api.listarReglasActivas(),
  ])

  const historiales = await Promise.all(
    solicitudesRes.items.map(s =>
      api.obtenerHistorial(s.id).catch(() => [] as HistorialEstadoApi[]),
    ),
  )

  const prevById = new Map(previousData.requests.map(r => [r.id, r]))
  const requests = solicitudesRes.items.map((s, idx) =>
    mapSolicitudToRequest(s, historiales[idx], reglas, prevById.get(s.codigo_publico)),
  )
  const members = mapRecolectoresToMembers(recolectores)
  const { pointRules, ruleIds } = mapReglasToPointRules(reglas)

  return { requests, members, pointRules, ruleIds, reglasRaw: reglas }
}

export async function syncTransitionToBackend(
  previous: Request | undefined,
  next: Request,
  reglasRaw: ReglaPuntosApi[],
): Promise<{ updated: Request; message: string } | null> {
  if (!next.backendId) {
    return null
  }
  const backendId = next.backendId

  // 1. Pendiente -> Autorizada (RECIBIDA -> EN_REVISION)
  if (previous?.status === 'pendiente' && next.status === 'autorizada') {
    const res = await api.revisarSolicitud(backendId, next.note)
    const hist = await api.obtenerHistorial(backendId).catch(() => [])
    return {
      updated: mapSolicitudToRequest(res, hist, reglasRaw, next),
      message: `Solicitud ${res.codigo_publico} marcada en revisión en el backend.`,
    }
  }

  // 2. Programar o reprogramar (-> PROGRAMADA)
  if (
    next.status === 'programada' &&
    next.assignee &&
    next.date &&
    (previous?.status !== 'programada' ||
      previous.assignee !== next.assignee ||
      previous.date !== next.date ||
      previous.time !== next.time ||
      previous.note !== next.note)
  ) {
    const hora = extractApiTime(next.time, next.date)
    const res = await api.programarSolicitud(backendId, {
      recolector_id: next.assignee,
      fecha_programada: next.date,
      hora_programada: hora,
      nota_operativa: next.note,
    })
    const hist = await api.obtenerHistorial(backendId).catch(() => [])
    return {
      updated: mapSolicitudToRequest(res, hist, reglasRaw, {
        ...next,
        time: res.hora_programada ?? hora,
      }),
      message: `Solicitud ${res.codigo_publico} programada en PostgreSQL (${res.fecha_programada} ${res.hora_programada ?? hora}).`,
    }
  }

  // 3. Cierre (PROGRAMADA -> RECOLECTADA)
  if (previous?.status === 'programada' && next.status === 'completada') {
    const kg =
      next.acceptedKg ??
      next.lines?.reduce((sum, l) => sum + l.kg, 0) ??
      0
    if (kg <= 0) {
      throw new ApiError(
        422,
        'CANTIDAD_INVALIDA',
        'El backend exige un peso real mayor a 0 kg para cerrar y acreditar EcoPuntos.',
      )
    }
    const res = await api.cerrarSolicitud(backendId, {
      cantidad_real_kg: kg,
      nota_operativa: next.note || 'Cierre registrado desde el panel coordinador.',
    })
    const hist = await api.obtenerHistorial(backendId).catch(() => [])
    const mapped = mapSolicitudToRequest(res, hist, reglasRaw, next)
    mapped.ecoPoints = res.puntos_otorgados
    mapped.ecoPointRule = {
      base: res.calculo_puntos.puntos_base_solicitud,
      perKg: res.calculo_puntos.puntos_por_kg,
    }
    return {
      updated: mapped,
      message: `Cierre guardado en PostgreSQL · ${res.puntos_otorgados.toLocaleString('es-CO')} EcoPuntos acreditados (${res.calculo_puntos.formula}).`,
    }
  }

  // 4. Cancelación / rechazo (-> CANCELADA)
  if (previous?.status !== 'rechazada' && next.status === 'rechazada') {
    const motivo =
      next.rejected && next.rejected.trim().length >= 5
        ? next.rejected.trim()
        : 'Cancelada por coordinación desde el panel.'
    const res = await api.cancelarSolicitud(backendId, motivo)
    const hist = await api.obtenerHistorial(backendId).catch(() => [])
    return {
      updated: mapSolicitudToRequest(res, hist, reglasRaw, next),
      message: `Solicitud ${res.codigo_publico} cancelada en el backend.`,
    }
  }

  return null
}

export async function savePointRulesToBackend(
  nextRules: EcoPointRules,
  ruleIds: Record<string, number>,
  reglasRaw: ReglaPuntosApi[],
): Promise<ReglaPuntosApi[]> {
  const flows: Flow[] = ['organico', 'reciclable']
  const generators: Generator[] = ['Hogar', 'Comercio']

  for (const flow of flows) {
    for (const generator of generators) {
      const rule = nextRules[flow][generator]
      const key = `${flow}:${generator}`
      const id = ruleIds[key]
      const existing = reglasRaw.find(r => r.id === id)
      if (id) {
        await api.adminActualizarRegla(id, {
          puntos_base_solicitud: rule.base,
          puntos_por_kg: rule.perKg,
          valor_referencia_kg_cop: existing?.valor_referencia_kg_cop ?? 80,
          activa: true,
        })
      } else {
        await api.adminCrearRegla({
          flujo: uiFlowToApi(flow),
          tipo_generador: uiGeneratorToApi(generator),
          puntos_base_solicitud: rule.base,
          puntos_por_kg: rule.perKg,
          valor_referencia_kg_cop: 80,
          descripcion_regla: `Regla ${flow} (${generator}).`,
          activa: true,
        })
      }
    }
  }

  return api.adminListarReglas({ activa: true, limit: 100 })
}
