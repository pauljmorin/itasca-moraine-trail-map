# itm-save — the map's save service

A Cloudflare Worker that lets the static trail map write back to
GitHub. The map cannot hold a GitHub login, so this Worker holds it
server-side (as a secret) and commits the change to the repo.

- Worker name: `itm-save`
- URL: `https://itm-save.<account-subdomain>.workers.dev`
  (confirm the exact subdomain after the first deploy)
- Repo: `pauljmorin/itasca-moraine-trail-map`, branch `main`
- Data file: `site/data/assets.geojson`

## Endpoints (all POST, JSON in, JSON out)

- `/classify` — live. Body `{serial, type, condition, photographer,
  note}`. Updates that pin's properties in `site/data/assets.geojson`
  (only the fields present in the body) and commits with the message
  `Classify <serial> as <type>, <condition> (via map)`. Returns
  `{ok:true, serial, commit:<sha>}`. 400 on bad input, 404 when the
  serial is not found, 500 when the secret is missing or GitHub
  rejects the call.
- `/ask` — live (Nov 13, 2026). Body `{question}` (max 500 chars).
  Answers ONLY from the checked-in digest
  (`site/data/trail-digest.json`, built by
  `scripts/build_trail_digest.py`; the Worker fetches the live Pages
  copy and caches it 10 minutes). Returns `{ok:true, answer,
  sources, focus, unanswered, queued, queue_id, email_sent}` where
  `focus` is `{type:"section"|"gap", name}` or
  `{type:"asset", serial}` — validated against the digest, so a
  hallucinated target never moves the map. When the digest cannot
  answer, the reply is warm + partial + work-sized (effort, data
  needed, whether the data exists, whose approval is needed), and
  the question is queued in `data/ask-queue.json` (one commit; a
  repeat of an open question bumps `asked_count`) and emailed to
  Paul. 503 with `error:"ask_not_configured"` until GEMINI_API_KEY
  is set; 429 past 20 questions/hour per IP. The queue file is also
  the coordinator's source — the weekly watch reads it — and Paul
  marks an entry done by editing the file (status `"done"` +
  `resolved_note`).
- `/report`, `/adopt`, `/pin` — stubs returning 501. Same Worker, same
  login, one more endpoint each when the chapter is ready for them:
  trail reports, adopter updates, new-pin submissions.

## Secrets (set once, by Paul, in the Cloudflare dashboard)

Workers & Pages → `itm-save` → Settings → Variables → Add secret,
named `GITHUB_TOKEN`. The value is a fine-grained personal access
token on the `pauljmorin` GitHub account, scoped to
`pauljmorin/itasca-moraine-trail-map` with Contents Read and write
(the token Paul created Nov 12, 2026). The Worker returns a clear
"GITHUB_TOKEN not configured" error until the secret is set. The
secret is never in this repo and never in a log.

`GEMINI_API_KEY` — Paul's Google AI Studio API key (the same key
the legacy-gemini connector already holds as `custom.gemini`).
`/ask` returns 503 `ask_not_configured` until it is set. Model
default `gemini-3.5-flash` (the connector's default — 2.5-flash
404s on these accounts), overridable with the plain env var
`LLM_MODEL`. Expected cost is a fraction of a cent per question
(digest ~5,000 input tokens, answer ~300 output tokens, Flash-class
pricing); the paid Tier 1 balance on the `custom.gemini` account
covers thousands of questions.

`RESEND_API_KEY` — the Resend API key for the unanswered-question
email to Paul (plain text, from `Muse <onboarding@resend.dev>`,
the established alert sender). Optional: without it the queue file
still records every unanswered question, but no email goes out.

## Deploy

```text
python3 worker/deploy.py worker/itm-save.js
```

This PUTs the script as the `itm-save` Worker on the
Pauljmorin@gmail.com Cloudflare account. The API token used for the
deploy needs Workers Scripts:Edit (the Cloudflare token as stored
Nov 12, 2026 has Pages Edit only — add Workers Scripts:Edit to it in
the Cloudflare dashboard under My Profile → API Tokens, or the
deploy returns 403). After the first deploy, fill in the exact
workers.dev URL here and in the `ITM_SAVE_URL` constant in
`site/app.js`.
