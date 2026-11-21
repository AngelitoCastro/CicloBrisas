/// <reference types="vite/client" />
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { X, CheckCircle2, Clock, CalendarDays, CheckCheck, UserCheck, CircleX, MessageCircle } from 'lucide-react'
import { statuses, type Status } from '../types'

import ecoConectaLogo from '../assets/logo-ecoconecta.png'
import villasLogo from '../assets/logo-villas-de-san-pablo.png'
import fundacionLogo from '../assets/logo-fundacion-santo-domingo.png'

export function Brand() {
    return <div className="brand">
        <img src={ecoConectaLogo} alt="EcoConecta Villas de San Pablo" width={2172} height={724} />
    </div>
}

export function InstitutionalLogos() {
    return <ul className="institutional-logos" aria-label="Identidad institucional">
        <li><img src={villasLogo} alt="Villas de San Pablo · Megabarrio Barranquilla" width={467} height={169} /></li>
        <li><img src={fundacionLogo} alt="Fundación Santo Domingo" width={586} height={317} /></li>
    </ul>
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
