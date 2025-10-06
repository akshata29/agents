"""
Yahoo Finance MCP Server - Azure Container Apps Entry Point

This module provides a FastAPI wrapper around the Yahoo Finance MCP server
for deployment to Azure Container Apps with SSE (Server-Sent Events) transport.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Header
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount
from yahoo_finance_server import yfinance_server
import uvicorn
import os
from typing import Optional

# Initialize FastAPI app
app = FastAPI(
    title="Yahoo Finance MCP Server",
    description="Model Context Protocol server for Yahoo Finance data",
    version="1.0.0",
    docs_url="/docs",  # Enable OpenAPI docs at /docs
    redoc_url="/redoc"  # Enable ReDoc at /redoc
)

# API Key Authentication (optional - configure via environment variable)
MCP_API_KEY = os.getenv("MCP_API_KEY")  # Set this in Container App environment


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if MCP_API_KEY is configured."""
    if MCP_API_KEY:
        if not x_api_key or x_api_key != MCP_API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key. Provide X-API-Key header."
            )
    return True


# Initialize SSE transport
sse = SseServerTransport("/messages/")

# Mount the SSE message handler
app.router.routes.append(Mount("/messages", app=sse.handle_post_message))


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - returns server info."""
    return {
        "name": "Yahoo Finance MCP Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Azure Container Apps."""
    return {
        "status": "healthy",
        "service": "yahoo-finance-mcp",
        "version": "1.0.0"
    }


@app.get("/sse", tags=["MCP"], dependencies=[Depends(verify_api_key)])
async def handle_sse(request: Request):
    """
    SSE endpoint for MCP protocol communication.
    
    This endpoint handles Server-Sent Events for the Model Context Protocol,
    allowing clients to connect and interact with the Yahoo Finance tools.
    """
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send
    ) as streams:
        read_stream, write_stream = streams
        init_options = yfinance_server._mcp_server.create_initialization_options()
        await yfinance_server._mcp_server.run(
            read_stream,
            write_stream,
            init_options,
        )


if __name__ == "__main__":
    # Get port from environment variable (Azure Container Apps uses PORT)
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
