"""FastAPI app for kodakondsuseksam. Two levels (Õpi, Eksam) plus a
Personal Tutor stub that proxies to a RAG endpoint."""
from __future__ import annotations

import json
import os
import random
import re
import secrets
from pathlib import Path

import httpx
import markdown as md_lib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = ROOT / "questions.json"
TEMPLATES_DIR = ROOT / "app" / "templates"
STATIC_DIR = ROOT / "app" / "static"
CORPUS_DIR = ROOT / "corpus"

# Level 0 (Lugemine) catalog: reference documents the real exam candidate
# is entitled to consult. Order matches the recommended pedagogical flow
# shown to the user: start with the Harno briefing (format, rules), then
# read the two statutes (Constitution + Citizenship Act), and finally
# browse the official question bank to see what gets asked. Files live in
# corpus/ and are also mirrored into the hp-lab Obsidian vault so the
# same content powers the Personal Tutor RAG. Source URLs cite Riigi
# Teataja or Harno verbatim.
LUGEMINE_DOCS: list[dict] = [
    {
        "slug": "harno-booklet",
        "file": "harno-booklet.md",
        "title": "Harno juhend eksamile kandideerijatele",
        "title_en": "Harno guide for examinees",
        "source": "https://harno.ee/sites/default/files/documents/2021-02/Kodakondsuse_eksam_ENG.pdf",
        "blurb": (
            "Alusta siit. Ametlik Harno juhend: eksami formaat, hindamine, "
            "lubatud abivahendid eksamiruumis. (Start here. Official Harno "
            "briefing: format, grading, what you can bring into the exam "
            "room.)"
        ),
    },
    {
        "slug": "pohiseadus",
        "file": "pohiseadus.md",
        "title": "Eesti Vabariigi põhiseadus",
        "title_en": "Constitution of the Republic of Estonia",
        "source": "https://www.riigiteataja.ee/akt/115052015002",
        "blurb": (
            "Põhiseaduse terviktekst. Eksamil küsitakse I, II ja III peatüki "
            "sisu kohta. (Constitution full text. The exam covers Chapters "
            "I, II and III.)"
        ),
    },
    {
        "slug": "kodakondsuse-seadus",
        "file": "kodakondsuse-seadus.md",
        "title": "Kodakondsuse seadus (KodS)",
        "title_en": "Citizenship Act",
        "source": "https://www.riigiteataja.ee/akt/710566",
        "blurb": (
            "Kodakondsuse omandamise, saamise, taastamise ja kaotamise "
            "tingimused ning kord. (Acquisition, granting, restoration, "
            "and loss of Estonian citizenship.)"
        ),
    },
    {
        "slug": "kusimustepank",
        "file": "riigi-teataja-akt-31893-kusimustepank.md",
        "title": "Ametlik küsimustepank (RT akt 31893)",
        "title_en": "Official question bank (RT act 31893)",
        "source": "https://www.riigiteataja.ee/akt/31893",
        "blurb": (
            "103 ametlikku eksamiküsimust nelja jaotuse kaupa. "
            "Päris eksamil genereeritakse iga vooru 24 küsimust just sellest "
            "pangast. (103 official exam questions across four sections.)"
        ),
    },
]
LUGEMINE_BY_SLUG: dict[str, dict] = {d["slug"]: d for d in LUGEMINE_DOCS}

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


@app.get("/lugemine", response_class=HTMLResponse)
async def lugemine_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "lugemine_index.html",
        {"request": request, "docs": LUGEMINE_DOCS},
    )


@app.get("/lugemine/{slug}", response_class=HTMLResponse)
async def lugemine_doc(request: Request, slug: str) -> HTMLResponse:
    doc = LUGEMINE_BY_SLUG.get(slug)
    if doc is None:
        raise HTTPException(404, "unknown reference document")
    path = CORPUS_DIR / doc["file"]
    if not path.exists():
        raise HTTPException(500, f"corpus file missing: {doc['file']}")
    raw = path.read_text(encoding="utf-8")
    # markdown for the .md files, plain <pre> for the .txt (Harno booklet
    # comes from pdftotext and the line wrapping shouldn't be reflowed).
    if doc["file"].endswith(".md"):
        html_body = md_lib.markdown(
            raw, extensions=["toc", "tables", "fenced_code", "attr_list"]
        )
    else:
        from html import escape as html_escape
        html_body = f"<pre class=\"plain-text\">{html_escape(raw)}</pre>"
    return templates.TemplateResponse(
        "lugemine_doc.html",
        {
            "request": request,
            "doc": doc,
            "html_body": html_body,
            "all_docs": LUGEMINE_DOCS,
        },
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


_CHUNK_REF_RE = re.compile(r"\s*\[chunk:\s*\d+(?:\s*[,\s]\s*\d+)*\]\s*")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")


def _clean_rag_answer(text: str) -> str:
    """Strip the RAG response's debug scaffolding before showing it to the
    end user: the leading 'Q: ...' prompt echo, the trailing 'Retrieved
    chunks:' citation block, AND any inline '[chunk:N]' / '[chunk:N,M]'
    references the model sprinkles into the answer body (per-sentence
    citations that read awkwardly when surfaced as user-facing prose).
    Idempotent on already-clean responses."""
    if not text:
        return text
    s = text.strip()
    if s.startswith("Q:"):
        parts = s.split("\n\n", 1)
        if len(parts) == 2:
            s = parts[1]
    for marker in ("\n---\nRetrieved chunks:", "\n\nRetrieved chunks:", "\nRetrieved chunks:"):
        idx = s.find(marker)
        if idx >= 0:
            s = s[:idx]
            break
    # Drop inline "[chunk:N]" or "[chunk:N,M,K]" references. Capture
    # surrounding whitespace so removal does not leave double spaces or a
    # space before punctuation.
    s = _CHUNK_REF_RE.sub(" ", s)
    s = _MULTISPACE_RE.sub(" ", s)
    # Tidy " ," " ." etc that may appear after the substitution.
    for bad, good in ((" ,", ","), (" .", "."), (" ;", ";"), (" :", ":"), (" )", ")"), ("( ", "(")):
        s = s.replace(bad, good)
    return s.strip()


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
        answer = _clean_rag_answer(data.get("answer") or data.get("response") or "")
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
