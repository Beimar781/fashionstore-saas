"""CU-31 · Gestionar información de productos y abastecimiento (RN01, RN02). Capa de negocio.

El proveedor avisa una remisión (lote EN_TRANSITO) y propone productos; el Administrador revisa las propuestas.
Al recibir el lote en la sucursal, el inventario suma las unidades (eso lo hace el paquete inventario, que llama a `recibir_lote`).
"""
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.constantes import PROVEEDOR
from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado, Prohibido
from app.modules.acceso.dependencias import Contexto
from app.modules.sucursales.publico import nombres_de_sucursales, sucursal_activa_de_empresa, sucursales_activas
from app.primer_parcial.proveedores.cu15_proveedores.repository import ProveedorRepository
from app.primer_parcial.proveedores.cu15_proveedores.schemas import ProveedorOut
from app.primer_parcial.proveedores.cu31_abastecimiento import schemas
from app.primer_parcial.proveedores.cu31_abastecimiento.repository import (
    ColeccionLectura, LoteRepository, PropuestaRepository, VarianteRepository,
)
from app.primer_parcial.proveedores.models import Lote, Propuesta

MSG_SKU = "El código SKU ingresado no corresponde a ningún producto habilitado; solicite su creación primero."  # excepción de la ficha CU-31
MSG_SIN_ITEMS = "Debe indicar al menos un producto en el aviso de remisión."


class AbastecimientoService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.proveedores = ProveedorRepository(db, ctx.empresa_id)
        self.lotes = LoteRepository(db, ctx.empresa_id)
        self.propuestas = PropuestaRepository(db, ctx.empresa_id)
        self.variantes = VarianteRepository(db, ctx.empresa_id)
        self.colecciones = ColeccionLectura(db, ctx.empresa_id)

    def mi_proveedor(self) -> ProveedorOut:
        return ProveedorOut.desde(self._proveedor_de_la_cuenta())

    # ---- ayudas para armar el aviso ----
    def sucursales_destino(self) -> list[schemas.SucursalDestino]:
        return [schemas.SucursalDestino(id=s["id"], nombre=s["nombre"], ciudad=s["ciudad"]) for s in sucursales_activas(self.db, self.empresa_id)]

    def buscar_variantes(self, q: str | None) -> list[schemas.VarianteHabilitada]:
        """Productos ya registrados que se pueden incluir en un aviso (activos, con variante activa)."""
        return [
            schemas.VarianteHabilitada(sku=v.sku, producto=v.producto.nombre, talla=v.talla.codigo, color=v.color.nombre)
            for v in self.variantes.buscar_habilitadas(q)
        ]

    # ---- avisos de remisión (lotes) ----
    def crear_lote(self, datos: schemas.LoteIn) -> schemas.LoteOut:
        proveedor = self._emisor(datos.proveedor_id)
        if not proveedor.activo:
            raise Conflicto("El proveedor está inactivo.")
        if not datos.items:
            raise DatosInvalidos(MSG_SIN_ITEMS)
        if not sucursal_activa_de_empresa(self.db, self.empresa_id, datos.sucursal_id):
            raise NoEncontrado("Sucursal no encontrada.")  # también si es de otra empresa o está inactiva

        por_sku = self.variantes.habilitadas_por_sku([i.sku.strip().upper() for i in datos.items])
        agregados: dict[int, tuple] = {}
        for item in datos.items:
            variante = por_sku.get(item.sku.strip().upper())
            if variante is None:
                raise DatosInvalidos(MSG_SKU)
            cantidad, costo = agregados.get(variante.id, (0, item.costo_unitario))
            agregados[variante.id] = (cantidad + item.cantidad, item.costo_unitario or costo)  # un SKU repetido se suma

        lote = self.lotes.agregar(Lote(
            proveedor_id=proveedor.id, sucursal_id=datos.sucursal_id, codigo="PENDIENTE", referencia=datos.referencia,
            notas=datos.notas, creado_por=self.ctx.usuario.id,
        ))
        for variante_id, (cantidad, costo) in agregados.items():
            self.lotes.agregar_item(lote, variante_id, cantidad, costo)
        self.db.flush()
        lote.codigo = f"LOT-{lote.id:06d}"  # el id es único, así que el código también lo es dentro de la empresa
        self.db.commit()
        return self._lote_out(lote)

    def listar_lotes(self, estado: str | None, proveedor_id: int | None) -> list[schemas.LoteOut]:
        if self.ctx.rol == PROVEEDOR:
            proveedor_id = self._proveedor_de_la_cuenta().id  # el proveedor solo ve lo suyo
        return self._lotes_out(self.lotes.listar(estado, proveedor_id, None))

    def obtener_lote(self, lote_id: int) -> schemas.LoteOut:
        return self._lote_out(self._lote(lote_id))

    def cancelar_lote(self, lote_id: int) -> schemas.LoteOut:
        lote = self._lote(lote_id)
        if lote.estado != "EN_TRANSITO":
            raise Conflicto("Solo se pueden cancelar lotes en tránsito.")
        lote.estado, lote.cerrado_por, lote.cerrado_en = "CANCELADO", self.ctx.usuario.id, datetime.now(timezone.utc)
        self.db.commit()
        return self._lote_out(lote)

    # ---- propuestas de producto ----
    def crear_propuesta(self, datos: schemas.PropuestaIn) -> schemas.PropuestaOut:
        proveedor = self._proveedor_de_la_cuenta()
        if self.colecciones.obtener(datos.coleccion_id) is None:
            raise NoEncontrado("Colección no encontrada.")
        propuesta = self.propuestas.agregar(Propuesta(
            proveedor_id=proveedor.id, coleccion_id=datos.coleccion_id, nombre=datos.nombre.strip(), descripcion=datos.descripcion,
            genero=datos.genero, precio_base=datos.precio_base, material=datos.material,
        ))
        self.db.commit()
        return self._propuesta_out(propuesta)

    def listar_propuestas(self, estado: str | None) -> list[schemas.PropuestaOut]:
        proveedor_id = self._proveedor_de_la_cuenta().id if self.ctx.rol == PROVEEDOR else None
        return [self._propuesta_out(p) for p in self.propuestas.listar(estado, proveedor_id)]

    def revisar_propuesta(self, propuesta_id: int, aprobar: bool, notas: str) -> schemas.PropuestaOut:
        propuesta = self.propuestas.obtener(propuesta_id)
        if propuesta is None:
            raise NoEncontrado("Propuesta no encontrada.")
        if propuesta.estado != "PENDIENTE":
            raise Conflicto("La propuesta ya fue revisada.")
        if not aprobar and not notas.strip():
            raise DatosInvalidos("Indique el motivo del rechazo.")
        propuesta.estado = "APROBADA" if aprobar else "RECHAZADA"
        propuesta.notas_revision, propuesta.revisado_por = notas.strip(), self.ctx.usuario.id
        self.db.commit()
        return self._propuesta_out(propuesta)

    def resumen(self) -> schemas.ResumenOut:
        """Lo que la administración ve como aviso: lotes por recibir y propuestas por revisar."""
        return schemas.ResumenOut(lotes_en_transito=self.lotes.contar_en_transito(), propuestas_pendientes=self.propuestas.contar_pendientes())

    # ---- recepción (la invoca el paquete inventario) ----
    def lotes_para_recibir(self, sucursal_id: int | None) -> list[schemas.LoteOut]:
        return self._lotes_out(self.lotes.listar("EN_TRANSITO", None, sucursal_id))

    def recibir_lote(
        self, lote_id: int, sucursal_id: int | None, recibidas: dict[int, int] | None,
        aplicar: Callable[[int, int, list[tuple[int, int]]], None],
    ) -> schemas.LoteOut:
        """Cierra el lote como RECIBIDO. `aplicar(lote_id, sucursal_id, [(variante_id, cantidad)])` suma las unidades al inventario."""
        lote = self._lote(lote_id)
        if sucursal_id is not None and lote.sucursal_id != sucursal_id:
            raise NoEncontrado("Lote no encontrado.")  # el Encargado solo ve los lotes de su sucursal
        if lote.estado != "EN_TRANSITO":
            raise Conflicto("El lote ya fue recibido o cancelado.")
        recibidas = recibidas or {}
        for item in lote.items:
            item.cantidad_recibida = recibidas.get(item.id, item.cantidad)
            if item.cantidad_recibida > item.cantidad:
                raise DatosInvalidos("No puede recibir más unidades de las que despachó el proveedor.")
        aplicar(lote.id, lote.sucursal_id, [(i.variante_id, i.cantidad_recibida) for i in lote.items if i.cantidad_recibida > 0])
        lote.estado, lote.cerrado_por, lote.cerrado_en = "RECIBIDO", self.ctx.usuario.id, datetime.now(timezone.utc)
        self.db.commit()
        return self._lote_out(lote)

    # ---- auxiliares ----
    def _proveedor_de_la_cuenta(self):
        proveedor = self.proveedores.de_usuario(self.ctx.usuario.id)
        if proveedor is None:
            raise Prohibido("Su usuario no está asociado a un proveedor.")
        return proveedor

    def _emisor(self, proveedor_id: int | None):
        """Quien envía el aviso: el propio proveedor, o el que indique el Administrador."""
        if self.ctx.rol == PROVEEDOR:
            return self._proveedor_de_la_cuenta()
        proveedor = self.proveedores.obtener(proveedor_id) if proveedor_id is not None else None
        if proveedor is None:
            raise NoEncontrado("Proveedor no encontrado.")
        return proveedor

    def _lote(self, lote_id: int) -> Lote:
        lote = self.lotes.obtener_completo(lote_id)
        if lote is None or (self.ctx.rol == PROVEEDOR and lote.proveedor_id != self._proveedor_de_la_cuenta().id):
            raise NoEncontrado("Lote no encontrado.")  # también si es de otra empresa o de otro proveedor
        return lote

    def _lotes_out(self, lotes: list[Lote]) -> list[schemas.LoteOut]:
        variantes = self.variantes.con_producto({i.variante_id for lote in lotes for i in lote.items})
        sucursales = nombres_de_sucursales(self.db, self.empresa_id)
        return [self._lote_out(lote, variantes, sucursales) for lote in lotes]

    def _lote_out(self, lote: Lote, variantes=None, sucursales=None) -> schemas.LoteOut:
        variantes = variantes if variantes is not None else self.variantes.con_producto({i.variante_id for i in lote.items})
        sucursales = sucursales if sucursales is not None else nombres_de_sucursales(self.db, self.empresa_id)
        return schemas.LoteOut(
            id=lote.id, codigo=lote.codigo, estado=lote.estado, proveedor_id=lote.proveedor_id,
            proveedor=lote.proveedor.nombre_comercial or lote.proveedor.razon_social, sucursal_id=lote.sucursal_id,
            sucursal=sucursales.get(lote.sucursal_id, ""), referencia=lote.referencia, notas=lote.notas, creado_en=lote.creado_en,
            cerrado_en=lote.cerrado_en, total_unidades=sum(i.cantidad for i in lote.items),
            items=[
                schemas.ItemOut(
                    id=i.id, variante_id=i.variante_id, sku=variantes[i.variante_id].sku, producto=variantes[i.variante_id].producto.nombre,
                    talla=variantes[i.variante_id].talla.codigo, color=variantes[i.variante_id].color.nombre, cantidad=i.cantidad,
                    cantidad_recibida=i.cantidad_recibida, costo_unitario=i.costo_unitario,
                )
                for i in lote.items
            ],
        )

    def _propuesta_out(self, p: Propuesta) -> schemas.PropuestaOut:
        coleccion = self.colecciones.obtener(p.coleccion_id)
        return schemas.PropuestaOut(
            id=p.id, proveedor_id=p.proveedor_id, proveedor=p.proveedor.nombre_comercial or p.proveedor.razon_social, nombre=p.nombre,
            descripcion=p.descripcion, coleccion_id=p.coleccion_id, coleccion=coleccion.nombre if coleccion else "", genero=p.genero,
            precio_base=p.precio_base, material=p.material, estado=p.estado, notas_revision=p.notas_revision, creado_en=p.creado_en,
        )
