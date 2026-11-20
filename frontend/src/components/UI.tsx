/// <reference types="vite/client" />
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { X, CheckCircle2, Clock, CalendarDays, CheckCheck, UserCheck, CircleX, MessageCircle } from 'lucide-react'
import { statuses, type Status } from '../types'

const logos = import.meta.glob<string>('../assets/logo-ecoconecta.{svg,png}', {
    eager: true, query: '?url', import: 'default',
})
const logo = Object.values(logos)[0]

export function Brand() {
    return <div className="brand">{logo ? <img src={logo} alt="EcoConecta" /> : <strong>EcoConecta</strong>}</div>
}

const stateIcons = {
    pendiente: Clock, autorizada: UserCheck, programada: CalendarDays,
    completada: CheckCheck, rechazada: CircleX,
}
export function Badge({ status }: { status: Status }) {
    const Icon = stateIcons[status]
    return <span className={'status ' + status}><Icon size={15} aria-hidden="true" />{statuses[status]}</span>
}

export function Empty({ children }: { children: ReactNode }) {
    return <div className="empty"><CheckCircle2 size={30} aria-hidden="true" /><p>{children}</p></div>
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
    const ref = useRef<HTMLDialogElement>(null)
    const titleId = useId()

    useEffect(() => {
        const dialog = ref.current
        const opener = document.activeElement
        dialog?.showModal()
        return () => {
            dialog?.close()
            if (opener instanceof HTMLElement && opener.isConnected) opener.focus()
        }
    }, [])

    return <dialog ref={ref} className="modal panel eco-dialog" aria-labelledby={titleId}
        onCancel={event => { event.preventDefault(); onClose() }}>
        <div className="flex items-center justify-between gap-3 mb-5">
            <h2 id={titleId}>{title}</h2>
            <button type="button" className="icon-btn" aria-label="Cerrar" onClick={onClose}><X /></button>
        </div>
        {children}
    </dialog>
}

export function WhatsApp({ children }: { children: ReactNode }) {
    return <div className="wa"><MessageCircle size={18} aria-hidden="true" /><div>{children}</div></div>
}
