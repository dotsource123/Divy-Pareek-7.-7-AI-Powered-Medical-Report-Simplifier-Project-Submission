from pydantic import BaseModel, Field
from typing import List, Dict, Any


# --- Pydantic Models for structured inputs ---

class RawTestsInput(BaseModel):
    tests_raw: List[str] = Field(
        ..., 
        example=["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"]
    )


# Updated: use raw_tests instead of original_text
class SummarizeInput(BaseModel):
    tests_raw: List[str] = Field(
        ..., 
        example=["Hemoglobin 10.2 g/dL (Low)", "WBC 11200 /uL (High)"]
    )
    tests: List[Dict[str, Any]] = Field(
        ..., 
        example=[
            {"name": "Hemoglobin", "value": 10.2, "unit": "g/dL", "status": "low"}
        ]
    )


# --- Optional plain text input ---
class TextInput(BaseModel):
    text: str
