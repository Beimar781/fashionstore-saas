from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fashionstore_saas"
    secret_key: str = "cambiar-esta-clave-larga-y-secreta"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"
    # Recuperación de contraseña: sin BREVO_API_KEY el enlace se imprime en la consola del servidor (desarrollo).
    frontend_url: str = "http://localhost:4200"
    reset_token_minutes: int = 60
    brevo_api_key: str = ""
    brevo_sender_email: str = "no-reply@fashionstore.com"
    brevo_sender_name: str = "FashionStore"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
