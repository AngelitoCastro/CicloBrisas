"""Fixtures piloto de EcoConecta (Villas de San Pablo).

Todos los nombres, teléfonos y direcciones son ficticios para demostración y pruebas;
no contienen datos personales reales ni contraseñas en texto claro.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict


class UsuarioFixture(TypedDict):
    nombre: str
    telefono: str
    rol: str
    direccion: str | None
    sector_manzana: str | None
    es_piloto: bool
    activo: bool
    password_env: str


class ReglaPuntosFixture(TypedDict):
    flujo: str
    tipo_generador: str
    puntos_base_solicitud: Decimal
    puntos_por_kg: Decimal
    valor_referencia_kg_cop: Decimal
    descripcion_regla: str
    activa: bool


class ContenidoEducativoFixture(TypedDict):
    titulo: str
    categoria: str
    resumen: str
    que_si_va: str | None
    que_no_va: str | None
    orden: int
    publicado: bool


USUARIOS_PILOTO: tuple[UsuarioFixture, ...] = (
    {
        "nombre": "Administración EcoConecta Piloto",
        "telefono": "+573000000100",
        "rol": "ADMIN",
        "direccion": "Centro Comunitario Villas de San Pablo (Demo)",
        "sector_manzana": "Sector Central",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_ADMIN",
    },
    {
        "nombre": "Coordinación Colectivo Huerteros",
        "telefono": "+573000000101",
        "rol": "COORD_HUERTEROS",
        "direccion": "Huerta Comunitaria Villas de San Pablo (Demo)",
        "sector_manzana": "Manzana Huerta",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_COORD_HUERTEROS",
    },
    {
        "nombre": "Huertero Campo Uno",
        "telefono": "+573000000102",
        "rol": "HUERTERO",
        "direccion": "Huerta Comunitaria Sector Norte (Demo)",
        "sector_manzana": "Manzana Huerta",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_HUERTERO",
    },
    {
        "nombre": "Huertero Campo Dos",
        "telefono": "+573000000103",
        "rol": "HUERTERO",
        "direccion": "Huerta Comunitaria Sector Sur (Demo)",
        "sector_manzana": "Manzana Huerta",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_HUERTERO",
    },
    {
        "nombre": "Coordinación Colectivo Recicladores",
        "telefono": "+573000000104",
        "rol": "COORD_RECICLADORES",
        "direccion": "Punto de Acopio Comunitario (Demo)",
        "sector_manzana": "Sector Acopio",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_COORD_RECICLADORES",
    },
    {
        "nombre": "Reciclador Ruta Uno",
        "telefono": "+573000000105",
        "rol": "RECICLADOR",
        "direccion": "Punto de Acopio Ruta A (Demo)",
        "sector_manzana": "Sector Acopio",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_RECICLADOR",
    },
    {
        "nombre": "Reciclador Ruta Dos",
        "telefono": "+573000000106",
        "rol": "RECICLADOR",
        "direccion": "Punto de Acopio Ruta B (Demo)",
        "sector_manzana": "Sector Acopio",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_RECICLADOR",
    },
    {
        "nombre": "Unidad Productiva Piloto Mercado Verde",
        "telefono": "+573000000107",
        "rol": "UNIDAD_PRODUCTIVA",
        "direccion": "Calle Ficticia 101 # 10-20 (Piloto)",
        "sector_manzana": "Manzana A - Piloto FSD",
        "es_piloto": True,
        "activo": True,
        "password_env": "SEED_PASSWORD_UNIDAD_PRODUCTIVA",
    },
    {
        "nombre": "Hogar Piloto Familia Demo",
        "telefono": "+573000000108",
        "rol": "HOGAR",
        "direccion": "Carrera Ficticia 12 # 102-15 (Piloto)",
        "sector_manzana": "Manzana B - Piloto FSD",
        "es_piloto": True,
        "activo": True,
        "password_env": "SEED_PASSWORD_HOGAR",
    },
    {
        "nombre": "Hogar Comunitario General",
        "telefono": "+573000000109",
        "rol": "HOGAR",
        "direccion": "Carrera Ficticia 14 # 104-08 (General)",
        "sector_manzana": "Manzana C - Sector Norte",
        "es_piloto": False,
        "activo": True,
        "password_env": "SEED_PASSWORD_HOGAR",
    },
)

REGLAS_PUNTOS_INICIALES: tuple[ReglaPuntosFixture, ...] = (
    {
        "flujo": "ORGANICO",
        "tipo_generador": "HOGAR",
        "puntos_base_solicitud": Decimal("10.00"),
        "puntos_por_kg": Decimal("5.00"),
        "valor_referencia_kg_cop": Decimal("80.00"),
        "descripcion_regla": (
            "Orgánicos de hogar para compostaje. Cálculo parametrizable sujeto a validación FSD."
        ),
        "activa": True,
    },
    {
        "flujo": "ORGANICO",
        "tipo_generador": "UNIDAD_PRODUCTIVA",
        "puntos_base_solicitud": Decimal("15.00"),
        "puntos_por_kg": Decimal("6.00"),
        "valor_referencia_kg_cop": Decimal("90.00"),
        "descripcion_regla": (
            "Orgánicos de unidad productiva piloto. Cálculo parametrizable sujeto a validación FSD."
        ),
        "activa": True,
    },
    {
        "flujo": "RECICLABLE",
        "tipo_generador": "HOGAR",
        "puntos_base_solicitud": Decimal("10.00"),
        "puntos_por_kg": Decimal("8.00"),
        "valor_referencia_kg_cop": Decimal("120.00"),
        "descripcion_regla": (
            "Material reciclable limpio de hogar. Cálculo parametrizable sujeto a validación FSD."
        ),
        "activa": True,
    },
    {
        "flujo": "RECICLABLE",
        "tipo_generador": "UNIDAD_PRODUCTIVA",
        "puntos_base_solicitud": Decimal("15.00"),
        "puntos_por_kg": Decimal("10.00"),
        "valor_referencia_kg_cop": Decimal("150.00"),
        "descripcion_regla": (
            "Material reciclable de unidad productiva. Cálculo parametrizable sujeto a validación FSD."
        ),
        "activa": True,
    },
)

CONTENIDOS_EDUCATIVOS_INICIALES: tuple[ContenidoEducativoFixture, ...] = (
    {
        "titulo": "Cómo separar residuos orgánicos",
        "categoria": "ORGANICO",
        "resumen": (
            "Los residuos orgánicos limpios alimentan la compostera de la huerta comunitaria "
            "de Villas de San Pablo."
        ),
        "que_si_va": (
            "Cáscaras de frutas y verduras, restos de alimentos crudos, borra de café, "
            "cáscaras de huevo trituradas y hojas secas."
        ),
        "que_no_va": (
            "Plásticos, vidrios, metales, pañales, aceites quemados, heces de mascotas "
            "ni alimentos muy procesados con exceso de grasa."
        ),
        "orden": 1,
        "publicado": True,
    },
    {
        "titulo": "Cómo preparar materiales reciclables",
        "categoria": "RECICLABLE",
        "resumen": (
            "Entrega los reciclables limpios y secos para facilitar el trabajo del "
            "colectivo de recicladores de oficio."
        ),
        "que_si_va": (
            "Botellas plásticas PET limpias y aplastadas, cartón y papel secos, "
            "latas de aluminio, chatarra limpia y envases de vidrio enteros."
        ),
        "que_no_va": (
            "Cartón mojado o untado de grasa o comida, icopor sucio, papel higiénico "
            "o residuos peligrosos."
        ),
        "orden": 2,
        "publicado": True,
    },
    {
        "titulo": "Compostaje y huerta comunitaria",
        "categoria": "HUERTA",
        "resumen": (
            "El colectivo de huerteros transforma el material orgánico separado en abono "
            "para fortalecer la seguridad alimentaria del barrio."
        ),
        "que_si_va": "Residuos orgánicos frescos separados en balde con tapa.",
        "que_no_va": "Mezclas con bolsas plásticas, servilletas sucias o químicos.",
        "orden": 3,
        "publicado": True,
    },
    {
        "titulo": "Frecuencias y programación de rutas",
        "categoria": "RUTAS",
        "resumen": (
            "Referencia comunitaria: orgánicos diarios para unidades productivas y día de por medio "
            "para hogares; reciclables según ruta confirmada por el coordinador."
        ),
        "que_si_va": "Registrar solicitud con disponibilidad clara y esperar confirmación de horario.",
        "que_no_va": "Dejar bolsas sin programar o mezclar orgánicos con reciclables.",
        "orden": 4,
        "publicado": True,
    },
)
