from decouple import config
from typing import Optional


class Settings:
    """Configuración centralizada de la aplicación"""

    # Local Token Configuration
    LOCAL_TOKEN: str = config('LOCAL_TOKEN')

    # Tavily Configuration
    TAVILY_API_KEY: str = config('TAVILY_API_KEY')

    # Server Configuration
    MCP_SERVER_HOST: str = config('MCP_SERVER_HOST', default='0.0.0.0')
    MCP_SERVER_PORT: int = config('MCP_SERVER_PORT', default=8000, cast=int)

    # Logging Configuration
    LOG_LEVEL: str = config('LOG_LEVEL', default='INFO')
    LOG_FILE: str = config('LOG_FILE', default='logs/mcp_server.log')
    LOG_ROTATION: str = config('LOG_ROTATION', default='10 MB')
    LOG_RETENTION: str = config('LOG_RETENTION', default='7 days')

    # Session Configuration
    SESSION_TIMEOUT: int = config('SESSION_TIMEOUT', default=3600, cast=int)
    SESSION_CLEANUP_INTERVAL: int = config('SESSION_CLEANUP_INTERVAL', default=300, cast=int)

    @classmethod
    def validate(cls):
        """Valida que todas las configuraciones requeridas estén presentes"""
        required_fields = [
            'LOCAL_TOKEN',
            'TAVILY_API_KEY'
        ]

        missing = []
        for field in required_fields:
            if not getattr(cls, field, None):
                missing.append(field)

        if missing:
            raise ValueError(f"Faltan configuraciones requeridas: {', '.join(missing)}")


settings = Settings()