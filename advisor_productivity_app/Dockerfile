# Multi-stage build for Deep Research App
# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-builder

ARG BACKEND_URL="http://localhost:8000"
ENV VITE_BACKEND_URL=${BACKEND_URL}

WORKDIR /app/frontend

# Copy frontend package files
COPY advisor_productivity_app/frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY advisor_productivity_app/frontend/ ./

# Build frontend with configured backend URL
RUN echo "Building frontend with VITE_BACKEND_URL=${VITE_BACKEND_URL}" && npm run build

# Stage 2: Build Backend
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY advisor_productivity_app/backend/requirements.txt ./

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

# Add framework to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV FRONTEND_DIST_PATH="/app/static"

# Copy backend application
COPY advisor_productivity_app/backend/app /app/app
COPY advisor_productivity_app/backend/requirements.txt /app/

# Copy built frontend static files to be served by FastAPI
COPY --from=frontend-builder /app/frontend/dist /app/static

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
