# DSA Group 3 — ML Full Stack Project

A full stack machine learning application with a React frontend, FastAPI backend, and a self-contained ML model package. Python dependencies are managed with **uv workspaces**; the model folder additionally uses **conda** for GPU/system-level dependencies.

---

## Project Structure

```
project-root/
├── pyproject.toml        # uv workspace root
├── uv.lock               # single Python lockfile
├── Makefile              # common commands (make)
├── Justfile              # common commands (just — alternative to make)
├── start.sh              # starts all services at once (dev mode)
├── docker-compose.yml    # container orchestration
├── CONTRIBUTING.md       # contribution guide
│
├── frontend/             # React application
├── backend/              # FastAPI application
└── model/                # ML model package (training + inference)
```

See each folder's own `README.md` for detailed setup and usage:
- [frontend/README.md](frontend/README.md)
- [backend/README.md](backend/README.md)
- [model/README.md](model/README.md)

---

## Prerequisites

| Tool | Purpose |
|---|---|
| Node.js >= 18 | Frontend |
| Python >= 3.11 | Backend + Model |
| [uv](https://docs.astral.sh/uv/) | Python dependency management |
| conda / miniconda | Model GPU/system deps |
| Docker + Docker Compose | Containerised startup |

---

## Quick Start — Local Dev (`start.sh`)

`start.sh` starts the frontend and backend together in dev mode with a single command. Press `Ctrl+C` to stop all services cleanly.

**1. Install all dependencies:**
```bash
make install
# or
just install
```

**2. Copy and fill in environment files:**
```bash
make env_copy
# or
just env_copy
```

**3. Set up the model conda environment (first time only):**
```bash
conda env create -f model/environment.yml
conda activate ml-env
```

**4. Start all services:**
```bash
bash start.sh
# or
make dev
# or
just dev
```

Services will be available at:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Quick Start — Docker

Docker runs all services in containers. Make sure Docker Desktop is running.

**1. Copy environment files:**
```bash
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

**2. Build images:**
```bash
make build
# or
just build
# or
docker-compose build
```

**3. Start all containers:**
```bash
make up
# or
just up
# or
docker-compose up
```

**4. Stop all containers:**
```bash
make down
# or
just down
# or
docker-compose down
```

The `backend` service mounts `model/saved_models/` so trained model artifacts are shared between the host and the container without rebuilding the image.

---

## Commands

Both `make` and `just` are supported. Use whichever you prefer — they run the same operations.

To install `just`:
```bash
brew install just   # macOS
```

Run `just` with no arguments to list all available commands.

| make | just | Description |
|---|---|---|
| `make install` | `just install` | Install frontend (npm) and Python (uv) dependencies |
| `make dev` | `just dev` | Start all services in dev mode via `start.sh` |
| `make build` | `just build` | Build Docker images |
| `make up` | `just up` | Start all Docker containers |
| `make down` | `just down` | Stop all Docker containers |
| `make train` | `just train` | Run model training |
| `make clean` | `just clean` | Remove build artifacts and caches |

---

## How the Services Connect

```
Browser
  └── Frontend (React :5173)
        └── HTTP requests → Backend (FastAPI :8000)
                              └── imports → Model package
                                             └── loads → model/saved_models/
```

The backend imports directly from the `model` Python package via uv workspace linking. It loads trained artifacts from `model/saved_models/` at runtime.
