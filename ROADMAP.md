# Roadmap

## v0 (now, 2026-05-27 night session)

- Repo scaffolding, docs, license split, .gitignore
- Seed question bank (66 Q ported from personal study tool)
- Minimal FastAPI app exposing the existing Level 2 (Eksam) mock
- Personal Tutor endpoint stub (calls hp-lab RAG, graceful fallback
  message when the Constitution is not yet ingested)
- Initial commit and push to github.com/beekayverma/kodakondsuseksam

## v1 (target: end of June 2026, MVP)

Ship a complete usable tool for English-speaking citizenship candidates.

- Level 1 (Õpi / Learn) page with toggle to show English hint,
  statute reference, plain-language explanation
- Level 2 (Eksam / Mock) preserved from v0, polished
- Personal Tutor wired to a populated RAG store (Constitution +
  Citizenship Act ingested into hp-lab pgvector)
- PWA manifest + service worker for offline play
- Spaced repetition: missed questions resurface at 1d, 3d, 7d, 14d,
  30d intervals, all client-side
- Score history chart (last 30 mock attempts)
- Topic filter: drill by Chapter (I, II, III) or by KodS section
- Production deploy to `citizenship.ee`

## v2 (target: end of August 2026)

Multi-language hint rollout, community contribution flow.

- Hint layer: add Russian (largest non-Estonian-speaker group)
- Hint layer: add Ukrainian
- AI Translation Assistant: when a new question lands in Estonian,
  AI drafts hints in all enabled languages; native reviewer approves
  via a tiny web UI
- Optional account: email + magic link, for cross-device progress
  sync only; no other PII
- Contributor flow: GitHub PR template + AI Question Validator that
  comments on every PR with a pass/fail and suggested fixes

## v3 (target: end of 2026)

Indian-diaspora languages and quality-of-life features.

- Hint layer: add Hindi
- Hint layer: add Gujarati, Punjabi, Tamil for regional Indian speakers
- Exam-day countdown and reminders
- Share-progress cards for social SEO
- Conversational "Ask the Constitution" mode using the same RAG
  store (free-form Q&A over the law text)

## v4 (long tail)

- Finnish hints (large Finnish minority in Estonia)
- German, Spanish for diaspora long tail
- Native iOS and Android wrappers (Capacitor) once PWA limitations
  prove costly
- Partnership with INSA or Harno for official endorsement
- Per-Chapter "lecture" mode: short curated reading from the
  Constitution itself with a 5-Q quiz at the end

## Out of scope (forever)

- Paid tiers, paywalls, or any monetization beyond optional donations
- Tracking, third-party analytics, or behavioral fingerprinting
- AI-generated questions that go live without human review
- Claiming any official status with respect to the exam itself
