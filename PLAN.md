# Plan

## Audience

People applying for Estonian citizenship who must pass the
constitutional and citizenship-law exam (24 questions in Estonian,
pass at 18 correct, administered ~8 times per year by Harno/Innove).

Specifically the segment of applicants whose Estonian is not yet
strong enough to study comfortably with Estonian-only materials.
Today their main free tool is the INSA 50-question game, in Estonian
and Russian only.

## What we add over INSA's 50 Questions

1. Bigger question bank (target 200+ over time)
2. Installable PWA, offline-capable
3. Hint layer in more languages (EN first, then RU, UA, HI, FI, DE...)
4. Spaced-repetition resurfacing
5. Three-level structure (Lugemine / Õpi / Eksam): Level 0 is a
   browsable copy of the three official reference documents that
   candidates are entitled to use in the real exam room (Constitution,
   Citizenship Act, Innove "6 Steps" booklet), with deep-linking from
   every question's statute reference. Level 1 is study-with-hints.
   Level 2 is the real-exam mock.
6. AI Tutor that explains wrong answers grounded in the actual
   Constitution and Citizenship Act text via RAG

## Non-goals

- Replacing the official 18-hour INSA training course
- Issuing certificates or claiming authority on the exam content
- Becoming a paid product (this stays donation-funded forever)
- Hosting user PII beyond what the user opts into for cross-device
  sync (anonymous by default; localStorage only)

## Architecture

```
                   browser (PWA)
                       |
                       v
                   FastAPI
            ___________|_________________
           |           |                 |
           v           v                 v
       questions/   /api/tutor      static assets
       (JSON, in     (RAG client)
        repo)            |
                         v
                   hp-lab RAG endpoint
                   (pgvector + Ollama mistral)
                         |
                         v
              Constitution text + KodS text
              indexed once, queried per turn
```

- Frontend: PWA, single page, no framework dependency for v1; Vue or
  Svelte may follow if interaction complexity grows
- Backend: FastAPI, async, served by uvicorn; everything else is JSON
  files in the repo
- AI Tutor: thin HTTP client to the existing hp-lab RAG service. No
  third-party API calls in the free tier. Donor tier may upgrade to
  Anthropic API for higher-quality narration; not in v1.
- State: per-user state lives in IndexedDB in the browser; no
  server-side accounts in v1. v2 may add an optional magic-link
  account for cross-device sync.

## Why these stack choices

- **FastAPI** over Flask: async needed for the RAG call, plus auto API
  docs for contributors. Small enough to stay readable.
- **Static questions** over a database: questions live in git, every
  change is a PR, history is the audit log. Contributors do not need
  to know SQL.
- **Reference documents bundled** (Constitution, Citizenship Act,
  Innove "6 Steps" booklet): Estonian state acts published in Riigi
  Teataja are public; the Innove booklet is published openly. All
  three ship in the repo as canonical Markdown so Level 0 works
  fully offline and the same corpus also powers the RAG store.
  When the Riigikogu amends the law, a quarterly diff job flags the
  change for re-import.
- **Local Ollama** over OpenAI/Anthropic: zero per-request cost is
  the only way a non-profit tool can offer AI tutoring at scale. Quality
  is "good enough" with mistral 7B for this task because RAG over the
  actual law text does the heavy lifting; the model only narrates.
- **MIT code, CC BY-SA content**: lets language schools and NGOs
  re-use the question bank with attribution while keeping the code
  permissive for forks.

## Hosting

- Primary: existing home Pi k3s cluster, namespace `kodakondsuseksam`,
  same pattern as `lets-play` (see [[reference_letsplayagame_deploy]])
- Edge: Cloudflare orange-cloud DNS to bahikash-hel Caddy if traffic
  outgrows the Pi; otherwise direct cloudflared tunnel
- Domains: `citizenship.ee` primary, others (kodanikuks, saakodanik,
  kodakondsuseksam, 18st24) all 301 to primary
- Cost: <€40/yr (domain renewals only; compute is existing infra)

## Risks and mitigations

- **Wrong answer in the bank harms a real candidate.** Mitigation:
  every question must cite a PS or KodS section; native + legal
  review before merge; quarterly law-change diff to catch updates.
- **INSA upgrades their tool.** Mitigation: this is community-led and
  open-source; state can match features but not match contribution
  velocity. Even better, partner with INSA when there is something
  to show.
- **AI Tutor hallucinates.** Mitigation: RAG-only context, no
  fall-back to vanilla LLM knowledge; cite the retrieved chunk in
  every answer; show a "draft, may be wrong" disclaimer on the AI
  panel; allow users to flag bad tutor answers for review.
- **Spam PRs.** Mitigation: AI validator does first-pass; human
  reviewer is the actual gate.
