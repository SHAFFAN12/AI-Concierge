# Agentic-AI — Phase 1 Prototype


## Structure
See `tree` in repo root.


## Quickstart (local, dev mode)


1. Backend (Python):
```bash
cd backend
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install
uvicorn app.main:app --reload --port 8000