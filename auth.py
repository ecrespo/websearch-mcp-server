from typing import Optional, Dict
from config import settings
from logger import log


class LocalTokenValidator:
    """Validador de tokens locales"""

    def __init__(self):
        self.local_token = settings.LOCAL_TOKEN
        log.info("LocalTokenValidator inicializado")

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Valida un token local comparándolo con el token almacenado

        Args:
            token: Token a validar

        Returns:
            Diccionario con información del token si es válido, None si no lo es
        """
        try:
            log.debug("Validando token local")

            if not token:
                log.warning("Token vacío")
                return None

            if token == self.local_token:
                log.info("Token validado exitosamente")
                return {
                    "valid": True,
                    "type": "local_token"
                }
            else:
                log.warning("Token inválido")
                return None

        except Exception as e:
            log.error(f"Error inesperado validando token: {e}")
            log.exception("Detalles del error:")
            return None


class LocalTokenClient:
    """Cliente para obtener el token local"""

    def __init__(self):
        self.local_token = settings.LOCAL_TOKEN
        log.info("LocalTokenClient inicializado")

    def get_token(self) -> Optional[str]:
        """
        Obtiene el token local almacenado en configuración

        Returns:
            Token local
        """
        try:
            log.info("Obteniendo token local")
            log.debug(f"Token preview: {self.local_token[:20]}...")
            return self.local_token
        except Exception as e:
            log.error(f"Error obteniendo token local: {e}")
            log.exception("Detalles del error:")
            return None