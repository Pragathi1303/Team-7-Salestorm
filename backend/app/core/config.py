from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://salestorm:salestorm_secret@localhost:5432/salestorm"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "dev_secret_key"
    environment: str = "development"
    log_level: str = "INFO"

    # Reservation
    reservation_expiry_seconds: int = 30
    queue_admission_rate: int = 50  # requests admitted per second

    # Demo
    demo_product_sku: str = "P001"
    demo_initial_inventory: int = 100

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
