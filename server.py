import asyncio
import time
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from mcp.server import Server
from mcp.types import Tool, TextContent
from tavily import TavilyClient

from config import settings
from logger import (
    log,
    console,
    log_section,
    log_table,
    log_json,
    log_panel,
    LogContext
)
from auth import LocalTokenValidator, LocalTokenClient


class SessionManager:
    """Gestor de sesiones con limpieza automática"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.cleanup_task = None
        log.info("SessionManager inicializado")

    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Crea una nueva sesión"""
        session = {
            "authenticated": False,
            "token": None,
            "payload": None,
            "created_at": time.time(),
            "last_activity": time.time()
        }
        self.sessions[session_id] = session
        log.info(f"Sesión creada: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una sesión existente"""
        session = self.sessions.get(session_id)
        if session:
            session["last_activity"] = time.time()
        return session

    def delete_session(self, session_id: str):
        """Elimina una sesión"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            log.info(f"Sesión eliminada: {session_id}")

    async def cleanup_expired_sessions(self):
        """Limpia sesiones expiradas periódicamente"""
        while True:
            try:
                await asyncio.sleep(settings.SESSION_CLEANUP_INTERVAL)

                current_time = time.time()
                expired = []

                for session_id, session in self.sessions.items():
                    if current_time - session["last_activity"] > settings.SESSION_TIMEOUT:
                        expired.append(session_id)

                for session_id in expired:
                    self.delete_session(session_id)

                if expired:
                    log.info(f"Limpiadas {len(expired)} sesiones expiradas")

            except Exception as e:
                log.error(f"Error en limpieza de sesiones: {e}")

    def start_cleanup(self):
        """Inicia la tarea de limpieza"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self.cleanup_expired_sessions())
            log.info("Tarea de limpieza de sesiones iniciada")

    def stop_cleanup(self):
        """Detiene la tarea de limpieza"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            log.info("Tarea de limpieza de sesiones detenida")


class MCPServerSSE:
    """Servidor MCP con autenticación local, Tavily y transporte SSE"""

    def __init__(self):
        self.mcp_server = Server("mcp-websearch-server")
        self.auth_validator = LocalTokenValidator()
        self.auth_client = LocalTokenClient()
        self.tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        self.session_manager = SessionManager()

        self.current_session_id: Optional[str] = None

        log.info("MCPServerSSE inicializado")
        self._register_mcp_handlers()

    def _register_mcp_handlers(self):
        """Registra los handlers del servidor MCP"""

        @self.mcp_server.list_tools()
        async def list_tools() -> List[Tool]:
            """Lista las herramientas disponibles"""
            log.debug("Listando herramientas disponibles")
            return [
                Tool(
                    name="authenticate",
                    description="Autentica la sesión usando el token local configurado en el servidor",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="web_search",
                    description="Busca información en la web usando Tavily. Requiere autenticación previa.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Consulta de búsqueda"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Número máximo de resultados (por defecto: 5)",
                                "default": 5
                            },
                            "search_depth": {
                                "type": "string",
                                "description": "Profundidad de búsqueda: 'basic' o 'advanced'",
                                "enum": ["basic", "advanced"],
                                "default": "basic"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="validate_token",
                    description="Valida un token local comparándolo con el token configurado en el servidor",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "token": {
                                "type": "string",
                                "description": "Token local a validar"
                            }
                        },
                        "required": ["token"]
                    }
                )
            ]

        @self.mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Ejecuta una herramienta"""
            log.info(f"Llamando herramienta: {name}")

            session_id = self.current_session_id

            if name == "authenticate":
                return await self._authenticate(session_id)

            elif name == "validate_token":
                return await self._validate_token(arguments.get("token"))

            elif name == "web_search":
                if not self._is_authenticated(session_id):
                    log.warning(f"Intento de búsqueda sin autenticación en sesión: {session_id}")
                    return [TextContent(
                        type="text",
                        text="❌ Error: Debes autenticarte primero usando la herramienta 'authenticate'"
                    )]

                return await self._web_search(
                    query=arguments.get("query"),
                    max_results=arguments.get("max_results", 5),
                    search_depth=arguments.get("search_depth", "basic")
                )

            else:
                log.warning(f"Herramienta desconocida: {name}")
                return [TextContent(
                    type="text",
                    text=f"❌ Herramienta desconocida: {name}"
                )]

    def _is_authenticated(self, session_id: Optional[str]) -> bool:
        """Verifica si una sesión está autenticada"""
        if not session_id:
            return False

        session = self.session_manager.get_session(session_id)
        if not session:
            return False

        return session.get("authenticated", False)

    async def _authenticate(self, session_id: Optional[str]) -> List[TextContent]:
        """Autentica usando el token local configurado"""
        with LogContext("AUTENTICACIÓN", "yellow"):
            try:
                log.info(f"Iniciando autenticación para sesión: {session_id}")

                token = self.auth_client.get_token()

                if not token:
                    log.error("No se pudo obtener token local")
                    return [TextContent(
                        type="text",
                        text="❌ Error al obtener token local. Verifica la configuración."
                    )]

                log.debug("Token obtenido, procediendo a validar...")

                # Validar el token obtenido
                payload = self.auth_validator.validate_token(token)

                if not payload:
                    log.error("Token obtenido pero no es válido")
                    return [TextContent(
                        type="text",
                        text="❌ Token obtenido pero no es válido"
                    )]

                # Guardar en sesión
                if session_id:
                    session = self.session_manager.get_session(session_id)
                    if not session:
                        session = self.session_manager.create_session(session_id)

                    session["authenticated"] = True
                    session["token"] = token
                    session["payload"] = payload

                    log.success(f"✅ Sesión {session_id} autenticada exitosamente")

                return [TextContent(
                    type="text",
                    text=f"✅ Autenticación exitosa!\n\n"
                         f"Token local válido.\n"
                         f"Tipo: {payload.get('type')}"
                )]

            except Exception as e:
                log.exception(f"Error durante la autenticación: {e}")
                return [TextContent(
                    type="text",
                    text=f"❌ Error durante la autenticación: {str(e)}"
                )]

    async def _validate_token(self, token: str) -> List[TextContent]:
        """Valida un token local"""
        if not token:
            log.warning("Intento de validación sin token")
            return [TextContent(
                type="text",
                text="❌ Token no proporcionado"
            )]

        payload =  self.auth_validator.validate_token(token)

        if payload:
            log.info("Token validado exitosamente")
            return [TextContent(
                type="text",
                text=f"✅ Token válido\n\n"
                     f"Tipo: {payload.get('type')}\n"
                     f"Válido: {payload.get('valid')}"
            )]
        else:
            log.warning("Token inválido")
            return [TextContent(
                type="text",
                text="❌ Token inválido"
            )]

    async def _web_search(
            self,
            query: str,
            max_results: int = 5,
            search_depth: str = "basic"
    ) -> List[TextContent]:
        """Realiza una búsqueda web con Tavily"""
        with LogContext("BÚSQUEDA WEB", "cyan"):
            try:
                search_params = {
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth
                }
                log_table("Parámetros de Búsqueda", search_params)

                log.info("Ejecutando búsqueda en Tavily...")
                response = self.tavily_client.search(
                    query=query,
                    max_results=max_results,
                    search_depth=search_depth
                )

                if response.get('results'):
                    log.success(f"✅ Encontrados {len(response['results'])} resultados")

                    results_text = f"🔍 Resultados para: '{query}'\n\n"

                    for i, result in enumerate(response['results'], 1):
                        results_text += f"{i}. **{result.get('title', 'Sin título')}**\n"
                        results_text += f"   URL: {result.get('url', 'N/A')}\n"
                        results_text += f"   {result.get('content', 'Sin contenido')}\n"
                        results_text += f"   Score: {result.get('score', 'N/A')}\n\n"

                    if response.get('answer'):
                        results_text += f"\n📝 **Resumen:**\n{response['answer']}\n"

                    return [TextContent(type="text", text=results_text)]
                else:
                    log.warning("No se encontraron resultados")
                    return [TextContent(
                        type="text",
                        text="No se encontraron resultados.\n"
                    )]

            except Exception as e:
                log.exception(f"Error en la búsqueda: {e}")
                return [TextContent(
                    type="text",
                    text=f"❌ Error en la búsqueda: {str(e)}"
                )]

    async def handle_tool_call(self, tool_name: str, arguments: dict, session_id: str) -> List[TextContent]:
        """Método auxiliar para manejar llamadas desde HTTP"""
        self.current_session_id = session_id

        if tool_name == "authenticate":
            return await self._authenticate(session_id)
        elif tool_name == "validate_token":
            return await self._validate_token(arguments.get("token"))
        elif tool_name == "web_search":
            if not self._is_authenticated(session_id):
                return [TextContent(
                    type="text",
                    text="❌ Error: Debes autenticarte primero usando la herramienta 'authenticate'"
                )]
            return await self._web_search(
                query=arguments.get("query"),
                max_results=arguments.get("max_results", 5),
                search_depth=arguments.get("search_depth", "basic")
            )
        else:
            return [TextContent(
                type="text",
                text=f"❌ Herramienta desconocida: {tool_name}"
            )]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    log.info("🚀 Iniciando servidor MCP...")

    try:
        settings.validate()
        log.info("✅ Configuración validada")
    except ValueError as e:
        log.error(f"❌ Error en configuración: {e}")
        raise

    mcp_server_instance.session_manager.start_cleanup()

    log.info(f"✅ Servidor listo en {settings.MCP_SERVER_HOST}:{settings.MCP_SERVER_PORT}")

    yield

    log.info("🛑 Deteniendo servidor MCP...")
    mcp_server_instance.session_manager.stop_cleanup()
    log.info("✅ Servidor detenido correctamente")


app = FastAPI(
    title="MCP Server with Auth0 and Tavily",
    description="Servidor MCP con autenticación Auth0 y búsqueda Tavily",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp_server_instance = MCPServerSSE()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    log.debug("Health check solicitado")
    return JSONResponse({
        "status": "healthy",
        "sessions": len(mcp_server_instance.session_manager.sessions),
        "version": "1.0.0"
    })


@app.get("/sse/{session_id}")
async def sse_endpoint(session_id: str, request: Request):
    """Endpoint SSE para comunicación en tiempo real"""
    log.info(f"Nueva conexión SSE: {session_id}")

    if not mcp_server_instance.session_manager.get_session(session_id):
        mcp_server_instance.session_manager.create_session(session_id)

    async def event_generator():
        try:
            yield f"event: connected\ndata: {{'session_id': '{session_id}', 'message': 'Conectado al servidor MCP'}}\n\n"
            log.info(f"Cliente SSE conectado: {session_id}")

            while True:
                if await request.is_disconnected():
                    log.info(f"Cliente SSE desconectado: {session_id}")
                    break

                await asyncio.sleep(30)
                yield f"event: heartbeat\ndata: {{'timestamp': {time.time()}}}\n\n"

        except asyncio.CancelledError:
            log.info(f"Conexión SSE cancelada: {session_id}")
        except Exception as e:
            log.error(f"Error en SSE: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/mcp/{session_id}")
async def handle_mcp_request(session_id: str, request: Request):
    """Handler para peticiones MCP sobre HTTP"""
    log.debug(f"Petición MCP recibida para sesión: {session_id}")

    if not mcp_server_instance.session_manager.get_session(session_id):
        mcp_server_instance.session_manager.create_session(session_id)

    try:
        body = await request.json()
        method = body.get('method')
        params = body.get('params', {})
        request_id = body.get('id')

        log.debug(f"Método MCP: {method}")

        if method == 'tools/list':
            tools_list = await mcp_server_instance.mcp_server.list_tools()

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools_list
                    ]
                }
            })

        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})

            result = await mcp_server_instance.handle_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                session_id=session_id
            )

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": item.type, "text": item.text}
                        for item in result
                    ]
                }
            })

        else:
            log.warning(f"Método no soportado: {method}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Método no soportado: {method}"
                }
            }, status_code=400)

    except Exception as e:
        log.exception(f"Error procesando petición MCP: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get('id') if 'body' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Error interno: {str(e)}"
            }
        }, status_code=500)


@app.get("/session/{session_id}/status")
async def session_status(session_id: str):
    """Endpoint para verificar estado de sesión"""
    log.debug(f"Consultando estado de sesión: {session_id}")

    session = mcp_server_instance.session_manager.get_session(session_id)

    if session:
        return JSONResponse({
            "session_id": session_id,
            "authenticated": session.get("authenticated", False),
            "has_token": session.get("token") is not None,
            "created_at": session.get("created_at"),
            "last_activity": session.get("last_activity")
        })
    else:
        log.warning(f"Sesión no encontrada: {session_id}")
        raise HTTPException(status_code=404, detail="Sesión no encontrada")


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Endpoint para eliminar una sesión"""
    log.info(f"Eliminando sesión: {session_id}")

    mcp_server_instance.session_manager.delete_session(session_id)

    return JSONResponse({
        "message": f"Sesión {session_id} eliminada correctamente"
    })


def main():
    """Punto de entrada principal"""
    log_section("SERVIDOR MCP CON AUTH0 Y TAVILY", "bold magenta")

    config_data = {
        "Host": settings.MCP_SERVER_HOST,
        "Port": settings.MCP_SERVER_PORT,
        "Log Level": settings.LOG_LEVEL,
        "Log File": settings.LOG_FILE,
        "Session Timeout": f"{settings.SESSION_TIMEOUT}s",
    }
    log_table("Configuración del Servidor", config_data)

    log.info("Iniciando servidor...")

    uvicorn.run(
        app,
        host=settings.MCP_SERVER_HOST,
        port=settings.MCP_SERVER_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()