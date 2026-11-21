"""Construye los dos avisos dentro de la transacción de negocio."""
from app.models import AvisoWhatsApp


def encolar(db, historial, solicitud, recolector):
    db.flush()
    hogar = solicitud.solicitante
    codigo = solicitud.codigo_publico
    evento = historial.estado_nuevo
    if evento == "PROGRAMADA":
        horario = f"{solicitud.fecha_programada} a las {solicitud.hora_programada:%H:%M}"
        orden = (f"Recolección {codigo}: {solicitud.flujo}, {solicitud.subtipo_material or 'sin subtipo'}. "
                 f"Dirección: {hogar.direccion or 'sin registrar'} {hogar.sector_manzana or ''}. "
                 f"Horario: {horario}. Al terminar responde LISTO {codigo} [kilos].")
        aviso = f"Tu solicitud {codigo} está programada para {horario}. Te atenderá {recolector.nombre}."
    else:
        orden = f"Cierre confirmado para {codigo}: {solicitud.cantidad_real_kg:.2f} kg."
        aviso = f"{orden} Recibiste {solicitud.puntos_otorgados:.2f} EcoPuntos."
    for rol, usuario, texto in (("RECOLECTOR", recolector, orden), ("SOLICITANTE", hogar, aviso)):
        db.add(AvisoWhatsApp(historial_id=historial.id, solicitud_id=solicitud.id, evento=evento,
                             destinatario=rol, telefono=usuario.telefono, contenido=texto))
