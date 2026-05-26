# Contributing

Every question added or translated here helps a real person take a
real exam. Quality bar is high, the process is light.

## What we accept

1. New Estonian questions with at least one statute citation
2. Hint translations into a supported language
3. Bug fixes, accessibility improvements, performance fixes
4. Reviewer time (legal/native review of pending PRs)

We do not accept questions without a statute citation, questions
copied verbatim from another study tool without permission and
re-attribution, or commentary on Estonian politics, citizenship
policy, or any party. Stay on the law and the exam.

## Question schema (v0)

```json
{
  "id": "d1",
  "section": "I",
  "question_et": "Kes on Eesti Vabariigis kõrgeima riigivõimu kandja?",
  "question_en": "Who holds the highest state power in the Republic of Estonia?",
  "options": ["Vabariigi President", "Rahvas", "Riigikogu", "Peaminister"],
  "answer_idx": 1,
  "ref": "PS §1"
}
```

Field rules:

- `id` is a short stable slug, unique across the bank
- `section` is the Constitution chapter or `KodS` for Citizenship Act
- `question_et` is the canonical question in Estonian (always required)
- `question_en` is the English translation hint (required at v0; later
  versions add `hints: { en, ru, uk, hi, ... }`)
- `options` is a list of 2 to 4 plausible answers in Estonian
- `answer_idx` is the zero-based index of the correct option
- `ref` is the statute citation, format `PS §N` or `KodS §N`. Multiple
  refs are joined with a comma, e.g. `PS §59, PS §65`. This is the
  non-negotiable quality gate.

## PR flow

1. Fork the repo
2. Add or edit `questions.json` (v0) or `questions/<id>.json` (v1+)
3. Open a pull request with a one-line description: what you added
   or changed, and why
4. AI Question Validator (when wired in v2) auto-comments with a
   first-pass review
5. A native reviewer for the affected language signs off
6. Maintainer merges; site rebuilds within minutes

## Reviewer roles

- Estonian native + basic legal literacy: reviews question_et,
  answer correctness, statute citation
- Per-language native: reviews hint translations
- Maintainer (initially the repo owner): merges after both reviews

Start: the maintainer plus one volunteer lawyer in Estonia is enough.
Reviewers are listed on the about page once we have one.

## Acknowledgement

Contributors are listed on the project site (anonymized handle by
default; real name only if you ask). Top contributors are noted in
the monthly digest email.

## Code of conduct

Be kind. The audience for this tool includes people who have spent
years working toward Estonian citizenship and may be studying in
their second, third, or fourth language. Reviewer comments should
help, not lecture. We have a one-strike rule on hostility.
