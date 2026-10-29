"""CU-42 · Dashboard analítico con Machine Learning (scikit-learn). Capa de negocio.

Dos modelos sobre las ventas de la empresa:
- Clasificación de rotación (KMeans, 3 grupos) de cada producto según lo que vende y lo que tiene en stock: ALTA, MEDIA o BAJA.
- Pronóstico de demanda: regresión lineal sobre las ventas semanales de las últimas 12 semanas, proyectada a 4 semanas, con una recomendación de reposición.
"""
from datetime import timedelta

import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression

from app.modules.ia.cu42_analitica_ml import schemas
from app.modules.ia.publico import registrar_uso_ia
from app.modules.reportes.publico import ReportesBase, hoy_local, inicio_del_dia
from app.core.tiempo import a_local

SEMANAS_HISTORIA = 12
SEMANAS_PROYECCION = 4
MIN_SEMANAS_CON_VENTAS = 3
MSG_POCOS_DATOS = "Todavía no hay ventas suficientes para pronosticar la demanda: se necesitan al menos 3 semanas con ventas de un producto."
MODELOS = {
    "rotacion": "KMeans (3 grupos) de scikit-learn sobre ventas de 30 días y stock",
    "pronostico": f"Regresión lineal de scikit-learn sobre las ventas semanales de las últimas {SEMANAS_HISTORIA} semanas",
}


def clasificar_rotacion(datos: list[tuple[str, int, int]]) -> dict[str, str]:
    """datos: (producto, unidades vendidas en 30 días, stock). Con menos de 3 productos distintos se usan umbrales fijos."""
    puntos = np.array([[u, u / (u + s) if (u + s) else 0.0] for _, u, s in datos], dtype=float)
    if len({tuple(p) for p in puntos}) < 3:
        return {p: "ALTA" if u / 30 >= 1 else "MEDIA" if u / 30 >= 0.2 else "BAJA" for p, u, _ in datos}
    normalizados = (puntos - puntos.mean(axis=0)) / np.where(puntos.std(axis=0) == 0, 1, puntos.std(axis=0))
    modelo = KMeans(n_clusters=3, n_init=10, random_state=42).fit(normalizados)
    orden = np.argsort([puntos[modelo.labels_ == k][:, 0].mean() for k in range(3)])  # de menos a más unidades vendidas
    nombre = {int(orden[0]): "BAJA", int(orden[1]): "MEDIA", int(orden[2]): "ALTA"}
    return {p: nombre[int(etiqueta)] for (p, _, _), etiqueta in zip(datos, modelo.labels_)}


def proyectar(historial: list[int]) -> tuple[list[int], str, float]:
    """(próximas semanas, tendencia, R²) por regresión lineal sobre las semanas."""
    x = np.arange(len(historial)).reshape(-1, 1)
    y = np.array(historial, dtype=float)
    modelo = LinearRegression().fit(x, y)
    futuro = modelo.predict(np.arange(len(historial), len(historial) + SEMANAS_PROYECCION).reshape(-1, 1))
    pendiente = float(modelo.coef_[0])
    tendencia = "SUBE" if pendiente > 0.2 else "BAJA" if pendiente < -0.2 else "ESTABLE"
    return [max(0, round(float(v))) for v in futuro], tendencia, round(max(0.0, float(modelo.score(x, y))), 2)


def recomendar(proyeccion: list[int], tendencia: str, stock: int) -> str:
    demanda = sum(proyeccion)
    if demanda > stock:
        return f"Reponer: la demanda proyectada de las próximas {SEMANAS_PROYECCION} semanas ({demanda} u.) supera el stock ({stock} u.)."
    if tendencia == "BAJA" and stock > 2 * max(demanda, 1):
        return f"Sobrestock: el stock ({stock} u.) duplica la demanda proyectada ({demanda} u.) y la tendencia baja; considere una promoción."
    return f"Stock adecuado para las próximas {SEMANAS_PROYECCION} semanas (demanda proyectada {demanda} u., stock {stock} u.)."


class AnaliticaMLService(ReportesBase):
    def analitica(self, sucursal: int | None) -> schemas.AnaliticaOut:
        sucursal = self.sucursal(sucursal)
        hasta = hoy_local()
        desde = hasta - timedelta(days=SEMANAS_HISTORIA * 7 - 1)
        d, h = inicio_del_dia(desde), inicio_del_dia(hasta + timedelta(days=1))
        semanal: dict[str, list[int]] = {}
        for producto, momento, unidades in self.repo.unidades_por_producto_y_fecha(d, h, sucursal):
            semana = min((a_local(momento).date() - desde).days // 7, SEMANAS_HISTORIA - 1)
            semanal.setdefault(producto, [0] * SEMANAS_HISTORIA)[semana] += unidades
        stock = self.repo.stock_por_producto(sucursal)

        corte = hasta - timedelta(days=29)
        ventas_30d = {p: 0 for p in stock}
        for producto, momento, unidades in self.repo.unidades_por_producto_y_fecha(inicio_del_dia(corte), h, sucursal):
            ventas_30d[producto] = ventas_30d.get(producto, 0) + unidades
        datos = sorted((p, ventas_30d[p], stock.get(p, 0)) for p in ventas_30d)
        clases = clasificar_rotacion(datos) if datos else {}
        rotacion = sorted(
            (schemas.RotacionOut(producto=p, unidades_30d=u, stock=s, tasa_diaria=round(u / 30, 2), clase=clases[p]) for p, u, s in datos),
            key=lambda r: (-r.unidades_30d, r.producto),
        )

        pronostico, sin_historia = [], 0
        for producto, historial in sorted(semanal.items()):
            con_ventas = sum(1 for v in historial if v > 0)
            if con_ventas < MIN_SEMANAS_CON_VENTAS:
                sin_historia += 1
                continue
            proy, tendencia, r2 = proyectar(historial)
            pronostico.append(schemas.PronosticoOut(
                producto=producto, semanas_con_ventas=con_ventas, historial=historial, proyeccion=proy, tendencia=tendencia, r2=r2,
                stock=stock.get(producto, 0), recomendacion=recomendar(proy, tendencia, stock.get(producto, 0)),
            ))
        pronostico.sort(key=lambda p: -sum(p.proyeccion))

        total = [sum(v[i] for v in semanal.values()) for i in range(SEMANAS_HISTORIA)]
        serie = [schemas.PuntoSerieOut(semana_inicio=desde + timedelta(days=7 * i), unidades=u, proyectada=False) for i, u in enumerate(total)]
        if sum(1 for u in total if u > 0) >= MIN_SEMANAS_CON_VENTAS:
            serie += [
                schemas.PuntoSerieOut(semana_inicio=desde + timedelta(days=7 * (SEMANAS_HISTORIA + i)), unidades=u, proyectada=True)
                for i, u in enumerate(proyectar(total)[0])
            ]
        registrar_uso_ia(self.db, self.empresa_id, self.ctx.usuario.id, "ANALITICA", "REGLAS")
        self.db.commit()
        return schemas.AnaliticaOut(
            sucursal_id=sucursal, desde=desde, hasta=hasta, semanas_historia=SEMANAS_HISTORIA, semanas_proyeccion=SEMANAS_PROYECCION, rotacion=rotacion,
            pronostico=pronostico, serie_total=serie, sin_historial_suficiente=sin_historia, mensaje=None if pronostico else MSG_POCOS_DATOS, modelos=MODELOS,
        )
