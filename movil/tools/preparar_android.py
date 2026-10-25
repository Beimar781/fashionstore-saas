"""Ajusta el AndroidManifest generado por `flutter create .` para que la app pueda conectarse a la API:
  - permiso INTERNET
  - tráfico HTTP (sin TLS) mientras se prueba contra el backend local (en la nube se usa HTTPS)
Uso (dentro de la carpeta movil):  python tools/preparar_android.py
"""
import pathlib
import re
import sys

ruta = pathlib.Path("android/app/src/main/AndroidManifest.xml")
if not ruta.exists():
    sys.exit("No existe android/app/src/main/AndroidManifest.xml. Ejecute primero:  flutter create .")

xml = ruta.read_text(encoding="utf-8")
if "android.permission.INTERNET" not in xml:
    xml = xml.replace("<application", '<uses-permission android:name="android.permission.INTERNET"/>\n    <application', 1)
if "usesCleartextTraffic" not in xml:
    xml = re.sub(r"<application", '<application android:usesCleartextTraffic="true"', xml, count=1)
ruta.write_text(xml, encoding="utf-8")
print("AndroidManifest.xml actualizado (INTERNET + HTTP de desarrollo).")
