# AgroDiag MVP (local)

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test request
```bash
curl -X POST http://127.0.0.1:8000/v1/diagnose   -F crop=tomato   -F symptoms_text="бурі водянисті плями та білий наліт знизу листка"   -F growth_stage=vegetative
```
