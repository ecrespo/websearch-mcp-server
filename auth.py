import httpx
from typing import Optional, Dict
from authlib.jose import jwt, JsonWebKey
from authlib.jose.errors import JoseError
import json
from config import settings
from logger import log


class Auth0Validator:
    """Validador de tokens JWT de Auth0"""

    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.audience = settings.AUTH0_AUDIENCE
        self.algorithm = settings.AUTH0_ALGORITHM
        self.jwks_uri = f'https://{self.domain}/.well-known/jwks.json'
        self._jwks = None
        log.info(f"Auth0Validator inicializado para dominio: {self.domain}")

    def get_jwks(self) -> Dict:
        """Obtiene las claves públicas de Auth0"""
        if self._jwks is None:
            try:
                log.debug(f"Obteniendo JWKS desde: {self.jwks_uri}")
                response = httpx.get(self.jwks_uri, timeout=10)
                response.raise_for_status()
                self._jwks = response.json()
                log.info("JWKS obtenido exitosamente")
            except Exception as e:
                log.error(f"Error obteniendo JWKS: {e}")
                raise
        return self._jwks

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Valida un token JWT de Auth0

        Args:
            token: Token JWT a validar

        Returns:
            Payload del token si es válido, None si no lo es
        """
        try:
            log.debug("Validando token JWT")

            # Obtener las claves públicas
            jwks_data = self.get_jwks()

            # Decodificar el token sin verificar para obtener el header
            import base64

            # Separar el token en sus partes
            parts = token.split('.')
            if len(parts) != 3:
                log.error("Token JWT malformado")
                return None

            # Decodificar el header (primera parte)
            header_data = parts[0]
            # Agregar padding si es necesario
            header_data += '=' * (4 - len(header_data) % 4)

            try:
                header = json.loads(base64.urlsafe_b64decode(header_data))
                kid = header.get('kid')
                log.debug(f"Token kid: {kid}")
            except Exception as e:
                log.error(f"Error decodificando header: {e}")
                return None

            # Buscar la clave pública correspondiente
            public_key = None
            for jwk in jwks_data.get('keys', []):
                if jwk.get('kid') == kid:
                    public_key = jwk
                    break

            if not public_key:
                log.warning(f"No se encontró la clave con kid: {kid}")
                return None

            # Validar el token usando authlib
            claims_options = {
                'aud': {'essential': True, 'value': self.audience},
                'iss': {'essential': True, 'value': f'https://{self.domain}/'}
            }

            # Decodificar y validar
            claims = jwt.decode(
                token,
                public_key,
            )

            # Validar claims manualmente
            claims.validate()

            # Verificar audience
            token_aud = claims.get('aud')
            if isinstance(token_aud, list):
                if self.audience not in token_aud:
                    log.error(f"Audience inválido: {token_aud}")
                    return None
            elif token_aud != self.audience:
                log.error(f"Audience inválido: {token_aud}")
                return None

            # Verificar issuer
            token_iss = claims.get('iss')
            expected_iss = f'https://{self.domain}/'
            if token_iss != expected_iss:
                log.error(f"Issuer inválido: {token_iss}")
                return None

            log.info(f"Token validado exitosamente. Subject: {claims.get('sub')}")
            return dict(claims)

        except JoseError as e:
            log.error(f"Error JOSE validando token: {e}")
            return None
        except Exception as e:
            log.error(f"Error inesperado validando token: {e}")
            log.exception("Detalles del error:")
            return None


class Auth0Client:
    """Cliente para obtener tokens de Auth0"""

    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.client_id = settings.AUTH0_CLIENT_ID
        self.client_secret = settings.AUTH0_CLIENT_SECRET
        self.audience = settings.AUTH0_AUDIENCE
        log.info(f"Auth0Client inicializado para cliente: {self.client_id}")

    def get_token(self) -> Optional[str]:
        """
        Obtiene un token de acceso usando Client Credentials Flow

        Returns:
            Token de acceso o None si hay error
        """
        url = f'https://{self.domain}/oauth/token'

        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': self.audience,
            'grant_type': 'client_credentials'
        }

        headers = {'content-type': 'application/json'}

        try:
            log.debug(f"Solicitando token a: {url}")
            response = httpx.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            token = response.json().get('access_token')

            if token:
                log.info("Token obtenido exitosamente")
                log.debug(f"Token preview: {token[:50]}...")
            else:
                log.error("No se recibió token en la respuesta")

            return token
        except httpx.exceptions.RequestException as e:
            log.error(f"Error HTTP obteniendo token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                log.error(f"Respuesta del servidor: {e.response.text}")
            return None
        except Exception as e:
            log.error(f"Error inesperado obteniendo token: {e}")
            log.exception("Detalles del error:")
            return None