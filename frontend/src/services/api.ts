/**
 * Cliente HTTP tipado para la API FastAPI de EcoConecta.
 * Fuente de verdad del contrato: backend/API_CONTRATO.md
 */

export type RolUsuario =
  | 'HOGAR'
  | 'UNIDAD_PRODUCTIVA'
  | 'COORD_HUERTEROS'
  | 'HUERTERO'
  | 'COORD_RECICLADORES'
  | 'RECICLADOR'
  | 'ADMIN'

export type FlujoResiduo = 'ORGANICO' | 'RECICLABLE'

export type EstadoSolicitud =
  | 'RECIBIDA'
  | 'EN_REVISION'
  | 'ASIGNADA'
  | 'PROGRAMADA'
  | 'RECOLECTADA'
  | 'CANCELADA'

export type TipoGenerador = 'HOGAR' | 'UNIDAD_PRODUCTIVA'

export interface UsuarioApi {
  id: string
  nombre: string
  telefono: string
  rol: RolUsuario
  direccion: string | null
  sector_manzana: string | null
  es_piloto: boolean
  puntos_acumulados: number
  activo: boolean
  creado_en: string
}

export interface TokenResponseApi {
  access_token: string
  token_type: 'bearer'
  expira_en_segundos: number
  usuario: UsuarioApi
}

export interface UsuarioResumenApi {
  id: string
  nombre: string
  rol: RolUsuario
}

export interface ContactoSolicitanteApi extends UsuarioResumenApi {
  telefono: string | null
  direccion: string | null
  sector_manzana: string | null
  es_piloto: boolean
}

export interface RecolectorCatalogoApi {
  id: string
  nombre: string
  rol: 'HUERTERO' | 'RECICLADOR'
  telefono: string
  activo: boolean
}

export interface SolicitudApi {
  id: number
  codigo_publico: string
  flujo: FlujoResiduo
  subtipo_material: string | null
  cantidad_estimada_kg: number | null
  cantidad_real_kg: number | null
  disponibilidad_usuario: string
  observaciones: string | null
  estado: EstadoSolicitud
  solicitante: ContactoSolicitanteApi
  coordinador: UsuarioResumenApi | null
  recolector: UsuarioResumenApi | null
  fecha_programada: string | null
  hora_programada: string | null
  puntos_otorgados: number
  regla_puntos_id: number | null
  creado_en: string
  actualizado_en: string
}

export interface SolicitudListApi {
  items: SolicitudApi[]
  total: number
  limit: number
  offset: number
}

export interface HistorialEstadoApi {
  id: number
  estado_anterior: EstadoSolicitud | null
  estado_nuevo: EstadoSolicitud
  actor: UsuarioResumenApi | null
  nota_operativa: string | null
  fecha_cambio: string
}

export interface CalculoPuntosApi {
  regla_puntos_id: number
  flujo: FlujoResiduo
  tipo_generador: TipoGenerador
  puntos_base_solicitud: number
  puntos_por_kg: number
  cantidad_real_kg: number
  puntos_otorgados: number
  formula: string
  nota_fsd: string
}

export interface CierreSolicitudApi extends SolicitudApi {
  calculo_puntos: CalculoPuntosApi
}

export interface ReglaPuntosApi {
  id: number
  flujo: FlujoResiduo
  tipo_generador: TipoGenerador
  puntos_base_solicitud: number
  puntos_por_kg: number
  valor_referencia_kg_cop: number
  descripcion_regla: string | null
  activa: boolean
  actualizado_en: string
}

export interface UsuarioListApi {
  items: UsuarioApi[]
  total: number
  limit: number
  offset: number
}

export interface ContenidoEducativoApi {
  id: number
  titulo: string
  categoria: 'ORGANICO' | 'RECICLABLE' | 'HUERTA' | 'RUTAS'
  resumen: string
  que_si_va: string | null
  que_no_va: string | null
  orden: number
}

export interface ErrorCampoApi {
  campo: string
  mensaje: string
  tipo: string
}

export class ApiError extends Error {
  status: number
  codigo: string
  errores?: ErrorCampoApi[]

  constructor(status: number, codigo: string, mensaje: string, errores?: ErrorCampoApi[]) {
    super(mensaje)
    this.name = 'ApiError'
    this.status = status
    this.codigo = codigo
    this.errores = errores
  }
}

export const ESTADOS_SOLICITUD_LABELS: Record<EstadoSolicitud, string> = {
  RECIBIDA: 'Recibida',
  EN_REVISION: 'En revisión',
  ASIGNADA: 'Asignada',
  PROGRAMADA: 'Programada',
  RECOLECTADA: 'Recolectada',
  CANCELADA: 'Cancelada',
}

export const ROLES_LABELS: Record<RolUsuario, string> = {
  HOGAR: 'Hogar',
  UNIDAD_PRODUCTIVA: 'Unidad Productiva',
  COORD_HUERTEROS: 'Coordinador de Huerteros',
  HUERTERO: 'Huertero',
  COORD_RECICLADORES: 'Coordinador de Recicladores',
  RECICLADOR: 'Reciclador',
  ADMIN: 'Administrador',
}

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')

const TOKEN_STORAGE_KEY = 'ecoconecta_access_token'

export function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  } catch {
    // Sin acceso a sessionStorage
  }
}

let unauthorizedHandler: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

async function request<T>(
  path: string,
  options: {
    method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
    body?: unknown
    auth?: boolean
    query?: Record<string, string | number | boolean | undefined | null>
  } = {},
): Promise<T> {
  const { method = 'GET', body, auth = true, query } = options
  const url = new URL(`${API_BASE_URL}${path}`)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
  }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (auth) {
    const token = getStoredToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }

  let response: Response
  try {
    response = await fetch(url.toString(), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(
      0,
      'ERROR_RED',
      `No se pudo conectar con la API en ${API_BASE_URL}. Verifica que el backend esté activo.`,
    )
  }

  const rawText = await response.text()
  let parsed: unknown = null
  if (rawText) {
    try {
      parsed = JSON.parse(rawText)
    } catch {
      parsed = null
    }
  }

  if (!response.ok) {
    const detail = (parsed as { detail?: { codigo?: string; mensaje?: string; errores?: ErrorCampoApi[] } | string } | null)?.detail
    let codigo = 'ERROR_HTTP'
    let mensaje = `Error ${response.status} al comunicarse con la API.`
    let errores: ErrorCampoApi[] | undefined

    if (detail && typeof detail === 'object') {
      codigo = detail.codigo || codigo
      mensaje = detail.mensaje || mensaje
      errores = Array.isArray(detail.errores) ? detail.errores : undefined
      if (errores?.length && codigo === 'VALIDACION') {
        const campos = errores.map(e => `${e.campo}: ${e.mensaje}`).join(' · ')
        mensaje = `${mensaje} (${campos})`
      }
    } else if (typeof detail === 'string') {
      mensaje = detail
    }

    if (response.status === 401 && auth && (codigo === 'TOKEN_EXPIRADO' || codigo === 'TOKEN_INVALIDO' || codigo === 'NO_AUTENTICADO')) {
      setStoredToken(null)
      unauthorizedHandler?.()
    }

    throw new ApiError(response.status, codigo, mensaje, errores)
  }

  return parsed as T
}

export type Aviso = { id: number; evento: string; destinatario: string; estado: string; error: string | null }
export const api = {
  avisos: (id: number) => request<Aviso[]>(`/api/solicitudes/${id}/avisos`),
  reintentarAviso: (id: number, aviso: number) =>
    request(`/api/solicitudes/${id}/avisos/${aviso}/reintentar`, { method: 'POST' }),
  // Autenticación
  async login(telefono: string, password: string): Promise<TokenResponseApi> {
    const res = await request<TokenResponseApi>('/api/auth/login', {
      method: 'POST',
      auth: false,
      body: { telefono: telefono.trim(), password },
    })
    setStoredToken(res.access_token)
    return res
  },

  async demoLogin(rol: RolUsuario): Promise<TokenResponseApi> {
    const res = await request<TokenResponseApi>('/api/auth/demo-login', {
      method: 'POST',
      auth: false,
      body: { rol },
    })
    setStoredToken(res.access_token)
    return res
  },

  me(): Promise<UsuarioApi> {
    return request<UsuarioApi>('/api/auth/me')
  },

  logout(): void {
    setStoredToken(null)
  },

  // Catálogos
  listarRecolectores(flujo?: FlujoResiduo): Promise<RecolectorCatalogoApi[]> {
    return request<RecolectorCatalogoApi[]>('/api/recolectores', {
      query: { flujo },
    })
  },

  listarReglasActivas(): Promise<ReglaPuntosApi[]> {
    return request<ReglaPuntosApi[]>('/api/reglas-puntos')
  },

  listarContenidosEducativos(categoria?: string): Promise<ContenidoEducativoApi[]> {
    return request<ContenidoEducativoApi[]>('/api/contenidos-educativos', {
      query: { categoria },
    })
  },

  // Solicitudes
  listarSolicitudes(params?: {
    flujo?: FlujoResiduo
    estado?: EstadoSolicitud
    limit?: number
    offset?: number
  }): Promise<SolicitudListApi> {
    return request<SolicitudListApi>('/api/solicitudes', {
      query: {
        flujo: params?.flujo,
        estado: params?.estado,
        limit: params?.limit ?? 100,
        offset: params?.offset ?? 0,
      },
    })
  },

  obtenerSolicitud(id: number): Promise<SolicitudApi> {
    return request<SolicitudApi>(`/api/solicitudes/${id}`)
  },

  obtenerHistorial(id: number): Promise<HistorialEstadoApi[]> {
    return request<HistorialEstadoApi[]>(`/api/solicitudes/${id}/historial`)
  },

  crearSolicitud(payload: {
    flujo: FlujoResiduo
    subtipo_material?: string | null
    cantidad_estimada_kg?: number | null
    disponibilidad_usuario: string
    observaciones?: string | null
  }): Promise<SolicitudApi> {
    return request<SolicitudApi>('/api/solicitudes', {
      method: 'POST',
      body: payload,
    })
  },

  revisarSolicitud(id: number, nota_operativa?: string | null): Promise<SolicitudApi> {
    return request<SolicitudApi>(`/api/solicitudes/${id}/revisar`, {
      method: 'POST',
      body: { nota_operativa: nota_operativa?.trim() || null },
    })
  },

  asignarSolicitud(id: number, recolector_id: string, nota_operativa?: string | null): Promise<SolicitudApi> {
    return request<SolicitudApi>(`/api/solicitudes/${id}/asignar`, {
      method: 'POST',
      body: {
        recolector_id,
        nota_operativa: nota_operativa?.trim() || null,
      },
    })
  },

  programarSolicitud(
    id: number,
    payload: {
      recolector_id: string
      fecha_programada: string
      hora_programada: string
      nota_operativa?: string | null
    },
  ): Promise<SolicitudApi> {
    return request<SolicitudApi>(`/api/solicitudes/${id}/programar`, {
      method: 'PATCH',
      body: {
        recolector_id: payload.recolector_id,
        fecha_programada: payload.fecha_programada,
        hora_programada: payload.hora_programada,
        nota_operativa: payload.nota_operativa?.trim() || null,
      },
    })
  },

  cerrarSolicitud(
    id: number,
    payload: {
      cantidad_real_kg: number
      nota_operativa?: string | null
    },
  ): Promise<CierreSolicitudApi> {
    return request<CierreSolicitudApi>(`/api/solicitudes/${id}/cerrar`, {
      method: 'POST',
      body: {
        cantidad_real_kg: payload.cantidad_real_kg,
        nota_operativa: payload.nota_operativa?.trim() || null,
      },
    })
  },

  cancelarSolicitud(id: number, motivo: string): Promise<SolicitudApi> {
    return request<SolicitudApi>(`/api/solicitudes/${id}/cancelar`, {
      method: 'POST',
      body: { motivo: motivo.trim() },
    })
  },

  // Administración (ADMIN)
  adminListarReglas(params?: {
    flujo?: FlujoResiduo
    tipo_generador?: TipoGenerador
    activa?: boolean
    limit?: number
    offset?: number
  }): Promise<ReglaPuntosApi[]> {
    return request<ReglaPuntosApi[]>('/api/admin/reglas-puntos', {
      query: {
        flujo: params?.flujo,
        tipo_generador: params?.tipo_generador,
        activa: params?.activa,
        limit: params?.limit ?? 100,
        offset: params?.offset ?? 0,
      },
    })
  },

  adminCrearRegla(payload: {
    flujo: FlujoResiduo
    tipo_generador: TipoGenerador
    puntos_base_solicitud: number
    puntos_por_kg: number
    valor_referencia_kg_cop: number
    descripcion_regla?: string | null
    activa?: boolean
  }): Promise<ReglaPuntosApi> {
    return request<ReglaPuntosApi>('/api/admin/reglas-puntos', {
      method: 'POST',
      body: payload,
    })
  },

  adminActualizarRegla(
    id: number,
    payload: {
      puntos_base_solicitud?: number
      puntos_por_kg?: number
      valor_referencia_kg_cop?: number
      descripcion_regla?: string | null
      activa?: boolean
    },
  ): Promise<ReglaPuntosApi> {
    return request<ReglaPuntosApi>(`/api/admin/reglas-puntos/${id}`, {
      method: 'PATCH',
      body: payload,
    })
  },

  adminListarUsuarios(params?: {
    rol?: RolUsuario
    es_piloto?: boolean
    activo?: boolean
    q?: string
    limit?: number
    offset?: number
  }): Promise<UsuarioListApi> {
    return request<UsuarioListApi>('/api/admin/usuarios', {
      query: {
        rol: params?.rol,
        es_piloto: params?.es_piloto,
        activo: params?.activo,
        q: params?.q,
        limit: params?.limit ?? 100,
        offset: params?.offset ?? 0,
      },
    })
  },

  adminCambiarPiloto(usuarioId: string, es_piloto: boolean): Promise<UsuarioApi> {
    return request<UsuarioApi>(`/api/admin/usuarios/${usuarioId}/piloto`, {
      method: 'PATCH',
      body: { es_piloto },
    })
  },
}
