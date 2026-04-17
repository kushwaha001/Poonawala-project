"""FastAPI entrypoint — serves both the API and the web frontend."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from app.schemas import PropertyInput
from app.orchestrator import run_pipeline
from app.tools.llm import chat_with_user

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

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


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


class ChatMessage(BaseModel):
    message: str
    history: Optional[list[dict]] = []


@app.post("/chat")
async def chat(req: ChatMessage):
    try:
        result = await chat_with_user(req.message, req.history or [])
        # If the chatbot wants to trigger valuation and extracted_fields has enough data,
        # run the pipeline and attach the result
        if result.get("trigger_valuation") and result.get("extracted_fields"):
            ef = result["extracted_fields"]
            if ef.get("city") and ef.get("sub_type") and ef.get("built_up_area_sqft") and ef.get("age_years"):
                try:
                    address = f"{ef.get('locality', '')}, {ef['city']}".strip(", ")
                    pipeline_input = {
                        "address": address,
                        "property_type": ef.get("property_type", "residential"),
                        "sub_type": ef["sub_type"],
                        "built_up_area_sqft": float(ef["built_up_area_sqft"]),
                        "age_years": int(ef["age_years"]),
                        "configuration": ef.get("configuration"),
                        "floor": ef.get("floor"),
                        "total_floors": ef.get("total_floors"),
                        "has_lift": ef.get("has_lift"),
                        "ownership": ef.get("ownership"),
                        "title_clear": ef.get("title_clear"),
                        "monthly_rent": ef.get("monthly_rent"),
                        "occupancy": ef.get("occupancy"),
                        "rera_registered": ef.get("rera_registered"),
                        "builder_name": ef.get("builder_name"),
                    }
                    valuation = await run_pipeline(pipeline_input)
                    result["valuation_result"] = valuation
                except Exception as ve:
                    result["valuation_error"] = str(ve)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "collateral-valuation-v2", "agents": 11}
