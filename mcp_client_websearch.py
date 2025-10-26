import asyncio
import json
import httpx
from logger import (
    log,
    console,
    log_section,
    log_table,
    log_json,
    log_panel,
    log_status,
    LogContext
)


class MCPClientHTTP:
    """Cliente para conectarse al servidor MCP vía HTTP/SSE"""

    def __init__(self, base_url: str = "http://localhost:8000", session_id: str = "test-session"):
        self.base_url = base_url
        self.session_id = session_id
        self.client = httpx.AsyncClient(timeout=30.0)

        log_panel(
            f"Cliente MCP inicializado\n"
            f"URL: {base_url}\n"
            f"Session ID: {session_id}",
            title="🚀 Cliente MCP",
            style="green"
        )

    async def health_check(self):
        """Verifica el estado del servidor"""
        url = f"{self.base_url}/health"

        with log_status("Verificando salud del servidor..."):
            try:
                response = await self.client.get(url)
                result = response.json()

                log_json(result, "✅ Estado del Servidor")
                return result
            except Exception as e:
                log.error(f"❌ Error en health check: {e}")
                return None

    async def list_tools(self):
        """Lista las herramientas disponibles"""
        url = f"{self.base_url}/mcp/{self.session_id}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        with log_status("Listando herramientas disponibles..."):
            response = await self.client.post(url, json=payload)
            result = response.json()

        tools = result.get('result', {}).get('tools', [])

        if tools:
            console.print("\n[bold cyan]🛠️  Herramientas Disponibles:[/bold cyan]")
            for tool in tools:
                console.print(f"  • [green]{tool['name']}[/green]: {tool['description']}")

        return result

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Llama a una herramienta"""
        url = f"{self.base_url}/mcp/{self.session_id}"

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        with LogContext(f"Herramienta: {tool_name}", "yellow"):
            if arguments:
                log_table("Argumentos", arguments)

            with log_status(f"Ejecutando {tool_name}..."):
                response = await self.client.post(url, json=payload)
                result = response.json()

            if 'result' in result:
                for content in result['result'].get('content', []):
                    log_panel(
                        content.get('text'),
                        title="📝 Resultado",
                        style="green"
                    )
            elif 'error' in result:
                log_json(result['error'], "❌ Error")

        return result

    async def get_session_status(self):
        """Obtiene el estado de la sesión"""
        url = f"{self.base_url}/session/{self.session_id}/status"

        with log_status("Consultando estado de sesión..."):
            response = await self.client.get(url)
            status = response.json()

        log_table("📊 Estado de Sesión", status)
        return status

    async def delete_session(self):
        """Elimina la sesión"""
        url = f"{self.base_url}/session/{self.session_id}"

        with log_status("Eliminando sesión..."):
            response = await self.client.delete(url)
            result = response.json()

        log.success(f"🗑️  {result.get('message')}")
        return result

    async def close(self):
        """Cierra el cliente"""
        await self.client.aclose()
        log.info("Cliente cerrado correctamente")


async def main():
    """Función de prueba"""

    log_section("PRUEBAS DEL CLIENTE MCP", "bold magenta")

    client = MCPClientHTTP(session_id="demo-session")

    try:
        # 1. Health check
        log_section("1. Health Check", "cyan")
        await client.health_check()

        # 2. Listar herramientas
        log_section("2. Listando Herramientas", "cyan")
        await client.list_tools()

        # 3. Estado inicial
        log_section("3. Estado Inicial de Sesión", "cyan")
        await client.get_session_status()

        # 4. Autenticar
        log_section("4. Autenticando con Auth0", "cyan")
        await client.call_tool("authenticate")

        # 5. Estado después de autenticar
        log_section("5. Estado Post-Autenticación", "cyan")
        await client.get_session_status()

        # 6. Búsqueda web
        log_section("6. Búsqueda Web", "cyan")
        await client.call_tool("web_search", {
            "query": "Python FastAPI tutorial",
            "max_results": 3,
            "search_depth": "basic"
        })

        # 7. Eliminar sesión
        log_section("7. Limpieza", "cyan")
        await client.delete_session()

        log_section("PRUEBAS COMPLETADAS ✓", "bold green")

    except Exception as e:
        log.exception("Error durante las pruebas")
        log_section("PRUEBAS FALLIDAS ✗", "bold red")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())