"""Datos de ejemplo del catálogo (Fase A) para las dos empresas de prueba. Lo llama `app.seed`; es idempotente."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.texto import codigo_corto, slugify
from app.modules.inventario.models import Existencia
from app.modules.sucursales.models import Sucursal
from app.primer_parcial.catalogo.models import (
    Categoria, Coleccion, Color, GrupoTalla, Marca, Producto, Promocion, Talla, Temporada, Variante,
)

GRUPOS = {"Ropa superior": ["S", "M", "L", "XL"], "Pantalones": ["28", "30", "32", "34"]}

# nombre, hex
COLORES = {
    "EMP-A": [("Negro", "#111111"), ("Blanco", "#F5F5F5"), ("Rojo", "#C62828"), ("Azul marino", "#1A2A5E")],
    "EMP-B": [("Beige", "#D8C3A5"), ("Marrón", "#6B4226"), ("Verde musgo", "#556B2F"), ("Azul andino", "#2E5E8C")],
}

# categoría, grupo de tallas
CATEGORIAS = {
    "EMP-A": [("Camisas", "Ropa superior"), ("Pantalones", "Pantalones"), ("Vestidos", "Ropa superior")],
    "EMP-B": [("Chompas", "Ropa superior"), ("Pantalones", "Pantalones")],
}

# producto, categoría, género, precio, colores, tallas, material
PRODUCTOS = {
    "EMP-A": [
        ("Camisa Oxford", "Camisas", "MASCULINO", "120", ["Blanco", "Azul marino"], ["S", "M", "L", "XL"], "100% algodón"),
        ("Polo Básico", "Camisas", "UNISEX", "80", ["Negro", "Blanco", "Rojo"], ["S", "M", "L"], "Algodón peinado"),
        ("Jean Slim", "Pantalones", "MASCULINO", "220", ["Azul marino", "Negro"], ["30", "32", "34"], "Denim elástico"),
        ("Vestido Floral", "Vestidos", "FEMENINO", "180", ["Rojo", "Blanco"], ["S", "M", "L"], "Viscosa"),
    ],
    "EMP-B": [
        ("Chompa de Alpaca", "Chompas", "UNISEX", "350", ["Beige", "Marrón", "Azul andino"], ["S", "M", "L", "XL"], "Alpaca 80%"),
        ("Chompa Tejida", "Chompas", "FEMENINO", "280", ["Verde musgo", "Beige"], ["S", "M", "L"], "Lana de oveja"),
        ("Pantalón de Lana", "Pantalones", "MASCULINO", "300", ["Marrón", "Verde musgo"], ["30", "32", "34"], "Lana y poliéster"),
    ],
}


def cargar(db: Session, empresa) -> None:
    codigo = empresa.codigo
    if codigo not in PRODUCTOS or db.scalar(select(Producto.id).where(Producto.empresa_id == empresa.id).limit(1)):
        return
    eid = empresa.id

    grupos = {}
    for nombre, codigos in GRUPOS.items():
        grupo = GrupoTalla(empresa_id=eid, nombre=nombre)
        db.add(grupo)
        db.flush()
        grupos[nombre] = grupo
        for orden, talla in enumerate(codigos, start=1):
            db.add(Talla(empresa_id=eid, grupo_id=grupo.id, codigo=talla, orden=orden))
    db.flush()

    categorias = {}
    for orden, (nombre, grupo) in enumerate(CATEGORIAS[codigo], start=1):
        categorias[nombre] = Categoria(empresa_id=eid, nombre=nombre, slug=slugify(nombre), grupo_talla_id=grupos[grupo].id, orden=orden)
        db.add(categorias[nombre])

    colores, usados = {}, set()
    for nombre, hexa in COLORES[codigo]:
        corto = codigo_corto(nombre, lambda c: c in usados)
        usados.add(corto)
        colores[nombre] = Color(empresa_id=eid, nombre=nombre, slug=slugify(nombre), codigo=corto, codigo_hex=hexa)
        db.add(colores[nombre])

    marca = Marca(empresa_id=eid, nombre="Urbana" if codigo == "EMP-A" else "Andino", slug="urbana" if codigo == "EMP-A" else "andino")
    hoy = date.today()
    temporada = Temporada(empresa_id=eid, nombre="Primavera-Verano 2026", codigo="PV26", tipo="PRIMAVERA_VERANO",
                          inicio=date(hoy.year, 9, 1), fin=date(hoy.year + 1, 3, 31))
    otra = Temporada(empresa_id=eid, nombre="Otoño-Invierno 2026", codigo="OI26", tipo="OTONO_INVIERNO",
                     inicio=date(hoy.year, 3, 1), fin=date(hoy.year, 8, 31))
    db.add_all([marca, temporada, otra])
    db.flush()
    nombre_col = "Verano Urbano" if codigo == "EMP-A" else "Altiplano"
    coleccion = Coleccion(empresa_id=eid, temporada_id=temporada.id, nombre=nombre_col, slug=slugify(nombre_col), fecha_lanzamiento=hoy)
    db.add(coleccion)
    db.flush()

    tallas = {(t.grupo.nombre, t.codigo): t for t in db.scalars(select(Talla).where(Talla.empresa_id == eid))}
    sucursales = list(db.scalars(select(Sucursal).where(Sucursal.empresa_id == eid).order_by(Sucursal.id)))
    for nombre, cat, genero, precio, nombres_color, codigos_talla, material in PRODUCTOS[codigo]:
        categoria = categorias[cat]
        producto = Producto(
            empresa_id=eid, categoria_id=categoria.id, marca_id=marca.id, coleccion_id=coleccion.id, nombre=nombre,
            slug=slugify(nombre), descripcion=f"{nombre} de la colección {nombre_col}.", genero=genero,
            precio_base=Decimal(precio), material=material, cuidado="Lavar a máquina en agua fría",
        )
        db.add(producto)
        db.flush()
        grupo = next(n for n, g in grupos.items() if g.id == categoria.grupo_talla_id)
        for c in nombres_color:
            for t in codigos_talla:
                talla, color = tallas[(grupo, t)], colores[c]
                v = Variante(empresa_id=eid, producto_id=producto.id, talla_id=talla.id, color_id=color.id,
                             sku=f"P{producto.id}-{t}-{color.codigo}".upper())
                db.add(v)
                db.flush()
                for s in sucursales:  # existencias de ejemplo: algunas variantes quedan agotadas en alguna sucursal
                    db.add(Existencia(empresa_id=eid, sucursal_id=s.id, variante_id=v.id, disponible=(v.id * 3 + s.id) % 8))

    db.add(Promocion(
        empresa_id=eid, nombre="Descuento de temporada", tipo_descuento="PORCENTAJE", valor=Decimal("15"),
        inicia=hoy - timedelta(days=1), termina=hoy + timedelta(days=60), categorias=[next(iter(categorias.values()))],
    ))
