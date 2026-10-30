from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRET_KEY_POR_DEFECTO = "cambiar-esta-clave-larga-y-secreta"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fashionstore_saas"
    secret_key: str = SECRET_KEY_POR_DEFECTO
    # Despliegue (Railway): en producción el backend se niega a arrancar con la SECRET_KEY por defecto. Railway define RAILWAY_ENVIRONMENT por su cuenta.
    entorno: str = "desarrollo"
    railway_environment: str = ""
    cargar_datos_demo: bool = False  # al arrancar, carga el seed solo si la base está vacía
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    # Imágenes de productos: una carpeta por empresa dentro de media_dir
    media_dir: str = "media"
    media_max_mb: int = 5
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    # Recuperación de contraseña: sin BREVO_API_KEY el enlace se imprime en la consola del servidor (desarrollo).
    frontend_url: str = "http://localhost:4200"
    reset_token_minutes: int = 60
    brevo_api_key: str = ""
    # Reservas (CU-09): vigencia tras el horario elegido, anticipación máxima y zona horaria de las tiendas (Bolivia, UTC-4)
    reserva_horas_vigencia: int = 24
    reserva_dias_max: int = 14
    zona_horaria_horas: int = -4
    # Compras (CU-08, CU-11): los precios ya incluyen el IVA; aquí solo se calcula cuánto es
    iva_porcentaje: int = 13
    # Pagos (CU-32): sin claves de Stripe se usa un pago simulado con tarjetas de prueba. Las claves van en .env, nunca en el código.
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    # Servicio de impuestos (CU-30): hoy es simulado; esta opción simula que no responde, para ver el comprobante interno temporal
    impuestos_simular_falla: bool = False
    # IA (CU-07, CU-23, CU-42): sin clave se usa el modo de respaldo con reglas locales. Las claves van en .env, nunca en el código.
    ia_proveedor: str = "gemini"  # gemini (gratuito) | anthropic
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    ia_modelo: str = ""  # vacío = el modelo por defecto del proveedor
    tasa_bob_por_usd: float = 6.96  # Stripe no cobra en bolivianos: en modo prueba se cobra el equivalente en dólares

    # Avisos push (regla 17): sin claves VAPID / sin cuenta de servicio de Firebase quedan en modo simulado. Las claves van en .env, nunca en el código.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:soporte@fashionstore.com"
    fcm_credenciales: str = ""  # ruta al JSON de la cuenta de servicio de Firebase
    fcm_credenciales_json: str = ""  # el mismo JSON pegado como variable (en Railway no hay archivos)
    fcm_proyecto: str = ""

    @property
    def stripe_activo(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_publishable_key)

    @property
    def vapid_activo(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    @property
    def fcm_activo(self) -> bool:
        return bool((self.fcm_credenciales or self.fcm_credenciales_json) and self.fcm_proyecto)

    @property
    def es_produccion(self) -> bool:
        return self.entorno.lower() in ("produccion", "producción", "production") or bool(self.railway_environment)

    @field_validator("database_url")
    @classmethod
    def _driver_psycopg(cls, url: str) -> str:
        """Railway entrega postgresql://... (o postgres://...): SQLAlchemy necesita el driver psycopg (3) indicado."""
        for prefijo in ("postgresql://", "postgres://"):
            if url.startswith(prefijo):
                return "postgresql+psycopg://" + url[len(prefijo):]
        return url

    brevo_sender_email: str = "no-reply@fashionstore.com"
    brevo_sender_name: str = "FashionStore"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
