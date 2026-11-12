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
- `/report`, `/adopt`, `/pin` — stubs returning 501. Same Worker, same
  login, one more endpoint each when the chapter is ready for them:
  trail reports, adopter updates, new-pin submissions.

## Secret (set once, by Paul, in the Cloudflare dashboard)

Workers & Pages → `itm-save` → Settings → Variables → Add secret,
named `GITHUB_TOKEN`. The value is a fine-grained personal access
token on the `pauljmorin` GitHub account, scoped to
`pauljmorin/itasca-moraine-trail-map` with Contents Read and write
(the token Paul created Nov 12, 2026). The Worker returns a clear
"GITHUB_TOKEN not configured" error until the secret is set. The
secret is never in this repo and never in a log.

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
