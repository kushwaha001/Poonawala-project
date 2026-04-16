# Collateral Valuation & Resale Liquidity Engine

**AI-Powered Estimation Portal — "Bloomberg Terminal for Real Estate Collateral"**

An 11-agent AI system that answers two questions together for property-backed lending:
1. **What is the asset worth today?** (Market Value + Distress Value, as ranges)
2. **How easily can it be liquidated?** (Resale Potential Index + Time-to-Sell)

---

## Quick Start (Any System)

### Prerequisites
- **Python 3.10+** (tested on 3.13)
- **Git** (to clone the repo)
- No API keys required — works fully offline

### Setup (One Command)

```bash
git clone <repo-url> collateral-engine
cd collateral-engine
bash setup.sh
```

This creates a virtual environment, installs pinned dependencies, and runs all tests.

### Start the Web App

```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

### Run Tests

```bash
source venv/bin/activate
python -m pytest tests/test_valuation_math.py -v    # 47 math tests
python tests/run_pipeline_test.py                     # 5 pipeline scenarios
python tests/test_poonawala_fincorp.py                # 6 Poonawalla LAP tests
```

---

## Manual Setup (Step by Step)

If `setup.sh` doesn't work on your system:

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows CMD
# venv\Scripts\Activate.ps1       # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.lock.txt

# 4. Copy env file
cp .env.example .env

# 5. Run tests
python -m pytest tests/test_valuation_math.py -v

# 6. Start server
python -m uvicorn app.main:app --reload --port 8000
```

---

## Windows-Specific Notes

```powershell
# Use python instead of python3
python -m venv venv
venv\Scripts\activate
pip install -r requirements.lock.txt
python -m uvicorn app.main:app --reload --port 8000
```

---

## API Usage

```bash
curl -X POST http://localhost:8000/valuate \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Baner, Pune",
    "property_type": "residential",
    "sub_type": "apartment",
    "built_up_area_sqft": 850,
    "age_years": 5,
    "configuration": "2BHK",
    "ownership": "freehold",
    "title_clear": true
  }'
```

---

## Project Structure

```
collateral-engine/
├── app/
│   ├── main.py              # FastAPI + frontend server
│   ├── orchestrator.py       # 11-agent DAG executor
│   ├── schemas.py            # Pydantic I/O models
│   ├── agents/               # 11 specialized agents
│   ├── math/formulas.py      # All valuation math (pure functions)
│   ├── config/constants.py   # All tunable constants
│   ├── tools/                # Geocoding, OSM, circle rate, LLM
│   └── data/                 # CSV data files
├── frontend/index.html       # Bloomberg-style web UI
├── tests/                    # 47 + 5 + 6 = 58 tests
├── requirements.txt          # Loose deps
├── requirements.lock.txt     # Pinned deps (use this)
├── setup.sh                  # One-command setup
├── .env.example              # Environment template
└── README.md                 # This file
```

---

## Tech Stack (All Free)

| Component | Tool | License |
|-----------|------|---------|
| Backend | Python 3.13 + FastAPI | MIT |
| Math | Pure Python (deterministic) | — |
| LLM | Claude (optional, free) | — |
| Geocoding | Nominatim / OpenStreetMap | ODbL |
| POI Data | Overpass API (OSM) | ODbL |
| Frontend | HTML/CSS/JS + Chart.js | MIT |
| Data | Government circle rates | Public |
