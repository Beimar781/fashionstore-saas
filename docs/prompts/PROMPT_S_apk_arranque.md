# Prompt S — El APK de release se cierra al abrir (WorkManager) y prueba de arranque automática

Todo lo que me escribas va en español. Este arreglo es corto: **no corras la suite completa de pruebas**; con `flutter analyze` basta. No releas todo `docs/`. No toques claves, variables de Railway ni secretos.

## Qué pasó
El APK de release (run #2 del workflow «Compilar APK», commit `b1adad6`) **no abre** en un celular Android (Redmi/MIUI). El informe de error del teléfono dice:

```
java.lang.RuntimeException: Unable to get provider androidx.startup.InitializationProvider
Caused by: java.lang.RuntimeException: Failed to create an instance of androidx.work.impl.WorkDatabase
  at androidx.work.WorkManagerInitializer.create(...)
  at androidx.startup.InitializationProvider.onCreate(...)
```

Los nombres de las clases del trazo están ofuscados (`wo.w`, `bm6`, `r8-map-id-...`), así que **R8 (la reducción de código del build de release de Flutter)** quitó o renombró la clase que Room genera (`androidx.work.impl.WorkDatabase_Impl`) y la app falla al arrancar, antes de mostrar nada. Hay varias librerías que traen WorkManager por dentro (Firebase, ML Kit, notificaciones) y `flutter_stripe` suma sus propias clases que R8 suele necesitar reglas para conservar.

## Qué hacer
1. **Apagar la reducción en el release** (lo más seguro para un proyecto académico, aunque el APK pese más): en `movil/android/app/build.gradle.kts`, dentro de `buildTypes { release { ... } }`, agrega `isMinifyEnabled = false` y `isShrinkResources = false`. Comprueba con `flutter build apk --help` si tu versión de Flutter admite `--no-shrink` y, si es así, agrégalo también al paso `flutter build apk --release` de `.github/workflows/apk.yml`.
2. **Reglas de respaldo por si alguien vuelve a activar R8:** crea `movil/android/app/proguard-rules.pro` y referéncialo con `proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")` en el `release`. Contenido mínimo:
   ```
   -keep class androidx.work.** { *; }
   -keep class * extends androidx.room.RoomDatabase
   -keep class androidx.startup.** { *; }
   -keep class com.stripe.** { *; }
   -keep class com.reactnativestripesdk.** { *; }
   -dontwarn com.stripe.android.pushProvisioning.**
   -dontwarn com.reactnativestripesdk.pushprovisioning.**
   ```
3. **Revisar los demás candidatos a fallar al arrancar** (solo lectura, dime qué encontraste): que el `android:name` de la `Application` y de la `MainActivity` sean los esperados por `flutter_stripe` (la `MainActivity` debe extender `FlutterFragmentActivity`), que el tema base sea `Theme.AppCompat` o compatible, que `minSdk` cumpla lo que piden `flutter_stripe`, `google_mlkit_pose_detection` y `firebase_messaging`, y que `android/app/src/main/AndroidManifest.xml` no tenga duplicados ni permisos mal escritos.
4. **Prueba de arranque automática en el workflow** (para no volver a descubrir esto en un celular). En `.github/workflows/apk.yml` agrega un segundo trabajo `prueba_arranque` que dependa de `apk`:
   - Descarga el artefacto `fashionstore-apk`.
   - Habilita KVM (el fragmento estándar con la regla de `udev`) y usa `reactivecircus/android-emulator-runner@v2` con `api-level: 34`, `target: google_apis`, `arch: x86_64`.
   - En el script del emulador: `adb install -r app-release.apk`, abre la app con `adb shell monkey -p com.example.fashionstore_movil -c android.intent.category.LAUNCHER 1`, espera 25 segundos, y falla si `adb logcat -d` contiene `FATAL EXCEPTION` o `AndroidRuntime` con el paquete de la app, o si `adb shell pidof com.example.fashionstore_movil` no devuelve un proceso vivo.
   - Sube el `logcat` como artefacto `logcat-arranque` (siempre, falle o no).
   - Marca el trabajo con `continue-on-error: true` para que, si el emulador no está disponible en el plan de GitHub, el APK igual se entregue; pero el resultado debe verse en el resumen del run.
   - Usa versiones fijas y con al menos dos semanas de antigüedad para las acciones.
5. **Documentación:** una nota corta en `docs/DESPLIEGUE.md` («El release se compila sin reducción de código por problemas de R8 con WorkManager y Stripe; la prueba de arranque corre en un emulador de GitHub») y una línea en `docs/MENSAJES_PENDIENTES_WORD.md` si procede.

## Cierre
Corre solo `cd movil && flutter analyze`. Si pasa: un commit corto en español con mi identidad de git, sin líneas de coautoría, y `git push`. Dime en un resumen corto qué cambiaste y qué encontraste en el punto 3. Cuando termines avísame para que lance el workflow del APK desde el chat.
