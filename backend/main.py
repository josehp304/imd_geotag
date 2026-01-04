import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add parent directory to sys.path to import convert_to_geojson
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from convert_to_geojson import parse_stations

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ogimet_data.txt")
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend/dist")

@app.get("/api/stations")
async def get_stations():
    stations = parse_stations(INPUT_FILE)
    return {
        "type": "FeatureCollection",
        "features": stations
    }

# Mount static files
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Allow other static files in root like favicon, etc. if they exist
        possible_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(possible_path):
            return FileResponse(possible_path)
        
        # Fallback to index.html for SPA routing
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
