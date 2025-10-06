# Multi-stage build for Multimodal Insights App
# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY multimodal_insights_app/frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY multimodal_insights_app/frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Build Backend
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY multimodal_insights_app/backend/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (ffmpeg for video processing, libmagic for file type detection)
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy framework directory structure (we're using it as a local package, not building it yet)
COPY framework/ /app/framework/

# Add framework to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Copy backend application
COPY multimodal_insights_app/backend/app /app/app
COPY multimodal_insights_app/backend/requirements.txt /app/

# Copy built frontend static files to be served by FastAPI
COPY --from=frontend-builder /app/frontend/dist /app/static

# Create necessary directories
RUN mkdir -p /app/uploads /app/data /app/exports /app/reports /app/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
