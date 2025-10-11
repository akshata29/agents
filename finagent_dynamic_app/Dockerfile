# Multi-stage build for Finagent Dynamic App

# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY finagent_dynamic_app/frontend/package*.json ./
RUN npm ci
COPY finagent_dynamic_app/frontend/ ./
RUN npm run build

# Stage 2: Build Backend
FROM python:3.11-slim AS backend-builder
COPY finagent_dynamic_app/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Add framework to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Copy backend application
COPY finagent_dynamic_app/backend/app /app/app
COPY finagent_dynamic_app/backend/requirements.txt /app/

# Copy built frontend static files to be served by FastAPI
COPY --from=frontend-builder /app/frontend/dist /app/static

# Create necessary directories
RUN mkdir -p /app/reports /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
