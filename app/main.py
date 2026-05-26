"""FastAPI app for kodakondsuseksam. Two levels (Õpi, Eksam) plus a
Personal Tutor stub that proxies to a RAG endpoint."""
from __future__ import annotations

import json
import os
import random
import secrets
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = ROOT / "questions.json"
TEMPLATES_DIR = ROOT / "app" / "templates"
STATIC_DIR = ROOT / "app" / "static"

# RAG endpoint config: defaults to the existing hp-lab RAG service
# documented in [[reference_hp_lab_rag_endpoint]]. Override via env in
# environments where the Constitution corpus lives elsewhere.
RAG_URL = os.environ.get("RAG_URL", "http://hp-lab:8080/answer")
RAG_TIMEOUT_SECONDS = float(os.environ.get("RAG_TIMEOUT", "20"))
MOCK_QUESTIONS_PER_ROUND = 24
MOCK_PASS_THRESHOLD = 18

QUESTIONS: list[dict] = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
QUESTIONS_BY_ID: dict[str, dict] = {q["id"]: q for q in QUESTIONS}

# Static-file cache buster: appended as ?v=... to static URLs in templates
# so any edit to style.css / app.js automatically invalidates the SW cache
# without requiring a manual DevTools wipe. mtime of the largest asset
# dominates so we don't need to track each file individually.
def _compute_static_version() -> str:
    try:
        files = [STATIC_DIR / "style.css", STATIC_DIR / "app.js", STATIC_DIR / "sw.js"]
        mtimes = [int(f.stat().st_mtime) for f in files if f.exists()]
        return str(max(mtimes)) if mtimes else "0"
    except OSError:
        return "0"

STATIC_VERSION = _compute_static_version()

# Server-held mock sessions keyed by an opaque token. Per-process only,
# resets on restart; fine for a single-Pi deployment. v2 moves this to
# IndexedDB on the client when we add the no-server mock path.
SESSIONS: dict[str, list[dict]] = {}

app = FastAPI(title="kodakondsuseksam", docs_url="/api/docs", redoc_url=None)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "question_count": len(QUESTIONS)},
    )


@app.get("/opi", response_class=HTMLResponse)
async def learn(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "learn.html",
        {"request": request, "questions": QUESTIONS},
    )


@app.get("/eksam", response_class=HTMLResponse)
async def exam(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "exam.html",
        {"request": request, "pass_threshold": MOCK_PASS_THRESHOLD},
    )


@app.post("/api/mock/start")
async def mock_start() -> dict:
    if len(QUESTIONS) < MOCK_QUESTIONS_PER_ROUND:
        raise HTTPException(500, "question bank smaller than a single round")
    picked = random.sample(QUESTIONS, MOCK_QUESTIONS_PER_ROUND)
    token = secrets.token_urlsafe(16)
    # Per-round option-order shuffle: prevents the user from memorising
    # "the correct answer is always option B." answer_idx is remapped to
    # the position the correct option landed at after the shuffle, then
    # stored server-side so grading uses the shuffled order. Without
    # this, every replay leaks an unintended shortcut.
    served: list[dict] = []
    stored: list[dict] = []
    for q in picked:
        correct_option = q["options"][q["answer_idx"]]
        shuffled_options = list(q["options"])
        random.shuffle(shuffled_options)
        new_answer_idx = shuffled_options.index(correct_option)
        served.append(
            {
                "id": q["id"],
                "section": q["section"],
                "question_et": q["question_et"],
                "question_en": q.get("question_en", ""),
                "options": shuffled_options,
                "ref": q.get("ref", ""),
            }
        )
        stored.append({**q, "options": shuffled_options, "answer_idx": new_answer_idx})
    SESSIONS[token] = stored
    return {
        "token": token,
        "questions": served,
        "pass_threshold": MOCK_PASS_THRESHOLD,
    }


class MockSubmission(BaseModel):
    token: str
    answers: dict[str, int] = Field(default_factory=dict)


@app.post("/api/mock/grade")
async def mock_grade(payload: MockSubmission) -> dict:
    picked = SESSIONS.pop(payload.token, None)
    if picked is None:
        raise HTTPException(404, "unknown or already-graded session token")
    results = []
    correct = 0
    for q in picked:
        chosen = payload.answers.get(q["id"], -1)
        is_correct = chosen == q["answer_idx"]
        if is_correct:
            correct += 1
        results.append(
            {
                "id": q["id"],
                "question_et": q["question_et"],
                "question_en": q.get("question_en", ""),
                "options": q["options"],
                "chosen": chosen,
                "correct": q["answer_idx"],
                "is_correct": is_correct,
                "ref": q.get("ref", ""),
            }
        )
    return {
        "correct": correct,
        "total": len(picked),
        "passed": correct >= MOCK_PASS_THRESHOLD,
        "pass_threshold": MOCK_PASS_THRESHOLD,
        "results": results,
    }


class TutorRequest(BaseModel):
    question_id: str
    chosen_idx: int = Field(..., ge=-1, le=10)
    hint_lang: str = Field(default="en", min_length=2, max_length=5)


@app.post("/api/tutor")
async def tutor(payload: TutorRequest) -> JSONResponse:
    q = QUESTIONS_BY_ID.get(payload.question_id)
    if q is None:
        raise HTTPException(404, "unknown question id")
    correct_text = q["options"][q["answer_idx"]]
    chosen_text = (
        q["options"][payload.chosen_idx]
        if 0 <= payload.chosen_idx < len(q["options"])
        else "(no answer)"
    )
    prompt = (
        f"In the language '{payload.hint_lang}', explain in 2 short paragraphs "
        f"why the correct answer to this Estonian citizenship exam question is "
        f"'{correct_text}' and why '{chosen_text}' is wrong. Cite the exact "
        f"article from the Constitution of Estonia (PS) or the Citizenship "
        f"Act (KodS). Question (Estonian): {q['question_et']}. "
        f"Statute reference for context: {q.get('ref', 'unknown')}."
    )
    try:
        async with httpx.AsyncClient(timeout=RAG_TIMEOUT_SECONDS) as client:
            resp = await client.post(RAG_URL, json={"question": prompt})
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer") or data.get("response") or ""
        if not answer.strip():
            raise ValueError("empty answer from RAG")
        return JSONResponse(
            {
                "source": "rag",
                "answer": answer,
                "ref": q.get("ref", ""),
                "correct_text": correct_text,
            }
        )
    except Exception:
        # Fallback when the RAG is unreachable or the Constitution
        # corpus is not yet ingested. Ships in v0 so the UI is wired
        # end-to-end; the live answer arrives once the corpus lands
        # in pgvector. See ROADMAP v1.
        return JSONResponse(
            {
                "source": "fallback",
                "answer": (
                    f"The correct answer is '{correct_text}'. Read the cited "
                    f"section {q.get('ref', '(unknown)')} in the Constitution "
                    f"or Citizenship Act for the full reasoning. The AI tutor "
                    f"is being prepared; for now please verify against the "
                    f"statute text directly."
                ),
                "ref": q.get("ref", ""),
                "correct_text": correct_text,
            }
        )


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "questions": len(QUESTIONS)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8765")),
        reload=False,
    )
