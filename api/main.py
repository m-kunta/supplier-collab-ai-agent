from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

# Load .env before importing the agent stack (LLM provider env vars).
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from api.deps import resolve_data_dir
from api.schemas import BriefingCreate
from api.store import BriefingStore
from src.agent import summarize_request
from src.data_loader import load_manifest

app = FastAPI(
    title="Supplier Collab AI API",
    version="0.1.0",
    description="REST API for pre-meeting supplier briefing generation.",
)

briefing_store = BriefingStore()

_cors_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe for orchestration and local dev."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_briefing_response(briefing_id: str, created_at: str, summary: dict[str, Any]) -> dict[str, Any]:
    """API envelope: ``id`` + ``created_at`` plus the CLI-shaped summary payload."""
    return {"id": briefing_id, "created_at": created_at, **summary}


def _get_record_or_404(briefing_id: str) -> dict[str, Any]:
    rec = briefing_store.get(briefing_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Briefing '{briefing_id}' not found.")
    return rec


# ---------------------------------------------------------------------------
# Briefings CRUD
# ---------------------------------------------------------------------------


@app.post("/api/briefings")
async def create_briefing(body: BriefingCreate) -> dict[str, Any]:
    """Run the full briefing pipeline, store the result, and return it with an ``id``.

    The synchronous ``summarize_request`` call is dispatched to a thread-pool executor
    so the event loop is not blocked during the (potentially 20–60 s) LLM call.

    Response shape: ``id``, ``created_at``, then the same keys as :func:`summarize_request`
    (``status``, ``message``, ``request``, engine outputs, ``briefing_text``, ``output_files``, …).
    """
    data_dir = resolve_data_dir(body.data_dir)
    loop = asyncio.get_running_loop()
    try:
        summary = await loop.run_in_executor(
            None,
            lambda: summarize_request(
                vendor=body.vendor,
                meeting_date=body.meeting_date,
                data_dir=data_dir,
                lookback_weeks=body.lookback_weeks,
                persona_emphasis=body.persona_emphasis,
                include_benchmarks=body.include_benchmarks,
                output_format=body.output_format,
                category_filter=body.category_filter,
                llm_provider=body.llm_provider,
                llm_model=body.llm_model,
            ),
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    briefing_id, created_at = briefing_store.save(summary)
    return _merge_briefing_response(briefing_id, created_at, summary)


@app.get("/api/briefings")
def list_briefings(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """List recent briefings (newest first) for history views."""
    rows = briefing_store.list_briefs(limit=limit)
    return {"briefings": rows, "total": briefing_store.count()}


@app.get("/api/briefings/{briefing_id}/stream")
async def stream_briefing(briefing_id: str) -> StreamingResponse:
    """Re-stream a stored briefing's ``briefing_text`` as Server-Sent Events.

    Each SSE event carries a JSON payload: ``{"type": "token", "content": "<chunk>"}``
    followed by a final ``{"type": "done"}`` sentinel.  The Next.js UI can consume
    this with the standard ``EventSource`` API for a live-typewriter effect.

    Note: this replays already-generated text (Phase 5).  True token-level streaming
    from the LLM during generation is deferred to Phase 6.
    """
    rec = _get_record_or_404(briefing_id)
    briefing_text: str = rec["summary"].get("briefing_text") or ""

    async def _sse_generator():
        chunk_size = 25
        for i in range(0, max(len(briefing_text), 1), chunk_size):
            chunk = briefing_text[i : i + chunk_size]
            if chunk:
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.015)
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/briefings/{briefing_id}/download")
def download_briefing(briefing_id: str) -> FileResponse:
    """Serve the generated briefing document as a file attachment.

    Prefers ``md_path``; falls back to ``docx_path`` if present.  Returns 410 Gone
    when the record exists in the store but the file is no longer on disk (e.g. after
    a server restart wiped the in-memory store while the ``output/`` directory was
    cleaned separately — or vice-versa).
    """
    rec = _get_record_or_404(briefing_id)
    output_files: dict[str, str] = rec["summary"].get("output_files") or {}
    if not output_files:
        raise HTTPException(status_code=404, detail="No output files recorded for this briefing.")

    path_str = output_files.get("md_path") or output_files.get("docx_path")
    if not path_str:
        raise HTTPException(status_code=404, detail="No downloadable output file found.")

    file_path = Path(path_str)
    if not file_path.exists():
        raise HTTPException(
            status_code=410,
            detail=(
                f"File '{file_path.name}' is no longer on disk. "
                "The in-memory store resets on server restart — re-generate the briefing to download again."
            ),
        )

    media_type = "text/markdown" if file_path.suffix == ".md" else "application/octet-stream"
    filename = file_path.name
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/briefings/{briefing_id}")
def get_briefing(briefing_id: str) -> dict[str, Any]:
    """Fetch a stored briefing by id (same response shape as POST)."""
    rec = _get_record_or_404(briefing_id)
    return _merge_briefing_response(rec["id"], rec["created_at"], rec["summary"])


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------


@app.get("/api/vendors")
def list_vendors(
    data_dir: str = Query(default="data/inbound/mock", description="Landing zone path (relative to repo root or absolute).")
) -> dict[str, Any]:
    """Return the vendor list from a landing zone's ``vendor_master.csv``.

    Useful for populating the vendor selector in the Next.js UI without
    requiring a full briefing run.
    """
    resolved = resolve_data_dir(data_dir)

    try:
        manifest = load_manifest(resolved)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No manifest found at '{resolved}'.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    files = manifest.get("files", {})
    vm_info = files.get("vendor_master")
    if not vm_info:
        raise HTTPException(status_code=404, detail="vendor_master not declared in manifest.")

    vm_path = resolved / vm_info["filename"]
    try:
        df = pd.read_csv(vm_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read vendor_master: {exc}") from exc

    return {
        "vendors": df.to_dict(orient="records"),
        "total": len(df),
        "data_dir": str(resolved),
    }
