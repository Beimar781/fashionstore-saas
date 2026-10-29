from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fashionstore_saas"
    secret_key: str = "cambiar-esta-clave-larga-y-secreta"
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
    tasa_bob_por_usd: float = 6.96  # Stripe no cobra en bolivianos: en modo prueba se cobra el equivalente en dólares

    @property
    def stripe_activo(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_publishable_key)
    brevo_sender_email: str = "no-reply@fashionstore.com"
    brevo_sender_name: str = "FashionStore"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
