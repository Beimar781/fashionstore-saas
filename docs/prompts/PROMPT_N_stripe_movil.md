# Prompt N — Pago con Stripe (modo prueba) dentro de la app móvil

Lee `CLAUDE.md`, `docs/DESPLIEGUE.md` y `docs/PRUEBAS_SISTEMA.md`. Todo lo que me escribas va en español. Código explicable en una defensa: nombres en español, funciones cortas, sin abstracciones innecesarias. No toques claves, variables de Railway ni secretos.

## Objetivo
Hoy en producción `/api/pagos/config` devuelve `modo: "stripe"` y el móvil solo muestra «termine el pago desde la versión web». Quiero que **el mismo Stripe de prueba funcione en la web y en el móvil**: el cliente paga dentro de la app con la tarjeta de prueba `4242 4242 4242 4242` (cualquier fecha futura y CVC), y el pedido queda aprobado, con su comprobante, igual que en la web. La pasarela simulada debe seguir funcionando cuando el backend no tenga claves de Stripe (modo `simulado`).

## Cómo funciona hoy el backend (no lo cambies salvo que sea imprescindible)
CU-32: `POST` que inicia el pago crea un `PaymentIntent` con captura manual y devuelve `publishable_key` y `client_secret`; el cliente confirma el pago con Stripe; luego `POST /pagos/{pago_id}/confirmar` lee el estado en Stripe, descuenta el stock y recién entonces captura el cobro. Mira `cu32_pago_electronico/{router,service,pasarela,schemas}.py` y, en la web, `pago-tarjeta.component.ts` y `core/pagos/stripe-js.service.ts` para ver el flujo exacto y los textos de error. El móvil debe seguir esos mismos pasos y mensajes.

## Qué hacer
1. **Librería (regla 13):** agrega `flutter_stripe` a `movil/pubspec.yaml` (usa una versión estable compatible con nuestro Flutter y Android Gradle Plugin). Ajusta lo que exija en Android: `MainActivity` como `FlutterFragmentActivity`, tema base `Theme.AppCompat` o equivalente en `styles.xml`, `minSdk` mínimo requerido y reglas de ProGuard/R8 si hacen falta para el build release. Comprueba con una instalación limpia (`flutter pub get`, `flutter build apk --release --dart-define=API_URL=https://fashionstore-saas-production.up.railway.app/api`) que compila.
2. **Flujo en la pantalla del carrito** (`carrito_screen.dart` y su repositorio):
   - Pide `/pagos/config`. Si `modo == "stripe"`: inicializa Stripe con la `publishable_key` que devuelve el backend (no la escribas en el código), inicia el pago, y con el `client_secret` muestra la hoja de pago de Stripe (Payment Sheet) o el campo de tarjeta, lo que sea más simple y estable.
   - Al terminar la hoja de pago, llama a `/pagos/{id}/confirmar` y muestra el resultado con los mismos textos que la web (aprobado, rechazado 402, pendiente de confirmación).
   - Si el cliente cancela la hoja de pago, el pedido queda «pendiente de pago» y la app lo dice sin error.
   - Si `modo == "simulado"`, deja el flujo actual con la tarjeta de prueba, sin cambios.
   - Quita el mensaje «termine el pago desde la versión web».
3. **Tarjetas de prueba útiles** (solo en la guía de pruebas, no en la interfaz): `4242 4242 4242 4242` aprueba; `4000 0000 0000 0002` rechaza; `4000 0027 6000 3184` pide autenticación 3D Secure. Comprueba que el rechazo y el 3D Secure se manejan bien.
4. **Comprobante y pedido:** tras aprobar, el pedido debe verse como pagado en el historial del móvil y el comprobante PDF debe poder abrirse igual que hoy.
5. **Pruebas:** agrega pruebas de Dart con un doble en memoria de la pasarela (sin llamar a Stripe real) para los casos aprobado, rechazado, cancelado y pendiente. `flutter analyze` sin avisos y `flutter test` en verde.
6. **Backend:** revisa que `confirmar` funcione igual si el `PaymentIntent` fue confirmado desde el SDK nativo (estado `requires_capture`). Si hay algún caso que falle, corrígelo con prueba. Si no hace falta cambiar nada, dilo.
7. **Documentación (regla 11):** actualiza `docs/PRUEBAS_SISTEMA.md` (el caso 5.3 ahora paga dentro de la app, con las tarjetas del punto 3), `docs/DESPLIEGUE.md` si algo cambia, y `docs/MENSAJES_PENDIENTES_WORD.md` con la decisión: «el pago con tarjeta se hace con Stripe en modo prueba tanto en web como en móvil».
8. Versiona también `docs/PROMPT_M_cierre_despliegue.md` y este prompt en la carpeta `docs/prompts/` (muévelos ahí).

## Cierre
Corre `cd backend && python -m pytest -q`, `cd frontend && npm run build`, y en `movil/` `flutter analyze` y `flutter test`. Si todo pasa: commits por bloque con mi identidad de git, mensaje corto en español, sin líneas de coautoría, y `git push`. Si algo falla: no hagas commit y explícame qué pasó.

Dame un resumen en español: qué cambiaste, qué decisión tomaste entre Payment Sheet y campo de tarjeta y por qué, y qué debo probar a mano en el celular. Cuando termines avísame para que lance el workflow del APK desde el chat.
