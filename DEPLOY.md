# Deployment Guide

This application consists of a **FastAPI backend** and a **Vite (React) frontend**.

We have configured the application for a **Unified Deployment**, meaning the FastAPI backend serves the compiled frontend static files. This simplifies hosting as you only need to run the Python application.

## Prerequisites

1.  **Python 3.8+**
2.  **Node.js & npm** (only for building the frontend)

## Build Instructions

Before running in production, you must build the frontend:

```bash
cd frontend
npm install
npm run build
cd ..
```

This creates a `dist` folder in `frontend/` containing the optimized HTML, CSS, and JS.

## Running the Application

1.  **Install Python Dependencies:**
    
    ```bash
    cd backend
    pip install -r requirements.txt  # You should generate this first
    # Or manually:
    pip install fastapi uvicorn aiofiles
    ```

2.  **Run the Server:**
    
    ```bash
    # From the backend directory
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

    The application will be available at `http://your-server-ip:8000`.

## Production Hosting Options

### Option 1: Render / Railway / Heroku (Cloud PaaS)

This is the easiest method.

1.  Create a `requirements.txt` in the root (or backend, adjust configurations accordingly).
2.  Define a Start Command:
    *   `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3.  Add a Build Command (if the platform supports it):
    *   `npm install --prefix frontend && npm run build --prefix frontend && pip install -r requirements.txt`

### Option 2: VPS (DigitalOcean, AWS EC2, Linode)

1.  SSH into your server.
2.  Clone the repository.
3.  Run the **Build Instructions**.
4.  Set up **Gunicorn** with **Uvicorn** workers to run the app as a daemon (systemd service).
5.  (Optional but recommended) Set up **Nginx** as a reverse proxy on port 80/443 pointing to localhost:8000.

## Docker (Containerization)

You can containerize the application for consistent deployment.

**Dockerfile:**

```dockerfile
FROM python:3.9-slim

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y nodejs npm

WORKDIR /app

# Copy project
COPY . .

# Build Frontend
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Setup Backend
WORKDIR /app/backend
RUN pip install fastapi uvicorn aiofiles

# Clean up source files if desired (optional)

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
```
