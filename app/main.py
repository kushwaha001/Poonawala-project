"""FastAPI entrypoint — serves both the API and the web frontend."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.schemas import PropertyInput
from app.orchestrator import run_pipeline

app = FastAPI(
    title="Collateral Valuation & Resale Liquidity Engine",
    description="Bloomberg Terminal for Real Estate Collateral — 11-agent AI pipeline",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend-react" / "dist"

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/valuate", response_model=None)
async def valuate(prop: PropertyInput):
    try:
        input_data = prop.model_dump()
        result = await run_pipeline(input_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "collateral-valuation-v2", "agents": 11}
