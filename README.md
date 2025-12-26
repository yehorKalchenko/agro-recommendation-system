# AgroDiag 

---

## Overview

AgroDiag is an intelligent diagnostic system that helps farmers and agronomists identify plant diseases through symptom descriptions and image analysis. It combines traditional knowledge base retrieval (RAG) with modern AI technologies (AWS Bedrock, Rekognition) to provide accurate, actionable recommendations.

**Key Features:**
- **10 Supported Crops**: tomato, potato, pepper, cucumber, onion, garlic, cabbage, carrot, beet, wheat
- **50+ Diseases**: Comprehensive knowledge base with detailed action plans
- **6-Stage AI Pipeline**: CV → RAG → Rules → LLM → Assembly → Persistence
- **Image Analysis**: AWS Rekognition Custom Labels for disease detection
- **LLM Enhancement**: AWS Bedrock Nova for Ukrainian explanations
- **PostgreSQL Database**: Full diagnosis history with async operations
- **Web Interface**: Interactive Streamlit UI with multi-page navigation

---

## 🏗️ Architecture

```
User Input (Symptoms + Images)
        ↓
    Streamlit UI
        ↓
    FastAPI REST API
        ↓
┌───────────────────────────┐
│   Pipeline Orchestrator   │
│                           │
│  1. Computer Vision       │ → Pillow + AWS Rekognition
│  2. RAG Retrieval         │ → TF-IDF + Cosine Similarity
│  3. Rules Engine          │ → Growth stage filtering
│  4. LLM Ranking           │ → AWS Bedrock Nova / Stub
│  5. Response Assembly     │ → Build action plans
│  6. Persistence           │ → PostgreSQL / Filesystem
└───────────────────────────┘
        ↓
DiagnoseResponse (JSON)
        ↓
    Display Results
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- AWS Account (optional, for Bedrock/Rekognition)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/agrodiag/agrodiag.git
   cd agrodiag
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start PostgreSQL**
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the backend**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

7. **Start the UI** (in a new terminal)
   ```bash
   streamlit run ui/app.py
   ```

8. **Access the application**
   - UI: http://localhost:8501
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## API Example

### Diagnose Plant Disease

```bash
curl -X POST "http://localhost:8000/v1/diagnose" \
  -H "X-Use-Bedrock: true" \
  -H "X-Use-Rekognition: true" \
  -F 'request={"crop":"tomato","growth_stage":"fruiting","symptoms_text":"темні водянисті плями на листях"}' \
  -F 'images=@leaf.jpg'
```

**Response:**
```json
{
  "case_id": "uuid",
  "candidates": [
    {
      "disease": "Late blight (Фітофтороз)",
      "score": 0.89,
      "rationale": "Темні водянисті плями та швидке поширення після дощу є характерними ознаками фітофторозу...",
      "kb_refs": [{"id": "tomato_late_blight", "title": "Phytophthora infestans"}]
    }
  ],
  "plan": {
    "diagnostics": ["Перевірте наявність білого пухнастого нальоту..."],
    "agronomy": ["Видаліть уражені рослини", "Покращіть вентиляцію"],
    "chemical": ["Бордоська рідина", "Ридоміл Голд МЦ"],
    "bio": ["Фітоспорін-М", "Триходермін"]
  },
  "visual_features": {"late_blight": 0.94, "img0_edges_mean": 0.58},
  "debug": {"timings": {"cv": 0.15, "total": 0.45}}
}
```

---

## Project Structure

```
agro-project/
├── app/                    # Backend application
│   ├── main.py            # FastAPI entry point
│   ├── api/               # API routes & schemas
│   ├── services/          # Business logic (orchestrator, CV, RAG, LLM)
│   ├── db/                # Database models & repositories
│   ├── core/              # Configuration
│   └── data/              # Knowledge base (YAML files)
│       └── kb/            # 50+ diseases across 10 crops
├── ui/                    # Streamlit web interface
│   ├── app.py            # Main diagnosis page
│   └── pages/            # Cases history & KB browser
├── tests/                 # Unit & integration tests
├── alembic/              # Database migrations
├── docker-compose.yml    # PostgreSQL container
├── requirements.txt      # Python dependencies
└── .env                  # Configuration (not in git)
```

---

## Configuration

Key environment variables (`.env`):

```bash
# Database
USE_DATABASE=true
POSTGRES_HOST=localhost
POSTGRES_DB=agrodiag

# AWS Rekognition (optional)
AGRO_USE_REKOGNITION=true
AGRO_REKOGNITION_REGION=us-east-1
AGRO_REKOGNITION_PROJECT_ARN=arn:aws:rekognition:...
AGRO_REKOGNITION_MODEL_ARN=arn:aws:rekognition:...

# AWS Bedrock (optional)
AGRO_LLM_MODE=bedrock  # or "stub"
AGRO_BEDROCK_REGION=us-east-1
AGRO_BEDROCK_MODEL_ID=amazon.nova-micro-v1:0

# File Limits
AGRO_MAX_IMAGES=4
AGRO_MAX_IMAGE_MB=5
```

**Note:** AWS services are optional. System works in stub mode without credentials.

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_api_diagnose.py -v
```

---

## 📊 Performance

- **Average response time**: 0.4s (stub mode) / 2.5s (full AI with Bedrock + Rekognition)
- **Database query time**: ~10-15ms
- **Supported load**: 100+ concurrent requests (with proper infrastructure)

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI, Python 3.10+, async/await |
| **Frontend** | Streamlit |
| **Database** | PostgreSQL 15, SQLAlchemy (async), Alembic |
| **CV** | Pillow, AWS Rekognition Custom Labels |
| **LLM** | AWS Bedrock (amazon.nova-micro-v1:0) |
| **RAG** | TF-IDF (scikit-learn), cosine similarity |
| **Deployment** | Docker Compose, Uvicorn |
| **Testing** | pytest, pytest-asyncio |


**Version 0.1.0-beta** - December 2024
