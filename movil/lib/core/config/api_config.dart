/// URL base del backend FastAPI.
///
/// - Emulador Android: `10.0.2.2` apunta al localhost de la PC (valor por defecto).
/// - Celular físico en la misma red: `flutter run --dart-define=API_URL=http://192.168.X.X:8000/api`
/// - Nube: `--dart-define=API_URL=https://su-dominio/api`
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000/api',
  );
}
