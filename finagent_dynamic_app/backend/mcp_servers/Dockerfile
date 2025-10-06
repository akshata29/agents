# Yahoo Finance MCP Server - Dockerfile for Azure Container Apps

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY yahoo_finance_server.py .
COPY main.py .
COPY __init__.py .

# Expose port (Azure Container Apps will override this)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run the server
CMD ["python", "main.py"]
