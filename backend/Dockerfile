FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

# Copy workspace root config
COPY pyproject.toml uv.lock* ./

# Copy both packages (backend needs model as a workspace dep)
COPY backend/ ./backend/
COPY model/ ./model/

# Install the full workspace
RUN uv sync --frozen

WORKDIR /app/backend

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
