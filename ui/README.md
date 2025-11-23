# AgroDiag — Streamlit UI

## Запуск
1) Активуй venv (або створи новий):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Переконайся, що бекенд працює локально на http://127.0.0.1:8000

3) Запусти Streamlit:
```powershell
streamlit run app.py
```
UI відкриється у браузері (http://localhost:8501).

### Налаштування адреси бекенда (необов'язково)
Створи файл `.streamlit/secrets.toml`:
```toml
BACKEND_URL = "http://127.0.0.1:8000/v1/diagnose"
```
