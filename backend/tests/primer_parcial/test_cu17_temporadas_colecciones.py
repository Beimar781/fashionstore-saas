"""CU-17 Gestionar temporadas y colecciones — caja negra (pasos de la ficha) + aislamiento entre empresas."""
MSG_FECHAS = "La fecha de fin debe ser posterior a la de inicio."


def _temporada(codigo="OI26", inicio="2026-03-01", fin="2026-08-31", **extra):
    return {"nombre": "Otoño-Invierno 2026", "codigo": codigo, "tipo": "OTONO_INVIERNO", "inicio": inicio, "fin": fin, **extra}


def test_01_crear_temporada_con_fechas_validas(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/temporadas", json=_temporada(), headers=h)
    assert r.status_code == 201 and r.json()["codigo"] == "OI26" and r.json()["activa"] is True


def test_02_fecha_de_fin_anterior_al_inicio(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/temporadas", json=_temporada(inicio="2026-08-31", fin="2026-03-01"), headers=h)
    assert r.status_code == 422 and r.json()["detail"] == MSG_FECHAS
    assert client.post("/api/temporadas", json=_temporada(inicio="2026-03-01", fin="2026-03-01"), headers=h).status_code == 422


def test_03_asociar_productos_a_la_temporada(tienda_a, client):
    p = tienda_a.producto("Polo", tienda_a.camisas["id"], tienda_a.col["id"], [tienda_a.alfa["tallas"][0]["id"]], [tienda_a.rojo["id"]])
    assert p["coleccion"] == "Colección Urbana" and p["temporada"] == "Primavera-Verano 2026"  # la temporada llega por la colección


def test_04_editar_una_temporada(tienda_a, client):
    h = tienda_a.h_admin
    r = client.put(f"/api/temporadas/{tienda_a.temp['id']}", json={"nombre": "PV 2026 renovada", "fin": "2027-06-30"}, headers=h)
    assert r.status_code == 200 and r.json()["nombre"] == "PV 2026 renovada" and r.json()["fin"] == "2027-06-30"
    r = client.put(f"/api/temporadas/{tienda_a.temp['id']}", json={"fin": "2026-01-01"}, headers=h)  # antes del inicio guardado
    assert r.status_code == 422 and r.json()["detail"] == MSG_FECHAS


def test_05_consultar_temporadas_activas(tienda_a, client):
    h = tienda_a.h_admin
    inactiva = client.post("/api/temporadas", json=_temporada(activa=False), headers=h).json()
    assert {t["codigo"] for t in client.get("/api/temporadas", headers=h).json()} == {"PV26", "OI26"}  # el Administrador ve todo
    assert inactiva["activa"] is False


def test_colecciones_por_temporada_y_duplicados(tienda_a, client):
    h = tienda_a.h_admin
    otra = client.post("/api/temporadas", json=_temporada(), headers=h).json()
    client.post("/api/colecciones", json={"nombre": "Invierno Andino", "temporada_id": otra["id"]}, headers=h)
    assert [c["nombre"] for c in client.get(f"/api/colecciones?temporada_id={otra['id']}", headers=h).json()] == ["Invierno Andino"]
    r = client.post("/api/colecciones", json={"nombre": "invierno andino", "temporada_id": otra["id"]}, headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe una colección con ese nombre."
    r = client.post("/api/temporadas", json=_temporada(), headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe una temporada con ese código."


def test_eliminar_con_dependencias(tienda_a, client):
    h = tienda_a.h_admin
    r = client.delete(f"/api/temporadas/{tienda_a.temp['id']}", headers=h)
    assert r.status_code == 409 and "colecciones asociadas" in r.json()["detail"]
    tienda_a.producto("Polo", tienda_a.camisas["id"], tienda_a.col["id"], [tienda_a.alfa["tallas"][0]["id"]], [tienda_a.rojo["id"]])
    r = client.delete(f"/api/colecciones/{tienda_a.col['id']}", headers=h)
    assert r.status_code == 409 and "productos asociados" in r.json()["detail"]


def test_aislamiento_entre_empresas(tienda_a, tienda_b, client):
    assert client.put(f"/api/temporadas/{tienda_a.temp['id']}", json={"nombre": "Xy"}, headers=tienda_b.h_admin).status_code == 404
    assert client.delete(f"/api/colecciones/{tienda_a.col['id']}", headers=tienda_b.h_admin).status_code == 404
    r = client.post("/api/colecciones", json={"nombre": "Nueva", "temporada_id": tienda_a.temp["id"]}, headers=tienda_b.h_admin)
    assert r.status_code == 404  # no se puede colgar una colección de la temporada de otra empresa
    # el mismo código de temporada y el mismo nombre de colección existen en ambas empresas sin chocar
    assert tienda_b.temp["codigo"] == tienda_a.temp["codigo"] and tienda_b.col["slug"] == tienda_a.col["slug"]
