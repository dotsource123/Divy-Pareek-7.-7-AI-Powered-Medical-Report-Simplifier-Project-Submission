import json
import google.generativeai as genai
from fastapi import HTTPException
from app.core.config import settings
from fuzzywuzzy import process
import re

# --- Model Configuration ---
try:
    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    raise RuntimeError(f"Failed to configure Google AI: {e}")


# --- Step 1: Extract Raw Tests ---
def extract_raw_tests_from_text(text: str) -> dict:
    """Uses Gemini to extract and correct raw test strings from text."""
    prompt = f"""
    You are a highly accurate medical data extraction assistant. Analyze the provided text from a medical lab report.
    Your Tasks:
    1. [cite_start]Identify and pull out every line that contains a medical test, its value, unit, and status. [cite: 8]
    2. [cite_start]Correct obvious OCR typos in test names (e.g., 'Hemglobin' becomes 'Hemoglobin', 'Hgh' becomes 'High'). [cite: 5, 8]
    Output Format:
    Return a JSON object with two keys: "tests_raw" (a list of corrected strings) and "confidence" (a float from 0.0 to 1.0).
    Report Text: --- {text} ---
    """
    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {e}")


# --- Step 2: Normalize Tests ---
def normalize_tests(raw_tests: list) -> dict:
    """Uses Gemini to convert raw strings into structured, normalized JSON."""
    prompt = f"""
    You are a medical data normalization expert. Convert the following list of raw test strings into a structured JSON array.
    For each string, create a JSON object with these keys: "name", "value" (numeric), "unit", "status" ("low", "high", or "normal"), and "ref_range" (an object with "low" and "high" values).

    **Important rule: For every test, you MUST provide a standard reference range based on common medical knowledge for an adult. IGNORE any reference ranges that may be present in the input strings and use your own standard values instead.**

    Input: {json.dumps(raw_tests)}
    Output Format:
    Return a JSON object with two keys: "tests" (the array of structured test objects) and "normalization_confidence" (your confidence score as a float).
    """
    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI normalization failed: {e}")


# --- Step 3: Guardrail Check (Improved) ---
def run_guardrail_check(raw_tests: list, normalized_tests: list) -> bool:
    """
    Ensures the normalized tests correspond to tests found in the raw extraction (no hallucinations).
    Uses exact match first, then fuzzy matching for small OCR or name differences.
    """

    # Allow a small mismatch in count (±2) to handle merging/splitting
    if abs(len(raw_tests) - len(normalized_tests)) > 2:
        return False

    # Extract probable test names from raw strings
    raw_test_names = []
    for s in raw_tests:
        match = re.match(r'^[\w\s\-\(\)\/]+', s)
        if match:
            raw_test_names.append(match.group(0).strip().lower())

    if not raw_test_names:
        return False

    for test in normalized_tests:
        normalized_name = test.get("name", "").strip().lower()
        if not normalized_name:
            return False

        # --- Step 1: Try exact match ---
        if normalized_name in raw_test_names:
            continue

        # --- Step 2: Try fuzzy match ---
        best_match, score = process.extractOne(normalized_name, raw_test_names)
        if score < 80:
            # Optional: log for debugging
            print(f"[Guardrail Fail] '{normalized_name}' → best match '{best_match}' (score: {score})")
            return False

    return True


# --- Step 4: Generate Patient Summary ---
def generate_patient_summary(normalized_tests: list) -> dict:
    """Uses Gemini to generate a patient-friendly summary."""
    prompt = f"""
    You are a helpful medical assistant. **Do not provide a diagnosis or medical advice.**
    Based on the provided JSON of lab results, generate a simple summary and one-sentence explanations for any results marked "low" or "high".

    **Output ONLY a valid JSON object with two keys:**
    **1. "summary": A single string summarizing the main findings.**
    **2. "explanations": A JSON array containing ONLY simple strings. Each string should be a one-sentence explanation for an abnormal test. Do not use objects or key-value pairs within this array.**

    Input: {json.dumps(normalized_tests)}
    """
    try:
        # Call Gemini model
        response = model.generate_content(prompt)

        # Clean up AI response and parse JSON
        json_str = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_str)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"AI summary generation failed. Raw AI output: {response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI summary generation failed: {e}"
        )