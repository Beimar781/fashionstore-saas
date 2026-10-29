"""CU-09 · Realizar reserva de múltiples prendas (RN01, RN02). Capa de negocio.

Este servicio también es el motor del ciclo de vida de la reserva: los casos de uso CU-10, CU-24 y CU-25 cambian
su estado y liberan su stock siempre a través de `cambiar_estado`, `liberar` y `expirar_vencidas`.
"""
import re
import secrets
from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.tiempo import a_local, ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.inventario.publico import aplicar_movimientos, disponible_por_variante
from app.modules.reservas.cu09_reservar import schemas
from app.modules.reservas.cu09_reservar.repository import ReservaRepository, VarianteReservaRepository
from app.modules.reservas.models import Reserva, ReservaItem
from app.modules.reservas.rf11_notificaciones.service import notificar
from app.modules.sucursales.publico import datos_de_sucursal_activa, nombres_de_sucursales, registrar_verificador_de_pendientes

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0, O, 1, I para que el código se dicte sin errores
TRANSICIONES = {
    "PENDIENTE": {"PREPARADA", "EN_PROBADOR", "CANCELADA", "EXPIRADA"},
    "PREPARADA": {"EN_PROBADOR", "CANCELADA", "EXPIRADA"},
    "EN_PROBADOR": {"COMPLETADA"},
}
TEXTO_ESTADO = {
    "PENDIENTE": "pendiente", "PREPARADA": "preparada", "EN_PROBADOR": "en probador", "COMPLETADA": "completada",
    "CANCELADA": "cancelada", "EXPIRADA": "expirada",
}
MSG_SIN_PRENDAS = "Seleccione al menos una prenda para reservar."
MSG_NO_DISPONIBLE = "Una o más prendas ya no están disponibles en el catálogo."


def horario_de_atencion(texto: str | None) -> tuple[time, time] | None:
    """Lee «9:00-20:00» dentro del texto libre del horario de la sucursal; si no hay horas, no se valida."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*(?:-|–|a|hasta)\s*(\d{1,2}):(\d{2})", texto or "")
    if not m:
        return None
    return time(int(m[1]), int(m[2])), time(int(m[3]), int(m[4]))


class ReservaService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.reservas = ReservaRepository(db, empresa_id)
        self.variantes = VarianteReservaRepository(db, empresa_id)

    # ---- CU-09: reservar ----
    def crear(self, ctx: Contexto, datos: schemas.ReservaIn) -> schemas.ReservaOut:
        if not datos.items:
            raise DatosInvalidos(MSG_SIN_PRENDAS)
        sucursal = datos_de_sucursal_activa(self.db, self.empresa_id, datos.sucursal_id)
        if sucursal is None:
            raise NoEncontrado("Sucursal no encontrada.")  # también si es de otra empresa o está inactiva
        programada = self._validar_horario(datos.programada_para, sucursal["horario"])

        pedidas: dict[int, int] = {}
        for item in datos.items:
            pedidas[item.variante_id] = pedidas.get(item.variante_id, 0) + item.cantidad  # una prenda repetida se suma
        habilitadas = self.variantes.habilitadas(set(pedidas))
        if len(habilitadas) != len(pedidas):
            raise DatosInvalidos(MSG_NO_DISPONIBLE)
        self._verificar_stock(pedidas, habilitadas, sucursal)

        cfg = get_settings()
        reserva = self.reservas.agregar(Reserva(
            codigo=self._codigo_libre(), cliente_id=ctx.usuario.id, sucursal_id=sucursal["id"], programada_para=programada,
            vence_en=programada + timedelta(hours=cfg.reserva_horas_vigencia), notas=datos.notas.strip(),
        ))
        for variante_id, cantidad in pedidas.items():
            self.reservas.agregar_item(reserva, variante_id, cantidad)
        self.db.flush()
        # el stock pasa de disponible a reservado (todo o nada)
        aplicar_movimientos(
            self.db, self.empresa_id, sucursal["id"], list(pedidas.items()), "RESERVA", "RESERVA", reserva.id, ctx.usuario.id, f"Reserva {reserva.codigo}"
        )
        unidades = sum(pedidas.values())
        cuando = a_local(programada).strftime("%d/%m/%Y %H:%M")
        notificar(  # RF11: la sucursal se entera de la reserva
            self.db, self.empresa_id, "RESERVA_NUEVA", f"Nueva reserva {reserva.codigo}",
            f"{ctx.usuario.nombre} {ctx.usuario.apellidos} reservó {unidades} prenda(s) para el {cuando}. Prepárelas para su visita.",
            sucursal_id=sucursal["id"], referencia_tipo="RESERVA", referencia_id=reserva.id,
        )
        notificar(
            self.db, self.empresa_id, "RESERVA_CREADA", f"Reserva {reserva.codigo} registrada",
            f"Su reserva en {sucursal['nombre']} quedó registrada para el {cuando}. Presente el código {reserva.codigo} en el mostrador.",
            usuario_id=ctx.usuario.id, referencia_tipo="RESERVA", referencia_id=reserva.id,
        )
        self.db.commit()
        return self.salida([reserva])[0]

    # ---- consultas para la sucursal (CU-24 y CU-25, por publico.py) ----
    def de_sucursal(self, sucursal_id: int, estados: tuple[str, ...] | None, desde: datetime | None, hasta: datetime | None) -> list[Reserva]:
        return self.reservas.buscar(sucursal_id=sucursal_id, estados=estados, desde=desde, hasta=hasta)

    def completa(self, reserva_id: int) -> Reserva | None:
        return self.reservas.obtener_completa(reserva_id)

    def por_codigo(self, codigo: str) -> Reserva | None:
        return self.reservas.por_codigo(codigo)

    # ---- ciclo de vida (lo usan CU-10, CU-24 y CU-25) ----
    def cambiar_estado(self, reserva: Reserva, nuevo: str) -> None:
        if nuevo not in TRANSICIONES.get(reserva.estado, set()):
            raise Conflicto(f"No se puede pasar una reserva {TEXTO_ESTADO[reserva.estado]} a {TEXTO_ESTADO[nuevo]}.")
        reserva.estado = nuevo

    def liberar(self, reserva: Reserva, items: list[ReservaItem], usuario_id: int | None, nota: str, no_encontrado: bool = False) -> None:
        """Devuelve a disponible el stock apartado de los ítems. Si la prenda no estaba físicamente (`no_encontrado`),
        además se descuenta del inventario como ajuste de salida."""
        pendientes = [i for i in items if i.estado == "RESERVADO"]
        if not pendientes:
            return
        lineas = [(i.variante_id, i.cantidad) for i in pendientes]
        aplicar_movimientos(self.db, self.empresa_id, reserva.sucursal_id, lineas, "LIBERA_RESERVA", "RESERVA", reserva.id, usuario_id, nota)
        if no_encontrado:
            aplicar_movimientos(
                self.db, self.empresa_id, reserva.sucursal_id, lineas, "AJUSTE_SALIDA", "RESERVA", reserva.id, usuario_id,
                f"No encontrado en físico (reserva {reserva.codigo})",
            )
        for i in pendientes:
            i.estado = "NO_ENCONTRADO" if no_encontrado else "LIBERADO"

    def completar_con_venta(self, reserva: Reserva, vendidos: dict[int, int], pedido_id: int, usuario_id: int | None) -> None:
        """La venta de caja (CU-29/CU-30) cierra la reserva: lo vendido pasa de reservado a vendido y lo que el cliente no se llevó
        vuelve a disponible. No hace commit: va en la misma transacción del cobro."""
        reservados = {i.variante_id: i for i in reserva.items if i.estado == "RESERVADO"}
        if any(v not in reservados or cantidad > reservados[v].cantidad for v, cantidad in vendidos.items()):
            raise Conflicto("La venta incluye prendas que no están en la reserva.")
        if reserva.estado == "PREPARADA":
            self.cambiar_estado(reserva, "EN_PROBADOR")  # el cliente pasó directo a caja
        self.cambiar_estado(reserva, "COMPLETADA")
        vendidas = [(v, c) for v, c in vendidos.items() if c > 0]
        sobrantes = [(v, i.cantidad - vendidos.get(v, 0)) for v, i in reservados.items() if i.cantidad > vendidos.get(v, 0)]
        if vendidas:
            aplicar_movimientos(self.db, self.empresa_id, reserva.sucursal_id, vendidas, "VENTA_RESERVA", "VENTA", pedido_id, usuario_id, f"Venta de la reserva {reserva.codigo}")
        if sobrantes:
            aplicar_movimientos(self.db, self.empresa_id, reserva.sucursal_id, sobrantes, "LIBERA_RESERVA", "RESERVA", reserva.id, usuario_id, f"Prendas de la reserva {reserva.codigo} que el cliente no compró")
        for variante_id, item in reservados.items():
            comprado = vendidos.get(variante_id, 0)
            item.estado = "VENDIDO" if comprado else "LIBERADO"
            item.cantidad = comprado or item.cantidad

    def expirar_vencidas(self) -> int:
        """Las reservas que pasaron su vigencia sin atenderse devuelven su stock. No hay tareas programadas: se aplica al
        consultar las reservas, así que el stock nunca queda apartado de más."""
        vencidas = self.reservas.vencidas(ahora())
        for reserva in vencidas:
            self.liberar(reserva, reserva.items, None, f"Reserva {reserva.codigo} expirada")
            self.cambiar_estado(reserva, "EXPIRADA")
            notificar(
                self.db, self.empresa_id, "RESERVA_EXPIRADA", f"Reserva {reserva.codigo} expirada",
                "Su reserva venció sin ser atendida y las prendas volvieron a estar disponibles. Puede hacer una nueva reserva.",
                usuario_id=reserva.cliente_id, referencia_tipo="RESERVA", referencia_id=reserva.id,
            )
        if vencidas:
            self.db.commit()
        return len(vencidas)

    # ---- salida ----
    def salida(self, reservas: list[Reserva]) -> list[schemas.ReservaOut]:
        variantes = self.variantes.con_producto({i.variante_id for r in reservas for i in r.items})
        sucursales = nombres_de_sucursales(self.db, self.empresa_id)
        clientes = nombres_de_usuarios(self.db, self.empresa_id, {r.cliente_id for r in reservas})
        return [
            schemas.ReservaOut(
                id=r.id, codigo=r.codigo, estado=r.estado, sucursal_id=r.sucursal_id, sucursal=sucursales.get(r.sucursal_id, ""),
                cliente_id=r.cliente_id, cliente=clientes.get(r.cliente_id, ""), programada_para=r.programada_para, vence_en=r.vence_en,
                notas=r.notas, creada_en=r.creada_en, total_unidades=sum(i.cantidad for i in r.items),
                puede_cancelar=r.estado in ("PENDIENTE", "PREPARADA"),
                items=[
                    schemas.ItemOut(
                        id=i.id, variante_id=i.variante_id, sku=variantes[i.variante_id].sku, producto=variantes[i.variante_id].producto.nombre,
                        talla=variantes[i.variante_id].talla.codigo, color=variantes[i.variante_id].color.nombre, cantidad=i.cantidad, estado=i.estado,
                    )
                    for i in r.items
                ],
            )
            for r in reservas
        ]

    # ---- auxiliares ----
    def _validar_horario(self, programada: datetime, horario: str | None) -> datetime:
        cfg = get_settings()
        local = a_local(programada)
        if local <= a_local(ahora()):
            raise DatosInvalidos("El horario de la reserva debe ser posterior al momento actual.")
        if local > a_local(ahora()) + timedelta(days=cfg.reserva_dias_max):
            raise DatosInvalidos(f"La reserva no puede programarse con más de {cfg.reserva_dias_max} días de anticipación.")
        horas = horario_de_atencion(horario)
        if horas and not (horas[0] <= local.time().replace(second=0, microsecond=0) <= horas[1]):
            raise DatosInvalidos(f"El horario debe estar dentro del horario de atención de la sucursal ({horas[0]:%H:%M} a {horas[1]:%H:%M}).")
        return local

    def _verificar_stock(self, pedidas: dict[int, int], variantes, sucursal: dict) -> None:
        disponibles = disponible_por_variante(self.db, self.empresa_id, pedidas, sucursal["id"])
        faltantes = [
            f"{variantes[v].producto.nombre} ({variantes[v].talla.codigo}, {variantes[v].color.nombre}): "
            f"solicitadas {cantidad}, disponibles {disponibles.get(v, 0)}"
            for v, cantidad in pedidas.items() if disponibles.get(v, 0) < cantidad
        ]
        if faltantes:
            raise Conflicto(f"No hay stock suficiente en {sucursal['nombre']} para: " + "; ".join(faltantes) + ".")

    def _codigo_libre(self) -> str:
        while True:
            codigo = "RSV-" + "".join(secrets.choice(ALFABETO) for _ in range(8))
            if not self.reservas.existe_codigo(codigo):
                return codigo


def _reservas_pendientes(db: Session, empresa_id: int, sucursal_id: int) -> bool:
    """CU-14: una sucursal con reservas activas no se desactiva (primero se resuelven; las vencidas se liberan antes de contar)."""
    ReservaService(db, empresa_id).expirar_vencidas()
    return ReservaRepository(db, empresa_id).hay_activas_en(sucursal_id)


registrar_verificador_de_pendientes(_reservas_pendientes)
