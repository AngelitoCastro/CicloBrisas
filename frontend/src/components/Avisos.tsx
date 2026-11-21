import { useEffect, useState } from 'react'
import { api, type Aviso } from '../services/api'

export default function Avisos({ solicitud }: { solicitud: number }) {
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [ocupado, setOcupado] = useState(false)
  useEffect(() => {
    let activo = true
    api.avisos(solicitud).then(filas => {
      if (activo) { setAvisos(filas); setError('') }
    }).catch(() => { if (activo) setError('No se pudieron consultar los avisos.') })
    return () => { activo = false }
  }, [solicitud, revision])
  async function reintentar(id: number) {
    setOcupado(true)
    try { await api.reintentarAviso(solicitud, id); setRevision(n => n + 1) }
    catch { setError('No se pudo reintentar el aviso. Actualiza su estado.') }
    finally { setOcupado(false) }
  }
  return <section aria-label="Avisos de WhatsApp">
    <button type="button" onClick={() => setRevision(n => n + 1)}>Actualizar avisos de WhatsApp</button>
    {error && <p role="alert">{error}</p>}
    {avisos.map(a => <p key={a.id}>{a.evento} · {a.destinatario}: {a.estado}
      {a.error && <> ({a.error})</>}
      {a.estado === 'FALLIDO' && <button type="button" disabled={ocupado} onClick={() => reintentar(a.id)}>Reintentar aviso</button>}
    </p>)}
  </section>
}
