## AI-Powered Medical Report Simplifier

A FastAPI service that extracts, normalizes, guardrails, and summarizes medical lab reports from images or raw text using Tesseract OCR and Google Gemini.

### Key Features
- **OCR extraction**: Read text from uploaded images via Tesseract.
- **LLM parsing**: Extract raw test strings from report text.
- **Normalization**: Convert to structured JSON with values, units, status, reference ranges.
- **Guardrails**: Detect hallucinated/unsupported tests with exact + fuzzy matching.
- **Summarization**: Patient-friendly summary and explanations without medical advice.

---

## Setup

### Prerequisites
- Python 3.10+
- Tesseract OCR installed and on PATH
  - Windows: Install from `https://github.com/UB-Mannheim/tesseract/wiki` and ensure `tesseract.exe` is in PATH
  - macOS: `brew install tesseract`
  - Linux (Debian/Ubuntu): `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- Google Generative AI API key (Gemini)

### 1) Clone and enter project
```bash
git clone <your-fork-or-path>
cd "plum_project_final - Copy"
```

### 2) Create virtual environment and install dependencies
```bash
python -m venv .venv
".venv/Scripts/activate"  # Windows PowerShell
# Or: source .venv/bin/activate  # macOS/Linux

pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Configure environment
Create a `.env` file in the project root with:
```bash
GOOGLE_API_KEY=your_google_gemini_api_key
```
The app loads this via `app/core/config.py` using `pydantic-settings`.

### 4) Run the server
```bash
uvicorn app.main:app --reload --port 8000
```

Visit docs: `http://localhost:8000/docs` and `http://localhost:8000/redoc`.

---

## Architecture

### Overview
- `app/main.py`: FastAPI app initialization and root route.
- `app/api/v1/report_router.py`: All API endpoints for extraction, normalization, guardrails, and summarization.
- `app/services/ocr_service.py`: Tesseract-based OCR (`perform_ocr`).
- `app/services/ai_service.py`: Gemini integration and pipeline steps:
  - `extract_raw_tests_from_text(text)`
  - `normalize_tests(raw_tests)`
  - `run_guardrail_check(raw_tests, normalized_tests)`
  - `generate_patient_summary(normalized_tests)`
- `app/schemas/report_schemas.py`: Pydantic request models.
- `app/core/config.py`: Settings loader for `.env` (`GOOGLE_API_KEY`).

### Data/State Handling
- Stateless HTTP API; no database.
- Inputs are either image bytes or text JSON.
- OCR output → LLM extraction → LLM normalization → Guardrail check → LLM summary.
- Guardrail allows small count mismatch (±2) and uses fuzzy matching (fuzzywuzzy) to reduce hallucinations.

---

## API Endpoints (Base: `http://localhost:8000/api/v1`)

### Health/Root
- `GET /` → `{ "message": "Welcome to the Medical Report Simplifier API!" }`

### 1) Extraction
- `POST /extract_from_image` (multipart/form-data): file: image
- `POST /extract_from_text` (application/json): `{ "text": "..." }`

Response (example):
```json
{
  "tests_raw": ["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"],
  "confidence": 0.93
}
```

### 2) Normalization
- `POST /normalize`
Request body (example):
```json
{
  "tests_raw": ["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"]
}
```
Response (example):
```json
{
  "tests": [
    {
      "name": "Hemoglobin",
      "value": 10.2,
      "unit": "g/dL",
      "status": "low",
      "ref_range": { "low": 12.0, "high": 15.5 }
    }
  ],
  "normalization_confidence": 0.9
}
```

### 3) Summarization (with Guardrail)
- `POST /summarize`
Request body (example):
```json
{
  "tests_raw": ["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"],
  "tests": [
    {"name": "Hemoglobin", "value": 10.2, "unit": "g/dL", "status": "low"},
    {"name": "WBC", "value": 11200, "unit": "/uL", "status": "high"}
  ]
}
```
Guardrail failure returns HTTP 422 with reason.
Response (example on success):
```json
{
  "summary": "Your hemoglobin is low and white blood cells are high.",
  "explanations": [
    "Low hemoglobin can indicate anemia or blood loss.",
    "High white blood cells may reflect infection or inflammation."
  ]
}
```

### 4) Full Pipeline
- `POST /process_report_from_image` (multipart/form-data): file: image
- `POST /process_report_from_text` (application/json): `{ "text": "..." }`

Response (example):
```json
{
  "tests": [ { "name": "Hemoglobin", "value": 10.2, "unit": "g/dL", "status": "low" } ],
  "summary": "Your hemoglobin is low.",
  "status": "ok"
}
```

---

## Sample cURL Requests

### Extract from text
```bash
curl -X POST "http://localhost:8000/api/v1/extract_from_text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hemoglobin 10.2 g/dL (Low)\nWBC 11200 /uL (High)"}'
```

### Extract from image
```bash
curl -X POST "http://localhost:8000/api/v1/extract_from_image" \
  -H "Accept: application/json" \
  -F "file=@/path/to/report.jpg"
```

### Normalize
```bash
curl -X POST "http://localhost:8000/api/v1/normalize" \
  -H "Content-Type: application/json" \
  -d '{"tests_raw": ["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"]}'
```

### Summarize
```bash
curl -X POST "http://localhost:8000/api/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{
        "tests_raw": ["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"],
        "tests": [
          {"name":"Hemoglobin","value":10.2,"unit":"g/dL","status":"low"},
          {"name":"WBC","value":11200,"unit":"/uL","status":"high"}
        ]
      }'
```

### Full pipeline from text
```bash
curl -X POST "http://localhost:8000/api/v1/process_report_from_text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hemoglobin 10.2 g/dL (Low)\nWBC 11200 /uL (High)"}'
```

---

## Postman
- Create a new collection pointing at `http://localhost:8000/api/v1`.
- Add requests matching the cURL examples above.
- For image endpoints, set Body → form-data, key `file` type "File".

---

## Prompts Used (Summarized)

- **Extraction (`extract_raw_tests_from_text`)**
  - Role: medical data extraction assistant
  - Tasks: identify lines containing test, value, unit, status; correct OCR typos
  - Output: `{ "tests_raw": string[], "confidence": number }`

- **Normalization (`normalize_tests`)**
  - Role: medical data normalization expert
  - Tasks: map to `{ name, value, unit, status, ref_range }`
  - Rule: use standard adult reference ranges; ignore ranges from input
  - Output: `{ "tests": Test[], "normalization_confidence": number }`

- **Summary (`generate_patient_summary`)**
  - Rule: no diagnosis/medical advice
  - Output: JSON with `summary` and array `explanations` (strings only)

Refinements made:
- Added explicit JSON-only outputs and code to strip markdown fences.
- Introduced guardrail with exact+fuzzy matching and count tolerance.

---

## Screenshots (optional)
Place screenshots (e.g., Swagger UI, Postman) in a `docs/` folder and link them here.

---



---

## Development

### Linting/Formatting
Use your preferred linters/formatters. Ensure imports and types are clean.

### Running tests
If/when tests are added, run via `pytest`.

---




