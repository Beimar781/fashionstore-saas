"""Segunda ronda E5 · La auditoría estática de las funciones sin conexión no debe tener fallas: si alguien agrega una pantalla con «Cargando…» sin salida,
una carga que solo corre con red o un indicador de carga del móvil sin salida, esta prueba falla. El informe completo se genera con scripts/auditar_offline.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
import auditar_offline as auditoria  # noqa: E402


def test_01_ninguna_pantalla_web_queda_con_cargando_eterno_ni_carga_solo_con_red():
    filas = auditoria.auditar_web()
    assert len(filas) > 40  # recorrió las rutas de los seis roles
    assert [f for f in filas if f[2] != "OK"] == []


def test_02_todo_indicador_de_carga_y_manejo_de_errores_del_movil_tiene_salida_sin_conexion():
    filas = auditoria.auditar_movil()
    assert len(filas) > 30
    assert [f for f in filas if f[2] != "OK"] == []
