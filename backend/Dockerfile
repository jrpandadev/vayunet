FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Install dependencies (frozen to ensure exact versions)
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Expose the port (Render sets this dynamically, but defaults to 8000)
ENV PORT=8000
EXPOSE $PORT

# Start Uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
