import uuid
import httpx
from typing import List, Dict
from loguru_config import logger


class MCPClient:
    """
    A client to connect to an MCP server, manage the session lifecycle,
    and execute tools like `web_search`.
    """

    def __init__(self, server_host: str, server_port: int):
        """
        Initialize the MCP client with the server's host/port.
        """
        self.base_url = f"http://{server_host}:{server_port}/mcp"
        # Generate and persist a unique session ID for this client instance
        self.session_id = str(uuid.uuid4())
        # Base headers required by Streamable HTTP transport
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            # Provide the session ID at the HTTP layer as required by the transport
            "mcp-session-id": self.session_id,
        }
        logger.info(f"Generated session ID: {self.session_id}")

    def web_search(self, query: str) -> List[Dict]:
        """
        Request a web search operation using the `web_search` tool.

        Args:
            query (str): Search query string.

        Returns:
            List[Dict]: Search result or error message.
        """
        # The Streamable HTTP transport requires the session ID to be provided
        # at the HTTP layer via the 'mcp-session-id' header. Do NOT send it as
        # a query parameter, as the server will reject it.
        url = self.base_url
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),  # Unique ID for this request
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {"query": query},
                "stream": False,
            },
        }

        try:
            logger.debug(f"Sending payload: {payload}")
            response = httpx.post(url, json=payload, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "error" in data:
                return [{"message": f"Server error: {data['error'].get('message', 'unknown')}"}]

            return data.get("result", [{"message": "No valid results in response."}])
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return [{"message": "Connection error."}]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            return [{"message": f"HTTP error {e.response.status_code} from server."}]
        except ValueError as e:
            logger.error("Error decoding server response as JSON.")
            return [{"message": "Error decoding server response."}]


if __name__ == "__main__":
    # Example client usage
    client = MCPClient(server_host="127.0.0.1", server_port=9000)

    # Test with a sample query
    search_query = "What is HTTPX?"
    logger.info(f"Sending query: {search_query}")
    results = client.web_search(search_query)
    logger.info(f"Results: {results}")