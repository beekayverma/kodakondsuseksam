# kodakondsuseksam

Free, open-source study tool for the Estonian citizenship exam (Eesti
Vabariigi põhiseaduse ja kodakondsuse seaduse tundmise eksam).

Built for people moving from any language background into Estonian
citizenship: starts with English hints alongside the Estonian source
question, and grows to Russian, Ukrainian, Hindi, and more as
community translators contribute.

This project is not affiliated with Harno, Innove, the Integration
Foundation (INSA), or any Estonian state body. It is a community
study aid maintained by volunteers. The Constitution of the Republic
of Estonia (PS) and the Citizenship Act (KodS) are the only
authoritative sources; this project always cites the relevant
section so users can verify against the original text.

## Why this exists

The state-funded "50 Questions to Estonian Citizenship" tool (INSA,
2023) covers 50 questions in Estonian and Russian. The real exam
draws from a larger pool, and many candidates would benefit from
hints in their own native language while they are still learning
Estonian. This project closes that gap:

- larger question bank (target 200+ over time, vs. INSA's 50)
- progressive Web App, installable on a phone, works offline
- multi-language hint layer (English, Russian, Ukrainian, Hindi
  planned), with the question text always in Estonian because that
  is the language of the real exam
- spaced-repetition resurfacing for questions the user got wrong
- two-level structure: Õpi (Learn) with hints, then Eksam (Mock)
  pure Estonian, 24 questions, 45 minutes, pass at 18 correct
- optional AI Tutor that explains wrong answers with citations to
  the actual Constitution and Citizenship Act text

## Status

Pre-MVP. See [ROADMAP.md](ROADMAP.md) for what is in v1 versus later.
Seed question bank: 66 questions ported from a personal exam-prep
tool used by the maintainer in May 2026. All seed questions cite a
PS or KodS section.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
# open http://127.0.0.1:8765
```

## Contributing questions

Every contribution helps a real person take a real exam. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for the question schema, the
review process, and the legal/native-speaker quality gate. Single
golden rule: every question must cite a statute section
(`PS §X` for Constitution, `KodS §Y` for Citizenship Act). No
citation, no merge.

## Licenses

- Code: MIT (see [LICENSE](LICENSE))
- Question content: CC BY-SA 4.0 (see [LICENSE-CONTENT](LICENSE-CONTENT))

The split exists so other community projects, language schools, and
NGOs can re-use the question bank under attribution + share-alike
without inheriting the code license.

## Related

- Plan and architecture: [PLAN.md](PLAN.md)
- Roadmap and phased rollout: [ROADMAP.md](ROADMAP.md)
- How to add or translate a question: [CONTRIBUTING.md](CONTRIBUTING.md)
- Official exam information: [harno.ee/en/citizenship-examinations](https://harno.ee/en/citizenship-examinations)
- Official 18-hour training: [integratsioon.ee](https://www.integratsioon.ee/en/training-courses-constitution-and-citizenship-act)
