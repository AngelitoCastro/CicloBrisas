import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Sprout,
  Recycle,
  Shield,
  ClipboardList,
  Users,
  History,
  Settings,
  BookOpen,
  LogOut,
  Scale,
  LayoutDashboard,
  BrainCircuit,
  Award,
  KeyRound,
} from 'lucide-react'
import { Brand, InstitutionalLogos } from './components/UI'
import {
  api,
  ApiError,
  getStoredToken,
  setUnauthorizedHandler,
  type ReglaPuntosApi,
  type UsuarioApi,
} from './services/api'
import {
  loadBackendForAuthenticatedUser,
  loadBackendForRole,
  savePointRulesToBackend,
  syncTransitionToBackend,
} from './services/backendBridge'
import { repository } from './services/repository'
import { applyRequestUpdate, type DemoNotice } from './services/requestUpdates'
import { type Role, type Flow, type Data, type Request, type Status, kgOf } from './types'
import Collections from './pages/Collections'
import PointRulesPage from './pages/PointRules'
import { Team, SettingsPage, Reports, KnowledgePage, Training } from './pages/Management'

const DEMO_LOGIN_ENABLED =
  String(import.meta.env.VITE_ENABLE_DEMO_LOGIN || '').toLowerCase() === 'true'

const roles = [
  {
    id: 'huerta' as const,
    title: 'Coordinador de Huerta',
    desc: 'Orgánicos, entregas directas y donaciones',
    icon: Sprout,
  },
  {
    id: 'reciclaje' as const,
    title: 'Coordinador de Reciclaje',
    desc: 'Aprovechables, recolecciones y tarifas',
    icon: Recycle,
  },
  {
    id: 'admin' as const,
    title: 'Administrador',
    desc: 'Gestión general, horarios y resultados',
    icon: Shield,
  },
]

export default function App() {
  // Inicia siempre con espacio limpio (solo preferencias locales, nunca datos reales en localStorage).
  const [data, setData] = useState<Data>(() => repository.createCleanWorkspace())
  const [role, setRole] = useState<Role | null>(null)
  const [usuario, setUsuario] = useState<UsuarioApi | null>(null)
  const [backendConnected, setBackendConnected] = useState(false)
  const [ruleIds, setRuleIds] = useState<Record<string, number>>({})
  const [reglasRaw, setReglasRaw] = useState<ReglaPuntosApi[]>([])
  const [page, setPage] = useState('Recolecciones')
  const [toast, setToast] = useState('')

  const [phoneInput, setPhoneInput] = useState('')
  const [passwordInput, setPasswordInput] = useState('')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(() => Boolean(getStoredToken()))

  // Control de generación de sesión y cancelación para descartar respuestas en vuelo al cerrar/expirar sesión.
  const sessionEpochRef = useRef(0)
  const sessionAbortRef = useRef<AbortController | null>(null)
  const dataRef = useRef(data)
  dataRef.current = data

  const notify = useCallback((s: string) => setToast(s), [])

  const beginSessionAttempt = useCallback(() => {
    sessionAbortRef.current?.abort()
    const controller = new AbortController()
    sessionAbortRef.current = controller
    sessionEpochRef.current += 1
    return { epoch: sessionEpochRef.current, controller, signal: controller.signal }
  }, [])

  const applySnapshot = useCallback(
    (
      snapshot: Awaited<ReturnType<typeof loadBackendForAuthenticatedUser>>,
      epoch: number,
      initial = false,
    ) => {
      if (sessionEpochRef.current !== epoch) return false
      setData(current => ({
        ...current,
        requests: snapshot.requests,
        members: snapshot.members,
        pointRules: snapshot.pointRules,
        messages: [],
        intakeRecords: initial ? [] : current.intakeRecords,
      }))
      setRuleIds(snapshot.ruleIds)
      setReglasRaw(snapshot.reglasRaw)
      setUsuario(snapshot.usuario)
      setRole(snapshot.role)
      setBackendConnected(true)
      if (initial) {
        setPage(snapshot.role === 'admin' ? 'Resumen' : 'Recolecciones')
      }
      return true
    },
    [],
  )

  const handleLogout = useCallback((mensaje?: string) => {
    // Invalida y aborta cualquier petición pendiente de la sesión que termina.
    sessionEpochRef.current += 1
    sessionAbortRef.current?.abort()
    sessionAbortRef.current = null
    api.logout()
    repository.purgeRealDataFromStorage()
    setData(repository.createCleanWorkspace())
    setRole(null)
    setUsuario(null)
    setBackendConnected(false)
    setRuleIds({})
    setReglasRaw([])
    setPasswordInput('')
    setAuthLoading(false)
    if (mensaje) setAuthError(mensaje)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      handleLogout('Tu sesión expiró. Vuelve a iniciar sesión.')
    })
    return () => setUnauthorizedHandler(null)
  }, [handleLogout])

  // Restaurar sesión JWT existente en sessionStorage descartando respuestas si se cierra sesión antes de resolver.
  useEffect(() => {
    repository.purgeRealDataFromStorage()
    if (!getStoredToken()) {
      setAuthLoading(false)
      return
    }
    const { epoch, controller, signal } = beginSessionAttempt()
    api
      .me(signal)
      .then(me => {
        if (sessionEpochRef.current !== epoch) return null
        return loadBackendForAuthenticatedUser(me, repository.createCleanWorkspace(), signal)
      })
      .then(snapshot => {
        if (!snapshot || sessionEpochRef.current !== epoch) return
        applySnapshot(snapshot, epoch, true)
      })
      .catch(() => {
        if (sessionEpochRef.current !== epoch) return
        handleLogout()
      })
      .finally(() => {
        if (sessionEpochRef.current === epoch) setAuthLoading(false)
      })
    return () => {
      controller.abort()
    }
  }, [beginSessionAttempt, applySnapshot, handleLogout])

  // Guardar en localStorage únicamente preferencias locales (horarios, tarifas, conocimiento), nunca datos de la API.
  useEffect(() => {
    try {
      repository.savePreferences({
        schedules: data.schedules,
        rates: data.rates,
        knowledge: data.knowledge,
      })
    } catch {
      setToast('No se pudieron guardar las preferencias locales en este navegador.')
    }
  }, [data.schedules, data.rates, data.knowledge])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(''), 5000)
    return () => clearTimeout(t)
  }, [toast])

  const refreshFromBackend = useCallback(async () => {
    if (!backendConnected || !usuario) return
    const epoch = sessionEpochRef.current
    const signal = sessionAbortRef.current?.signal
    try {
      const snapshot = await loadBackendForAuthenticatedUser(usuario, dataRef.current, signal)
      if (sessionEpochRef.current !== epoch) return
      applySnapshot(snapshot, epoch, false)
    } catch (err) {
      if (sessionEpochRef.current !== epoch) return
      if (err instanceof ApiError && err.status !== 401 && err.codigo !== 'ABORTADO') {
        notify(err.message)
      }
    }
  }, [backendConnected, usuario, applySnapshot, notify])

  // Refresco periódico suave para mostrar nuevas solicitudes entrantes de WhatsApp Meta
  useEffect(() => {
    if (!backendConnected || !usuario || page !== 'Recolecciones') return
    const interval = window.setInterval(() => {
      const epoch = sessionEpochRef.current
      const signal = sessionAbortRef.current?.signal
      loadBackendForAuthenticatedUser(usuario, dataRef.current, signal)
        .then(snapshot => {
          if (sessionEpochRef.current !== epoch) return
          applySnapshot(snapshot, epoch, false)
        })
        .catch(() => {
          // Ignorar fallos silenciosos o abortos en refresco periódico
        })
    }, 20_000)
    return () => window.clearInterval(interval)
  }, [backendConnected, usuario, page, applySnapshot])

  async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthError('')
    setAuthLoading(true)
    repository.purgeRealDataFromStorage()
    const { epoch, signal } = beginSessionAttempt()
    try {
      const res = await api.login(phoneInput, passwordInput, signal)
      if (sessionEpochRef.current !== epoch) return
      const snapshot = await loadBackendForAuthenticatedUser(
        res.usuario,
        repository.createCleanWorkspace(),
        signal,
      )
      if (!applySnapshot(snapshot, epoch, true)) return
      setPasswordInput('')
      notify(`Sesión iniciada como ${res.usuario.nombre}.`)
    } catch (err) {
      if (sessionEpochRef.current !== epoch) return
      api.logout()
      setData(repository.createCleanWorkspace())
      setAuthError(
        err instanceof ApiError
          ? err.message
          : 'No se pudo iniciar sesión. Verifica el teléfono, la contraseña y que el backend esté activo.',
      )
    } finally {
      if (sessionEpochRef.current === epoch) setAuthLoading(false)
    }
  }

  async function handleDemoRole(selectedRole: Role) {
    setAuthError('')
    setAuthLoading(true)
    repository.purgeRealDataFromStorage()
    const { epoch, signal } = beginSessionAttempt()
    try {
      const snapshot = await loadBackendForRole(
        selectedRole,
        repository.createCleanWorkspace(),
        signal,
      )
      if (!applySnapshot(snapshot, epoch, true)) return
      notify(`Acceso rápido conectado como ${snapshot.usuario.nombre}.`)
    } catch (err) {
      if (sessionEpochRef.current !== epoch) return
      api.logout()
      setData(repository.createCleanWorkspace())
      setAuthError(
        err instanceof ApiError
          ? err.message
          : 'El acceso rápido no está habilitado en este entorno.',
      )
    } finally {
      if (sessionEpochRef.current === epoch) setAuthLoading(false)
    }
  }

  const flow: Flow | undefined =
    role === 'huerta' ? 'organico' : role === 'reciclaje' ? 'reciclable' : undefined

  async function update(
    nextReq: Request,
    notifications?: DemoNotice[],
    reply?: DemoNotice,
    expectedStatus?: Status,
  ): Promise<boolean> {
    const previous = dataRef.current.requests.find(item => item.id === nextReq.id)
    if (expectedStatus && previous?.status !== expectedStatus) return false

    if (backendConnected && nextReq.backendId) {
      const epoch = sessionEpochRef.current
      try {
        const synced = await syncTransitionToBackend(previous, nextReq, reglasRaw)
        if (sessionEpochRef.current !== epoch) return false
        if (!synced) return true
        setData(current =>
          applyRequestUpdate(current, synced.updated, undefined, undefined, expectedStatus),
        )
        notify(synced.message)
        return true
      } catch (err) {
        if (sessionEpochRef.current !== epoch) return false
        notify(
          err instanceof ApiError
            ? err.message
            : 'No se pudo guardar el cambio en el servidor.',
        )
        return false
      }
    }

    setData(current =>
      applyRequestUpdate(current, nextReq, notifications, reply, expectedStatus),
    )
    return true
  }

  function saveAdminSettings(settings: Partial<Pick<Data, 'pointRules' | 'rates'>>) {
    if (backendConnected && settings.pointRules) {
      const epoch = sessionEpochRef.current
      savePointRulesToBackend(settings.pointRules, ruleIds, reglasRaw)
        .then(nuevasReglas => {
          if (sessionEpochRef.current !== epoch) return
          setReglasRaw(nuevasReglas)
          setData(current => ({ ...current, ...settings }))
          notify('Reglas de EcoPuntos guardadas en PostgreSQL.')
        })
        .catch(err => {
          if (sessionEpochRef.current !== epoch) return
          notify(
            err instanceof ApiError
              ? err.message
              : 'No se pudieron guardar las reglas en el backend.',
          )
        })
      return true
    }
    const next = { ...dataRef.current, ...settings }
    try {
      repository.savePreferences({
        schedules: next.schedules,
        rates: next.rates,
        knowledge: next.knowledge,
      })
      setData(next)
      return true
    } catch {
      return false
    }
  }

  const props = {
    data,
    setData: (fn: (d: Data) => Data) => setData(fn),
    notify,
    flow,
  }
  const current = roles.find(r => r.id === role)
  const nav =
    role === 'admin'
      ? [
          { n: 'Resumen', i: LayoutDashboard },
          { n: 'Equipo', i: Users },
          { n: 'Reglas de EcoPuntos', i: Award },
          { n: 'Base de conocimiento', i: BrainCircuit },
          { n: 'Capacitación', i: BookOpen },
        ]
      : [
          { n: 'Recolecciones', i: ClipboardList },
          { n: 'Equipo', i: Users },
          { n: 'Historial', i: History },
          { n: 'Métricas', i: Settings },
          { n: 'Capacitación', i: BookOpen },
        ]
  const total = data.requests
    .filter(r => r.status === 'completada' && (!flow || r.flow === flow))
    .reduce((s, r) => s + kgOf(r), 0)

  return (
    <>
      {!role ? (
        <main className="login">
          <section className="panel login-card">
            <div className="flex justify-center mb-5">
              <Brand />
            </div>
            <h1 className="text-center">Gestión comunitaria</h1>
            <p className="text-center muted mt-2 mb-6">
              Inicia sesión con tu cuenta de coordinación o administración
            </p>
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <label className="field">
                Teléfono registrado
                <input
                  type="tel"
                  autoComplete="username"
                  required
                  value={phoneInput}
                  onChange={e => setPhoneInput(e.target.value)}
                  placeholder="+573000000101"
                />
              </label>
              <label className="field">
                Contraseña
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  value={passwordInput}
                  onChange={e => setPasswordInput(e.target.value)}
                  placeholder="Ingresa tu contraseña"
                />
              </label>
              {authError && (
                <p className="error" role="alert">
                  {authError}
                </p>
              )}
              <button
                type="submit"
                className="btn primary w-full min-h-[52px]"
                disabled={authLoading}
              >
                <KeyRound size={18} aria-hidden="true" />
                {authLoading ? 'Verificando acceso…' : 'Iniciar sesión'}
              </button>
            </form>

            {DEMO_LOGIN_ENABLED && (
              <div className="mt-6 pt-5 border-t border-[#d9e1d7] space-y-3">
                <p className="muted text-center">Acceso rápido de desarrollo (ENTORNO=development)</p>
                {roles.map(r => (
                  <button
                    key={r.id}
                    type="button"
                    className="request-card flex! gap-3 items-center"
                    disabled={authLoading}
                    onClick={() => handleDemoRole(r.id)}
                  >
                    <span className="mini-icon">
                      <r.icon />
                    </span>
                    <div className="flex-1">
                      <h3>{r.title}</h3>
                      <p className="muted">{r.desc}</p>
                    </div>
                    <span className="text-xl text-[#527b43]">›</span>
                  </button>
                ))}
              </div>
            )}

            <div className="mt-5 border-t border-[#d9e1d7] pt-4">
              <InstitutionalLogos />
            </div>
          </section>
        </main>
      ) : (
        <>
          <header className="topbar">
            <Brand />
            <div className="top-info">
              <strong>
                {current?.title}
                {flow === 'organico'
                  ? ' (Orgánicos)'
                  : flow === 'reciclable'
                    ? ' (Aprovechables)'
                    : ''}
              </strong>
              <p>
                {usuario ? `${usuario.nombre} · ` : ''}Villas de San Pablo · Fundación Santo
                Domingo
              </p>
            </div>
            <div className="top-total">
              <Scale size={23} color="#b5d99b" /> Total recolectado:{' '}
              <strong className="text-xl">{total.toLocaleString('es-CO')} kg</strong>
            </div>
            <button
              className="icon-btn border-[#638177]!"
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
              onClick={() => handleLogout()}
            >
              <LogOut size={21} />
            </button>
          </header>
          <nav className="nav" aria-label="Navegación principal">
            {nav.map(({ n, i: Icon }) => (
              <button
                key={n}
                className={page === n ? 'active' : ''}
                onClick={() => setPage(n)}
              >
                <Icon size={18} />
                {n}
              </button>
            ))}
          </nav>
          <main className="main" key={role + page}>
            {page === 'Recolecciones' && flow ? (
              <Collections
                flow={flow}
                data={data}
                update={update}
                notify={notify}
                backendConnected={backendConnected}
                onRefresh={backendConnected ? refreshFromBackend : undefined}
                onSaveRecord={record =>
                  setData(d => ({ ...d, intakeRecords: [record, ...d.intakeRecords] }))
                }
              />
            ) : role === 'admin' && page === 'Reglas de EcoPuntos' ? (
              <PointRulesPage
                rules={data.pointRules}
                save={pointRules => saveAdminSettings({ pointRules })}
                rates={data.rates}
                saveRates={rates =>
                  notify(
                    saveAdminSettings({ rates })
                      ? 'Tarifas guardadas.'
                      : 'No se pudieron guardar las tarifas en este navegador.',
                  )
                }
              />
            ) : page === 'Equipo' ? (
              <Team {...props} role={role} />
            ) : page === 'Métricas' && flow ? (
              <SettingsPage {...props} flow={flow} />
            ) : page === 'Base de conocimiento' ? (
              <KnowledgePage {...props} />
            ) : page === 'Capacitación' ? (
              <Training />
            ) : (
              <Reports {...props} />
            )}
            <footer className="app-footer">
              <InstitutionalLogos />
              <div className="app-footer-copy">
                <p>
                  {backendConnected
                    ? 'EcoConecta · Villas de San Pablo · Conectado a API FastAPI'
                    : 'EcoConecta · Prototipo local'}
                </p>
                <p>Cálculo parametrizable sujeto a validación FSD.</p>
              </div>
            </footer>
          </main>
        </>
      )}
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </>
  )
}
