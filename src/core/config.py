import os

from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("APP_PORT", 8000))
    RELOAD: bool = os.getenv("APP_RELOAD", "True").lower() in ("true", "1")
    AMOUNT_WEEKS_ANALYSE: int = 52


class PostgresConfig:
    HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    PORT: str = os.getenv("POSTGRES_PORT", "5432")
    USER: str = os.getenv("POSTGRES_USER", "postgres")
    PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    DB_NAME: str = os.getenv("POSTGRES_DB", "postgres")

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.DB_NAME}"
        )


base_config = BaseConfig()
postgres_config = PostgresConfig()
