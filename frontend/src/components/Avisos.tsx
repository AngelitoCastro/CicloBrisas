import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCheck, Clock, MessageCircle, RefreshCw, RotateCcw, Send } from 'lucide-react'
import { api, ApiError, type Aviso } from '../services/api'

const ESTADO_META: Record<string, { label: string; tone: string; detalle?: string }> = {
  PENDIENTE: { label: 'En cola de envío', tone: 'pendiente' },
  CONCILIAR: {
    label: 'Pendiente de conciliación',
    tone: 'pendiente',
    detalle: 'Resultado incierto: esperando confirmación del proveedor antes de reenviar.',
  },
  ACEPTADO: { label: 'Aceptado por WhatsApp', tone: 'autorizada' },
  ENVIADO: { label: 'Enviado', tone: 'autorizada' },
  ENTREGADO: { label: 'Entregado', tone: 'completada' },
  LEIDO: { label: 'Leído', tone: 'completada' },
  FALLIDO: { label: 'Fallo confirmado', tone: 'rechazada' },
  SIN_CONSENTIMIENTO: {
    label: 'Sin consentimiento vigente',
    tone: 'rechazada',
    detalle:
      'No se envió porque el destinatario no tiene consentimiento explícito y vigente para WhatsApp.',
  },
  SUSTITUIDO: { label: 'Sustituido por reprogramación', tone: 'pendiente' },
}

const DESTINATARIO_LABEL: Record<string, string> = {
  RECOLECTOR: 'Recolector',
  SOLICITANTE: 'Solicitante',
}

const EVENTO_LABEL: Record<string, string> = {
  PROGRAMADA: 'Programación',
  RECOLECTADA: 'Cierre',
}

export default function Avisos({ solicitud, refreshKey = 0 }: { solicitud: number; refreshKey?: number }) {
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)
  const [revision, setRevision] = useState(0)
  const [ocupadoId, setOcupadoId] = useState<number | null>(null)

  useEffect(() => {
    let activo = true
    const controller = new AbortController()
    setCargando(true)
    api
      .avisos(solicitud, controller.signal)
      .then(filas => {
        if (activo) {
          setAvisos(filas)
          setError('')
        }
      })
      .catch(err => {
        if (activo && !(err instanceof ApiError && err.codigo === 'ABORTADO')) {
          setError(err instanceof ApiError ? err.message : 'No se pudieron consultar los avisos.')
        }
      })
      .finally(() => {
        if (activo) setCargando(false)
      })
    return () => {
      activo = false
      controller.abort()
    }
  }, [solicitud, revision, refreshKey])

  async function reintentar(id: number) {
    setOcupadoId(id)
    setError('')
    try {
      await api.reintentarAviso(solicitud, id)
      setRevision(n => n + 1)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'No se pudo reintentar el aviso. Actualiza su estado.',
      )
      setRevision(n => n + 1)
    } finally {
      setOcupadoId(null)
    }
  }

  return (
    <section className="rounded-xl border border-[#cfd9cf] bg-[#f8faf7] p-3 space-y-2" aria-label="Estado de avisos WhatsApp">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <MessageCircle size={17} aria-hidden="true" />
          <h3>Estado del aviso WhatsApp</h3>
        </div>
        <button
          type="button"
          className="btn"
          style={{ minHeight: 36, padding: '6px 10px' }}
          disabled={cargando}
          onClick={() => setRevision(n => n + 1)}
        >
          <RefreshCw size={14} aria-hidden="true" />
          {cargando ? 'Actualizando…' : 'Actualizar estado'}
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!cargando && avisos.length === 0 && !error && (
        <p className="muted">No hay avisos de WhatsApp registrados para esta solicitud.</p>
      )}
      <div className="space-y-2">
        {avisos.map(a => {
          const meta = ESTADO_META[a.estado] ?? { label: a.estado, tone: 'pendiente' }
          const Icon =
            a.estado === 'ENTREGADO' || a.estado === 'LEIDO'
              ? CheckCheck
              : a.estado === 'FALLIDO' || a.estado === 'SIN_CONSENTIMIENTO'
                ? AlertTriangle
                : a.estado === 'ACEPTADO' || a.estado === 'ENVIADO'
                  ? Send
                  : Clock
          return (
            <div
              key={a.id}
              className="rounded-lg border border-[#dce4dc] bg-white p-2.5 flex flex-wrap items-center justify-between gap-2"
            >
              <div className="space-y-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <strong>
                    {DESTINATARIO_LABEL[a.destinatario] ?? a.destinatario} · {EVENTO_LABEL[a.evento] ?? a.evento}
                  </strong>
                  <span className={'status ' + meta.tone}>
                    <Icon size={13} aria-hidden="true" />
                    {meta.label}
                  </span>
                </div>
                {meta.detalle && <p className="muted">{meta.detalle}</p>}
                {a.error && (
                  <p className="muted">
                    Código del proveedor: <strong>{a.error}</strong>
                  </p>
                )}
              </div>
              {a.estado === 'FALLIDO' && (
                <button
                  type="button"
                  className="btn"
                  disabled={ocupadoId === a.id}
                  onClick={() => reintentar(a.id)}
                >
                  <RotateCcw size={15} aria-hidden="true" />
                  {ocupadoId === a.id ? 'Reintentando…' : 'Reintentar aviso'}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
