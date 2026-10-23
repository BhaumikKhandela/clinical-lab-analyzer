import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.agent import analyze_labs
from app.pdf_extract import extract_report, extract_text
from app.schemas import AnalyzeLabsRequest, AnalyzeLabsResponse
from app.observability import request_trace, observation, capture_content

logger = logging.getLogger("agent")

router = APIRouter(tags=["labs"])

# Matches the 10 MB cap the patient service puts on uploads.
MAX_PDF_BYTES = 10 * 1024 * 1024


@router.post("/analyze_labs", response_model=AnalyzeLabsResponse)
async def analyze_labs_endpoint(payload: AnalyzeLabsRequest, request: Request) -> Dict[str, Any]:
    with request_trace("analyze-labs", uuid.uuid4().hex, input=payload.labs) as root:
        result = await analyze_labs(request.app.state.mcp_client, payload.labs)
        _complete_trace(root, result, len(payload.labs))
        return result


@router.post("/analyze_report", response_model=AnalyzeLabsResponse)
async def analyze_report_endpoint(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    with request_trace("analyze-report", uuid.uuid4().hex) as root:
        result = await _analyze_report(request, file)
        _complete_trace(root, result)
        return result


def _complete_trace(root, result, rows=None):
    root.update(metadata={**result.get("summary", {}), "rows_rejected": len(result.get("errors", [])),
                          "rows_submitted": rows},
                output=result if capture_content() else {"summary": result.get("summary", {})})


async def _analyze_report(request: Request, file: UploadFile) -> Dict[str, Any]:
    """Accept a PDF report, extract its rows with the LLM, then analyse them.

    The extraction is validated against ExtractedReport before analysis, so a
    bad model reply fails as a 422 here rather than producing wrong results.
    """
    is_pdf = file.content_type == "application/pdf" or (file.filename or "").lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(status_code=415, detail="Only PDF reports are accepted.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="That PDF is larger than the 10 MB limit.")

    # pypdf and call_llm are both blocking; off the event loop they go, or they
    # would stall every other request for the duration of the extraction.
    try:
        with observation("read-pdf"):
            text = await run_in_threadpool(extract_text, data)
        with observation("extract-lab-rows", input=text) as extraction:
            report = await run_in_threadpool(extract_report, text)
            extraction.update(metadata={"rows_extracted": len(report.labs)})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info("PDF '%s' yielded %d row(s) for analysis", file.filename, len(report.labs))
    return await analyze_labs(request.app.state.mcp_client, report.to_lab_rows())
