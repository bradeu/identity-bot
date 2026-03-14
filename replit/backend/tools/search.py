from typing import Dict, List, Optional, Any, TypedDict, Union
from mcp.server.fastmcp import FastMCP, Context
from infra.logger import logger

mcp = FastMCP("Search")

@mcp.tool()
def search(
    query: str,
    ctx: Context = None
) -> str:
    """
    Searches the public api for information based on the current context.
    
    Args:
        query: The query to search the public api for information.
        ctx: MCP context  
    """
    logger.debug(f"Searching for information based on the current context: {query}")
    return "I'm sorry, I can't search the public api for information based on the current context."