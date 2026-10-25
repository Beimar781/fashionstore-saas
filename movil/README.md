# FashionStore · Móvil (Flutter + SQLite)

Alcance Lote 1: **CU-02 Iniciar sesión** con código de empresa, sesión guardada en SQLite (funciona sin conexión) y
esquema local para el Lote 2 (productos locales, operaciones pendientes con estados de sincronización).

## Preparar el entorno (una sola vez)
1. Instalar el **Flutter SDK** (https://docs.flutter.dev/get-started/install/windows) y agregar `flutter\bin` al PATH.
2. En **Android Studio**: *More Actions → SDK Manager* (Android SDK y *Command-line Tools*) y *Plugins → Flutter* (instala Dart).
3. `flutter doctor --android-licenses` (aceptar todo) y `flutter doctor` (debe quedar sin ❌ en Android).
4. Crear un emulador: Android Studio → *Device Manager → Create Device* (por ejemplo Pixel 6, Android 14) → ▶.
   O conectar un celular Android con *Depuración USB* activada.

## Generar las carpetas de plataforma y correr
```powershell
cd movil
flutter create . --project-name fashionstore_movil --org bo.fashionstore --platforms=android
python tools/preparar_android.py        # permiso de Internet + HTTP de desarrollo
flutter pub get
flutter run                             # el backend debe estar corriendo en la PC (puerto 8000)
```
- Emulador Android: usa `http://10.0.2.2:8000/api` (ya es el valor por defecto; `10.0.2.2` es el localhost de la PC).
- Celular físico (misma red Wi‑Fi): `flutter run --dart-define=API_URL=http://192.168.X.X:8000/api`
- Pruebas: `flutter test`

## Estructura (por paquetes)
`lib/core` (config, red, SQLite, tema) · `lib/features/auth` (P2: data / presentation) · `lib/features/home`.
Los paquetes del Lote 2 se agregan como `lib/features/<paquete>/{data,presentation}`.
