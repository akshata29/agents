# Multi-stage build for patterns App
# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY patterns/frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY patterns/frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Build Backend
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY patterns/backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Add backend to Python path and expose frontend dist location
ENV PYTHONPATH=/app/backend
ENV FRONTEND_DIST_PATH=/app/frontend/dist

# Copy backend application code and config
COPY patterns/backend /app/backend
COPY patterns/backend/requirements.txt /app/

# Copy built frontend static files to be served by FastAPI
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Create necessary directories
RUN mkdir -p /app/backend/logs /app/backend/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set working directory for the backend runtime
WORKDIR /app/backend

# Run the application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
