from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from app.services import ocr_service, ai_service
from app.schemas.report_schemas import RawTestsInput, SummarizeInput, TextInput

# --- API Router Initialization ---
router = APIRouter()


# --- Step 1: Extract test data from image ---
@router.post("/extract_from_image", summary="Step 1: Extract test data from an image")
async def extract_from_image(file: UploadFile = File(...)):
    """
    Takes a medical report image, performs OCR, and extracts raw test strings.
    """
    file_content = await file.read()
    original_text = ocr_service.perform_ocr(file_content)

    if not original_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the image.")

    extracted_data = ai_service.extract_raw_tests_from_text(original_text)
    return extracted_data


# --- Step 1 (Alt): Extract test data from text ---
@router.post("/extract_from_text", summary="Step 1: Extract test data from text")
async def extract_from_text(data: TextInput):
    """
    Takes raw text from a medical report and extracts test strings.
    """
    original_text = data.text
    if not original_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    extracted_data = ai_service.extract_raw_tests_from_text(original_text)
    return extracted_data


# --- Step 2: Normalize raw test data ---
@router.post("/normalize", summary="Step 2: Normalize raw test data")
async def normalize_extracted_tests(data: RawTestsInput):
    return ai_service.normalize_tests(data.tests_raw)


# --- Step 3: Summarization (with Guardrail) ---
@router.post("/summarize", summary="Step 3: Generate a patient-friendly summary")
async def summarize_normalized_tests(data: SummarizeInput):
    """
    Takes the normalized JSON and the raw tests, runs a guardrail check,
    and then generates a patient-friendly summary.
    """
    if not ai_service.run_guardrail_check(data.tests_raw, data.tests):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "unprocessed",
                "reason": "Guardrail failed: hallucinated tests not present in input"
            }
        )

    return ai_service.generate_patient_summary(data.tests)



# --- Helper for full pipeline ---
async def run_pipeline(original_text: str):
    """
    Contains the core logic for the AI pipeline:
    OCR/Text → Raw extraction → Normalization → Guardrail → Summary
    """
    extracted_data = ai_service.extract_raw_tests_from_text(original_text)
    raw_tests_list = extracted_data.get("tests_raw", [])

    normalized_data = ai_service.normalize_tests(raw_tests_list)
    normalized_tests_list = normalized_data.get("tests", [])

    if not ai_service.run_guardrail_check(raw_tests_list, normalized_tests_list):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "unprocessed",
                "reason": "Guardrail failed: detected hallucinated tests not present in input"
            }
        )

    summary_data = ai_service.generate_patient_summary(normalized_tests_list)

    return {
        "tests": normalized_tests_list,
        "summary": summary_data.get("summary"),
        "status": "ok"
    }


# --- Step 4: Full pipeline from image ---
@router.post("/process_report_from_image", summary="Step 4: Run full pipeline from an image")
async def process_report_from_image(file: UploadFile = File(...)):
    """
    Takes an image, performs OCR, and runs the full processing pipeline.
    """
    file_content = await file.read()
    original_text = ocr_service.perform_ocr(file_content)

    if not original_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the image.")

    return await run_pipeline(original_text)


# --- Step 4: Full pipeline from text ---
@router.post("/process_report_from_text", summary="Step 4: Run full pipeline from text")
async def process_report_from_text(data: TextInput):
    """
    Takes a text string and runs the full processing pipeline.
    """
    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    return await run_pipeline(data.text)
