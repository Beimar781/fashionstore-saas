"""CU-07 · Asistente y recomendador de prendas (RN07: plan con IA). Capa de negocio.

El asistente entiende el pedido del cliente (IA externa o reglas de respaldo), lo busca con la búsqueda del catálogo (CU-04, solo prendas con stock)
y responde con prendas reales. El recomendador usa lo que el cliente compró; si aún no compró nada, muestra lo más vendido.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import DatosInvalidos, NoEncontrado
from app.core.ia import obtener_ia
from app.modules.acceso.dependencias import Contexto
from app.modules.catalogo.publico import BusquedaService, FiltrosBusqueda, PrendaOut
from app.modules.ia.publico import registrar_uso_ia
from app.primer_parcial.ia.cu07_asistente import schemas
from app.primer_parcial.ia.cu07_asistente.intencion import Intencion, combinar, parsear_con_ia, parsear_con_reglas
from app.primer_parcial.ia.cu07_asistente.recomendador import Recomendador
from app.primer_parcial.ia.cu07_asistente.repository import AsistenteRepository, InteraccionRepository
from app.primer_parcial.ia.models import InteraccionCliente

MSG_VACIO = "Escriba su consulta para el asistente."
BIENVENIDA = "¡Hola! Soy el asistente de la tienda. Cuénteme qué busca, por ejemplo «una camisa azul de menos de 200 Bs», «ropa formal para hombre» o «arme un outfit casual»."
SIN_GUSTOS = "Todavía no conozco sus gustos, así que le muestro lo más vendido. Busque o mire prendas y aprenderé qué le gusta."
SIN_RESULTADOS = "No encontré prendas disponibles con esas características. Pruebe con otro color, otra categoría o un precio mayor."
MAX_PRENDAS = 6


class AsistenteService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.repo = AsistenteRepository(db, ctx.empresa_id)
        self.catalogo = BusquedaService(db, ctx.empresa_id)
        self.interacciones = InteraccionRepository(db, ctx.empresa_id)
        self.recomendador = Recomendador(db, ctx, self.catalogo, self.repo)

    # ---- chat ----
    def chat(self, datos: schemas.ChatIn) -> schemas.ChatOut:
        ultimo = datos.mensajes[-1]
        if ultimo.rol != "usuario" or not ultimo.texto.strip():
            raise DatosInvalidos(MSG_VACIO)
        self.catalogo.validar_sucursal(datos.sucursal_id)
        categorias, colores = dict((n, i) for i, n in self.repo.nombres_de_categorias()), dict((n, i) for i, n in self.repo.nombres_de_colores())
        conversacion = [(m.rol, m.texto.strip()) for m in datos.mensajes if m.texto.strip()]
        intencion = parsear_con_ia(obtener_ia(), conversacion, list(colores), list(categorias))
        origen = "IA"
        if intencion is None:
            origen = "REGLAS"
            intencion = parsear_con_reglas(ultimo.texto, list(colores), list(categorias))
            anterior = next((parsear_con_reglas(t, list(colores), list(categorias)) for r, t in reversed(conversacion[:-1]) if r == "usuario"), None)
            intencion = combinar(anterior, intencion)

        if intencion.saludo:
            productos, relajados, respuesta = [], [], BIENVENIDA
        elif intencion.recomendar and intencion.vacia():  # «recomiéndame algo»: se compara con sus gustos
            rec = self.recomendador.recomendar(datos.sucursal_id, MAX_PRENDAS)
            productos, origen = rec.productos, rec.origen
            respuesta = f"Estas prendas le pueden gustar. {rec.motivo}" if rec.personalizada else SIN_GUSTOS
        else:
            productos, relajados = self._buscar(intencion, datos.sucursal_id, categorias, colores)
            respuesta = self._responder(intencion, productos, relajados)
        self._recordar_pedido(intencion, ultimo.texto, categorias, colores)
        registrar_uso_ia(self.db, self.empresa_id, self.ctx.usuario.id, "ASISTENTE", origen)
        self.db.commit()
        return schemas.ChatOut(
            respuesta=respuesta, productos=productos, sugerencias=self._sugerencias(intencion, productos),
            filtros=intencion.model_dump(mode="json", exclude_defaults=True), origen=origen,
        )

    def _buscar(self, i: Intencion, sucursal: int | None, categorias: dict[str, int], colores: dict[str, int]) -> tuple[list[PrendaOut], list[str]]:
        """La búsqueda del pedido; si no hay resultados se van soltando filtros (precio, talla, color, estilo) y se avisa cuál."""
        pasos, actual = [("", i)], i
        for nombre, campos, pedido in (
            ("precio", {"precio_min": None, "precio_max": None}, i.precio_min or i.precio_max), ("talla", {"talla": None}, i.talla),
            ("color", {"colores": []}, i.colores), ("estilo", {"ocasion": None, "genero": None}, i.ocasion or i.genero),
        ):
            if pedido:  # solo se suelta lo que el cliente había pedido
                actual = actual.model_copy(update=campos)
                pasos.append((nombre, actual))
        relajados: list[str] = []
        for nombre, paso in pasos:
            if nombre:
                relajados.append(nombre)
            productos = self._ejecutar(paso, sucursal, categorias, colores)
            if productos:
                return productos, relajados
        return [], relajados

    def _ejecutar(self, i: Intencion, sucursal: int | None, categorias: dict[str, int], colores: dict[str, int]) -> list[PrendaOut]:
        ids_categoria = [categorias[c] for c in i.categorias if c in categorias] or [None]
        ids_color = [colores[c] for c in i.colores if c in colores] or [None]
        vistos: dict[int, PrendaOut] = {}
        for categoria_id in ids_categoria[:3]:
            for color_id in ids_color[:3]:
                filtros = FiltrosBusqueda(
                    q=i.ocasion, categoria_id=categoria_id, color_id=color_id, talla=i.talla, precio_min=i.precio_min, precio_max=i.precio_max, genero=i.genero,
                    sucursal=sucursal, solo_disponibles=True, tamano=50 if i.outfit else MAX_PRENDAS,
                )
                for prenda in self.catalogo.buscar(filtros).items:
                    vistos.setdefault(prenda.id, prenda)
        lista = [p for p in vistos.values() if not i.ofertas or p.promocion]
        if i.outfit:  # una prenda de cada categoría para que combinen
            por_categoria: dict[str, PrendaOut] = {}
            for p in lista:
                por_categoria.setdefault(p.categoria, p)
            lista = list(por_categoria.values())[:4]
        return lista[:MAX_PRENDAS]

    def _responder(self, i: Intencion, productos: list[PrendaOut], relajados: list[str]) -> str:
        if not productos:
            return "No encontré ofertas con esas características." if i.ofertas else SIN_RESULTADOS
        partes = [*i.categorias, *i.colores]
        if i.talla:
            partes.append(f"talla {i.talla}")
        if i.precio_max:
            partes.append(f"hasta Bs {i.precio_max:.0f}")
        if i.precio_min:
            partes.append(f"desde Bs {i.precio_min:.0f}")
        if i.ocasion:
            partes.append(i.ocasion)
        detalle = f" ({', '.join(partes)})" if partes else ""
        if i.outfit:
            texto = f"Le armé un outfit de {len(productos)} prenda(s) que combinan{detalle}: " + ", ".join(p.nombre for p in productos) + "."
        else:
            texto = f"Encontré {len(productos)} prenda(s) disponible(s){detalle}."
        if relajados:
            texto += f" No había con todo lo pedido, así que amplié la búsqueda sin el filtro de {', '.join(relajados)}."
        return texto

    @staticmethod
    def _sugerencias(i: Intencion, productos: list[PrendaOut]) -> list[str]:
        if i.saludo or not productos:
            return ["Muéstreme lo más vendido", "Quiero ropa formal", "Arme un outfit casual"]
        sugerencias = ["Muéstreme algo más económico", "¿Lo tiene en otro color?"]
        sugerencias.append("Muéstreme las ofertas" if not i.ofertas else "Arme un outfit con esto")
        return sugerencias

    # ---- perfil de gustos: lo que el cliente hace en la tienda ----
    def _recordar_pedido(self, i: Intencion, texto: str, categorias: dict[str, int], colores: dict[str, int]) -> None:
        """Lo que el cliente le pidió al asistente también cuenta como gusto (si no apagó la personalización)."""
        if i.vacia() or not self.interacciones.personaliza(self.ctx.usuario.id):
            return
        for categoria in (i.categorias[:3] or [None]):
            self.interacciones.agregar(InteraccionCliente(
                cliente_id=self.ctx.usuario.id, tipo="ASISTENTE", texto=texto.strip()[:120], categoria_id=categorias.get(categoria) if categoria else None,
                color_id=colores.get(i.colores[0]) if i.colores else None, talla=i.talla, precio_max=i.precio_max,
            ))
        self.interacciones.recortar(self.ctx.usuario.id)

    def registrar_interaccion(self, datos: schemas.InteraccionIn) -> schemas.InteraccionOut:
        cliente_id = self.ctx.usuario.id
        if not self.interacciones.personaliza(cliente_id):
            return schemas.InteraccionOut(registrada=False)
        categoria_id, color_id = datos.categoria_id, datos.color_id
        if datos.tipo == "VISTA":
            if datos.producto_id is None:
                raise DatosInvalidos("Indique la prenda que miró.")
            producto = self.repo.producto_existe(datos.producto_id)
            if producto is None:
                raise NoEncontrado("Prenda no encontrada.")  # también si es de otra empresa
            categoria_id = producto.categoria_id
        elif not any((datos.texto and datos.texto.strip(), categoria_id, color_id, datos.talla, datos.precio_max)):
            raise DatosInvalidos("La búsqueda no tiene datos de los que aprender.")
        categoria_id = categoria_id if categoria_id in dict(self.repo.nombres_de_categorias()) else None
        color_id = color_id if color_id in dict(self.repo.nombres_de_colores()) else None
        self.interacciones.agregar(InteraccionCliente(
            cliente_id=cliente_id, tipo=datos.tipo, texto=(datos.texto or "").strip()[:120] or None, producto_id=datos.producto_id if datos.tipo == "VISTA" else None,
            categoria_id=categoria_id, color_id=color_id, talla=(datos.talla or "").strip().upper() or None, precio_max=datos.precio_max,
        ))
        self.interacciones.recortar(cliente_id)
        self.db.commit()
        return schemas.InteraccionOut(registrada=True)

    def privacidad(self) -> schemas.PrivacidadOut:
        return schemas.PrivacidadOut(personalizar=self.interacciones.personaliza(self.ctx.usuario.id), interacciones=self.interacciones.cuantas(self.ctx.usuario.id))

    def fijar_privacidad(self, personalizar: bool) -> schemas.PrivacidadOut:
        self.interacciones.fijar_personalizar(self.ctx.usuario.id, personalizar)
        if not personalizar:  # al apagar la personalización también se olvida lo aprendido
            self.interacciones.borrar_del_cliente(self.ctx.usuario.id)
        self.db.commit()
        return self.privacidad()

    def borrar_historial(self) -> schemas.PrivacidadOut:
        self.interacciones.borrar_del_cliente(self.ctx.usuario.id)
        self.db.commit()
        return self.privacidad()

    # ---- recomendador y outfits ----
    def recomendaciones(self, sucursal: int | None, limite: int) -> schemas.RecomendacionesOut:
        self.catalogo.validar_sucursal(sucursal)
        resultado = self.recomendador.recomendar(sucursal, limite)
        registrar_uso_ia(self.db, self.empresa_id, self.ctx.usuario.id, "ASISTENTE", resultado.origen)
        self.db.commit()
        return resultado

    def outfit(self, producto_id: int | None, sucursal: int | None) -> schemas.OutfitOut:
        self.catalogo.validar_sucursal(sucursal)
        resultado = self.recomendador.outfit(producto_id, sucursal)
        registrar_uso_ia(self.db, self.empresa_id, self.ctx.usuario.id, "ASISTENTE", resultado.origen)
        self.db.commit()
        return resultado
