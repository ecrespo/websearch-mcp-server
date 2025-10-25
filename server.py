from config import TAVILY_API
from loguru_config import logger

from mcp.server import FastMCP

from tavily import TavilyClient
from typing import List,Dict

mcp = FastMCP(
    "WebSearch",
    host="0.0.0.0",
    port=9000,
    json_response=True
)
client = TavilyClient(api_key=TAVILY_API)


@mcp.tool()
def web_search(query: str)-> List[Dict]:
    """
    Use this tool to search the web for information using Tavily API.
    Executes a web search using the provided query string and returns a list of
    search results as dictionaries.

    This function connects to a search client, executes the search query, and
    fetches the results. If the search execution fails for any reason, the function
    will return an error message inside a dictionary.

    Args:
        query (str): The search query string to execute.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a
        search result. If an exception occurs, a single dictionary containing an
        error message is returned.
    """
    try:
        response = client.search(
            query=query
        )
        return response["results"]
    except Exception as e:
        logger.error(f"Error executing search: {str(e)}")
        return [{"message": "Error executing search."}]


if __name__ == "__main__":
    try:
        logger.info("Starting server...")
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("Stopping server...")
