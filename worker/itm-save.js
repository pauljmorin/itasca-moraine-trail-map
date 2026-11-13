/* itm-save — the save service for the Itasca Moraine trail map.
   One Worker, several endpoints. /classify ships first (Paul, Nov 12,
   2026); /ask (Ask the trail Q&A, Nov 13, 2026); /report, /adopt
   and /pin are stubs for later — each is one more endpoint on this
   same Worker, not another build.

   The map is a static site, so it cannot write to GitHub on its own.
   This Worker holds the GitHub login server-side (the secret
   GITHUB_TOKEN, set in the Cloudflare dashboard) and commits the
   change to the repo. The token never appears in this file, is never
   logged, and is never sent anywhere except api.github.com.

   /ask answers board questions from the map's own data only. The
   Worker fetches the checked-in digest
   (site/data/trail-digest.json, built by
   scripts/build_trail_digest.py) and sends it — and nothing else —
   to the model. When the digest cannot answer a question, the
   Worker queues it in data/ask-queue.json (same GitHub-commit
   pattern as /classify) and emails Paul, so the question reaches
   both Paul and Muse. The queue file is the product roadmap: each
   entry carries the work sizing (effort, data needed, whether the
   data already exists, whose approval is needed).

   Deploy: python3 worker/deploy.py worker/itm-save.js
   (PUTs this file as the `itm-save` Worker on the Pauljmorin@gmail.com
   Cloudflare account. The API token used for the deploy needs
   Workers Scripts:Edit.)

   Secrets (set once, in the Cloudflare dashboard — Workers & Pages →
   itm-save → Settings → Variables → Add secret):
     GITHUB_TOKEN — a fine-grained personal access token on the
       pauljmorin GitHub account, scoped to
       pauljmorin/itasca-moraine-trail-map with Contents Read and write.
     GEMINI_API_KEY — Paul's Google AI Studio API key (the same key
       the legacy-gemini connector already holds as custom.gemini).
       /ask returns a clear "not configured" message until it is set.
     RESEND_API_KEY — the Resend API key for the unanswered-question
       email to Paul. Optional: without it the queue file still
       records every question, but no email goes out.
   Env vars (plain, not secrets):
     LLM_MODEL — default "gemini-2.5-flash".
     ASK_DIGEST_URL — override for the digest URL (default: the live
       Pages copy of site/data/trail-digest.json).
*/

var REPO = "pauljmorin/itasca-moraine-trail-map";
var GEOJSON_PATH = "site/data/assets.geojson";
var QUEUE_PATH = "data/ask-queue.json";
var ALLOWED_ORIGINS = ["https://pauljmorin.github.io"];
var ASSET_TYPES = ["BN", "BO", "BR", "BW", "CP", "CS", "KI", "LT",
                   "PK", "PO", "RG", "SG", "SH", "UN", "WT"];
var CONDITIONS = ["good", "fair", "poor", "new", "worn", "replace"];
var DEFAULT_DIGEST_URL =
  "https://pauljmorin.github.io/itasca-moraine-trail-map" +
  "/site/data/trail-digest.json";
var DEFAULT_MODEL = "gemini-3.5-flash"; /* the legacy-gemini
  connector's default; gemini-2.5-flash 404s on these accounts. */
var ASK_RATE_PER_HOUR = 20;
var DIGEST_TTL_MS = 10 * 60 * 1000;
var QUEUE_FILE_URL =
  "https://github.com/pauljmorin/itasca-moraine-trail-map" +
  "/blob/main/data/ask-queue.json";

/* The model answers ONLY from the digest. The reply is JSON, so the
   Worker can validate the focus target and queue the unanswered
   ones. "answerable" is the model's own verdict — the Worker trusts
   it, because the digest is the only evidence the model was given. */
var ASK_SYSTEM_PROMPT =
  "You are 'Ask the trail', answering questions about the Itasca " +
  "Moraine chapter of the North Country Trail in Minnesota, for the " +
  "chapter board. You are given a TRAIL DIGEST: a compact summary " +
  "of the chapter map's own data. Answer ONLY from the digest. " +
  "Every factual claim in your answer must come from the digest; " +
  "cite the digest section it came from in 'sources' (e.g. " +
  "'trail.sections', 'assets.by_type', 'buildout_verified'). " +
  "Never invent mileage, prices, counts, or figures. If a number " +
  "is not in the digest, say so — do not estimate it.\n\n" +
  "Adopter display is INITIALS ONLY: report adopter initials as " +
  "given, never expand them to names, and never include phone " +
  "numbers or email addresses (none exist in the digest). Parcel " +
  "owner names are published county records and may be quoted; " +
  "taxpayer information does not exist and must never be added.\n\n" +
  "Do NOT classify or judge any photo or asset: if asked to judge " +
  "an asset's condition or classify a photo, decline briefly and " +
  "point to the chapter classification page (classify.html). " +
  "Reporting a condition value already recorded in the digest " +
  "(e.g. 'ITM-BW-001 is recorded as fair') is fine — that is " +
  "reading data, not judging it.\n\n" +
  "If the digest DOES answer the question, set answerable=true, " +
  "give the answer with sources, and set focus when the question " +
  "is about a specific section, gap, or asset: " +
  "focus={type:'section',name:'<section name>'} or " +
  "focus={type:'gap',name:'<gap id, e.g. GAP-W>'} or " +
  "focus={type:'asset',serial:'<serial>'} — only names, gap ids, " +
  "and serials that appear in the digest. Otherwise focus=null.\n\n" +
  "If the digest does NOT answer the question, set answerable=false " +
  "and write the answer in this shape, in plain language:\n" +
  "(1) Warm opening: 'That's a really good question.'\n" +
  "(2) The partial picture: what the digest DOES have on the " +
  "topic, with sources. Never a bare 'I don't know'.\n" +
  "(3) Honest sizing of the work: what kind of effort it would " +
  "take, what data would be needed, and whether the data already " +
  "exists somewhere but needs a service manager's or developer's " +
  "approval to use.\n" +
  "(4) Close with: \"I'll get this to Paul now.\"\n" +
  "Also fill: missing_data (one line: what is missing), " +
  "work_estimate (e.g. 'an afternoon's data pull', 'a new dataset " +
  "plus a build, a few days', 'a season of field counts'), " +
  "data_needed, data_exists ('yes' | 'no' | 'unknown'), " +
  "approval_needed (who must approve, or null), " +
  "suggested_next_step (the concrete next action).\n\n" +
  "Respond with JSON only, no markdown fences, exactly this shape:\n" +
  "{\"answer\": \"...\", \"sources\": [\"...\"], \"focus\": null or " +
  "{\"type\": \"section|gap|asset\", \"name\"|\"serial\": \"...\"}, " +
  "\"answerable\": true|false, \"missing_data\": \"...\"|null, " +
  "\"work_estimate\": \"...\"|null, \"data_needed\": \"...\"|null, " +
  "\"data_exists\": \"yes|no|unknown\"|null, \"approval_needed\": " +
  "\"...\"|null, \"suggested_next_step\": \"...\"|null}\n" +
  "Escape newlines as \\n inside string values; never put a " +
  "literal newline inside a quoted string.";

function originAllowed(origin) {
  if (!origin) return false;
  if (ALLOWED_ORIGINS.indexOf(origin) !== -1) return true;
  /* Local testing only. */
  return /^http:\/\/localhost(:\d+)?$/.test(origin) ||
    /^http:\/\/127\.0\.0\.1(:\d+)?$/.test(origin);
}

function corsHeaders(origin) {
  var h = { "Content-Type": "application/json", "Vary": "Origin" };
  if (originAllowed(origin)) h["Access-Control-Allow-Origin"] = origin;
  h["Access-Control-Allow-Methods"] = "POST, OPTIONS";
  h["Access-Control-Allow-Headers"] = "Content-Type";
  return h;
}

function json(status, obj, origin) {
  return new Response(JSON.stringify(obj), {
    status: status, headers: corsHeaders(origin),
  });
}

function ghHeaders(token) {
  return {
    "Authorization": "Bearer " + token,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "itm-save-worker",
  };
}

/* Read a JSON file from the repo. Returns {sha, data} or throws an
   Error with a plain message. A 404 becomes {sha: null, data: null}
   so callers can create the file. */
async function readRepoJson(token, path) {
  var res = await fetch(
    "https://api.github.com/repos/" + REPO + "/contents/" + path,
    { headers: ghHeaders(token) });
  if (res.status === 404) return { sha: null, data: null };
  if (!res.ok) {
    throw new Error("GitHub read failed (" + res.status + ")");
  }
  var body = await res.json();
  var text;
  try {
    /* GitHub returns base64 with newlines; atob ignores them. */
    text = atob(body.content.replace(/\s/g, ""));
  } catch (e) {
    throw new Error("GitHub returned unreadable content");
  }
  var data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    throw new Error(path + " is not valid JSON");
  }
  return { sha: body.sha, data: data };
}

/* Write a JSON object back. Pretty-printed with a 1-space indent
   and a trailing newline, matching the repo's files, so a commit is
   a small diff. */
async function writeRepoJson(token, path, sha, data, message) {
  var text = JSON.stringify(data, null, 1) + "\n";
  var bytes = new TextEncoder().encode(text);
  var bin = "";
  for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  var body = {
    message: message,
    content: btoa(bin),
    branch: "main",
  };
  if (sha) body.sha = sha;
  var res = await fetch(
    "https://api.github.com/repos/" + REPO + "/contents/" + path,
    {
      method: "PUT",
      headers: Object.assign(ghHeaders(token),
        { "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
  if (!res.ok) {
    var detail = "";
    try { detail = (await res.json()).message || ""; } catch (e) {}
    throw new Error("GitHub write failed (" + res.status + ")" +
      (detail ? ": " + detail : ""));
  }
  return await res.json();
}

/* POST /classify — {serial, type, condition, photographer, note}.
   Only the fields present in the body are changed; the rest of the
   pin is untouched. */
async function handleClassify(body, env, origin) {
  if (!body || typeof body !== "object") {
    return json(400, { ok: false, error: "Expected a JSON body." }, origin);
  }
  var serial = body.serial;
  if (!serial || typeof serial !== "string") {
    return json(400, { ok: false, error: "serial is required." }, origin);
  }
  if (body.type !== undefined && body.type !== null &&
      ASSET_TYPES.indexOf(String(body.type).toUpperCase()) === -1) {
    return json(400, { ok: false,
      error: "type must be one of " + ASSET_TYPES.join(", ") + "." }, origin);
  }
  if (body.condition !== undefined && body.condition !== null &&
      body.condition !== "" &&
      CONDITIONS.indexOf(String(body.condition)) === -1) {
    return json(400, { ok: false, error: "condition must be one of " +
      CONDITIONS.join(", ") + "." }, origin);
  }
  if (!env.GITHUB_TOKEN) {
    return json(500, { ok: false,
      error: "GITHUB_TOKEN not configured on the Worker." }, origin);
  }
  var read;
  try {
    read = await readRepoJson(env.GITHUB_TOKEN, GEOJSON_PATH);
  } catch (e) {
    return json(500, { ok: false, error: e.message }, origin);
  }
  var feature = null;
  var feats = (read.data || {}).features || [];
  for (var i = 0; i < feats.length; i++) {
    if ((feats[i].properties || {}).serial === serial) {
      feature = feats[i];
      break;
    }
  }
  if (!feature) {
    return json(404, { ok: false,
      error: "No pin with serial " + serial + "." }, origin);
  }
  var p = feature.properties;
  if (body.type !== undefined && body.type !== null && body.type !== "") {
    p.type = String(body.type).toUpperCase();
  }
  if (body.condition !== undefined && body.condition !== null) {
    p.condition = body.condition === "" ? null : String(body.condition);
  }
  if (body.photographer !== undefined && body.photographer !== null) {
    p.photographer = String(body.photographer);
  }
  if (body.note !== undefined && body.note !== null) {
    p.note = String(body.note);
  }
  var typeLabel = p.type || "UN";
  var condLabel = p.condition || "ungraded";
  var message = "Classify " + serial + " as " + typeLabel + ", " +
    condLabel + " (via map)";
  var committed;
  try {
    committed = await writeRepoJson(env.GITHUB_TOKEN, GEOJSON_PATH,
      read.sha, read.data, message);
  } catch (e) {
    return json(500, { ok: false, error: e.message }, origin);
  }
  return json(200, { ok: true, serial: serial,
    commit: (committed.commit || {}).sha || null }, origin);
}

/* ------------------------------------------------------- Ask the trail */

/* Per-IP rate limit, in-memory (per isolate): 20 questions/hour.
   This is abuse control for the paid model key, not a user-facing
   quota — a board meeting asks a handful of questions. */
var askRate = new Map();
function askRateOk(ip) {
  var now = Date.now();
  var hits = askRate.get(ip) || [];
  hits = hits.filter(function (t) { return now - t < 3600 * 1000; });
  if (hits.length >= ASK_RATE_PER_HOUR) return false;
  hits.push(now);
  askRate.set(ip, hits);
  return true;
}

/* The digest is fetched from the live site and cached in memory for
   10 minutes, so a burst of questions does not re-fetch it. */
var digestCache = { text: null, at: 0 };
async function fetchDigest(env) {
  var now = Date.now();
  if (digestCache.text && now - digestCache.at < DIGEST_TTL_MS) {
    return digestCache.text;
  }
  var url = env.ASK_DIGEST_URL || DEFAULT_DIGEST_URL;
  var res = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!res.ok) {
    throw new Error("Trail digest unavailable (" + res.status + ")");
  }
  var text = await res.text();
  JSON.parse(text); /* fail fast if the digest is not valid JSON */
  digestCache = { text: text, at: now };
  return text;
}

function stripFences(text) {
  return String(text).replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```\s*$/, "");
}

/* Parse the model's JSON, repairing the common failure of literal
   newlines inside quoted strings (the model sometimes emits them
   despite the prompt). Returns the parsed object or throws. */
function parseModelJson(rawText) {
  try {
    return JSON.parse(stripFences(rawText));
  } catch (e) {}
  var out = "";
  var inStr = false;
  var esc = false;
  var text = stripFences(rawText);
  for (var i = 0; i < text.length; i++) {
    var ch = text[i];
    if (inStr) {
      if (esc) { out += ch; esc = false; }
      else if (ch === "\\") { out += ch; esc = true; }
      else if (ch === '"') { out += ch; inStr = false; }
      else if (ch === "\n") { out += "\\n"; }
      else if (ch === "\r") { out += "\\r"; }
      else if (ch === "\t") { out += "\\t"; }
      else { out += ch; }
    } else {
      out += ch;
      if (ch === '"') inStr = true;
    }
  }
  return JSON.parse(out);
}

/* A focus target is only honoured if it names something in the
   digest — a hallucinated section or serial must never move the
   map. */
function validFocus(focus, digest) {
  if (!focus || typeof focus !== "object") return null;
  var sections = {};
  (digest.trail.sections || []).forEach(function (s) {
    sections[s.name] = true;
  });
  var gaps = {};
  (digest.trail.gaps || []).forEach(function (g) { gaps[g.gap_id] = true; });
  var serials = {};
  (digest.assets.list || []).forEach(function (a) {
    if (a.serial) serials[a.serial] = true;
  });
  if (focus.type === "section" && sections[focus.name]) {
    return { type: "section", name: focus.name };
  }
  if (focus.type === "gap" && gaps[focus.name]) {
    return { type: "gap", name: focus.name };
  }
  if (focus.type === "asset" && serials[focus.serial]) {
    return { type: "asset", serial: focus.serial };
  }
  return null;
}

function normalizeQuestion(q) {
  return String(q).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

/* Append an unanswered question to data/ask-queue.json. A repeat of
   an already-open question bumps asked_count instead of duplicating
   the entry. Retries once on a GitHub sha conflict. Returns the
   entry id, or null if the queue write failed (the asker still gets
   the answer — the queue is best-effort, never a blocker). */
async function queueUnanswered(token, modelOut, question) {
  var now = new Date().toISOString();
  var norm = normalizeQuestion(question);
  for (var attempt = 0; attempt < 2; attempt++) {
    var read;
    try {
      read = await readRepoJson(token, QUEUE_PATH);
    } catch (e) {
      return null;
    }
    var queue = read.data;
    if (!queue || !Array.isArray(queue.entries)) {
      queue = { version: 1, entries: [] };
    }
    var entries = queue.entries;
    var existing = null;
    for (var i = 0; i < entries.length; i++) {
      if (entries[i].status === "open" &&
          normalizeQuestion(entries[i].question) === norm) {
        existing = entries[i];
        break;
      }
    }
    var id;
    if (existing) {
      existing.asked_count = (existing.asked_count || 1) + 1;
      existing.last_asked_at = now;
      id = existing.id;
    } else {
      var maxN = 0;
      entries.forEach(function (e) {
        var m = /^AQ-(\d+)$/.exec(e.id || "");
        if (m) maxN = Math.max(maxN, parseInt(m[1], 10));
      });
      id = "AQ-" + String(maxN + 1).padStart(4, "0");
      entries.push({
        id: id,
        asked_at: now,
        last_asked_at: now,
        asked_count: 1,
        status: "open",
        question: question,
        missing_data: modelOut.missing_data || null,
        partial_answer: modelOut.answer || null,
        work_estimate: modelOut.work_estimate || null,
        data_needed: modelOut.data_needed || null,
        data_exists: modelOut.data_exists || null,
        approval_needed: modelOut.approval_needed || null,
        suggested_next_step: modelOut.suggested_next_step || null,
        sources: modelOut.sources || [],
        resolved_note: null,
      });
    }
    try {
      await writeRepoJson(token, QUEUE_PATH, read.sha, queue,
        "Ask the trail: queue unanswered question " + id);
      return id;
    } catch (e) {
      if (attempt === 0 && /409|sha/i.test(e.message)) continue;
      return null;
    }
  }
  return null;
}

/* Email Paul the unanswered question. Plain text, no emojis, full
   content in the body — the established alert channel (Resend to
   pauljmorin@gmail.com). Returns true when Resend accepted it. */
async function emailUnanswered(key, entry) {
  var short_q = entry.question.length > 60
    ? entry.question.slice(0, 60) + "..." : entry.question;
  var lines = [
    "A board question came in that the trail map could not answer:",
    "",
    "Question: " + entry.question,
    "Asked: " + entry.asked_at,
    "Queue entry: " + entry.id + " (" + QUEUE_FILE_URL + ")",
    "",
    "What was missing: " + (entry.missing_data || "not stated"),
    "",
    "What the map did answer (partial picture):",
    entry.partial_answer || "(none)",
    "",
    "Work sizing:",
    "- Effort: " + (entry.work_estimate || "not estimated"),
    "- Data needed: " + (entry.data_needed || "not stated"),
    "- Data already exists: " + (entry.data_exists || "unknown"),
    "- Approval needed from: " + (entry.approval_needed || "none stated"),
    "",
    "Suggested next step: " + (entry.suggested_next_step || "none stated"),
    "",
    "To mark this done, edit data/ask-queue.json on GitHub: set "
      + "status to \"done\" and add a resolved_note.",
  ];
  var res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + key,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "Muse <onboarding@resend.dev>",
      to: ["pauljmorin@gmail.com"],
      subject: "Trail question the map couldn't answer: " + short_q,
      text: lines.join("\n"),
    }),
    signal: AbortSignal.timeout(15000),
  });
  return res.ok;
}

/* POST /ask — {question}. Returns {ok, answer, sources, focus,
   unanswered, queued, queue_id, email_sent}. */
async function handleAsk(body, env, origin, ip) {
  if (!body || typeof body !== "object" ||
      typeof body.question !== "string" ||
      body.question.trim().length === 0) {
    return json(400, { ok: false,
      error: "question is required." }, origin);
  }
  var question = body.question.trim().slice(0, 500);
  if (!askRateOk(ip)) {
    return json(429, { ok: false, error: "Too many questions — " +
      "please wait a little and try again." }, origin);
  }
  if (!env.GEMINI_API_KEY) {
    return json(503, { ok: false, error: "ask_not_configured",
      message: "Ask the trail isn't set up yet — the chapter needs "
        + "to add the GEMINI_API_KEY secret in the Cloudflare "
        + "dashboard (Workers & Pages → itm-save → Settings → "
        + "Variables)." }, origin);
  }
  var digestText;
  try {
    digestText = await fetchDigest(env);
  } catch (e) {
    return json(502, { ok: false, error: e.message }, origin);
  }
  var digest;
  try {
    digest = JSON.parse(digestText);
  } catch (e) {
    return json(502, { ok: false,
      error: "Trail digest is not valid JSON." }, origin);
  }
  var model = env.LLM_MODEL || DEFAULT_MODEL;
  var genRes;
  try {
    genRes = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" +
      encodeURIComponent(model) + ":generateContent?key=" +
      encodeURIComponent(env.GEMINI_API_KEY),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          system_instruction: { parts: [{ text: ASK_SYSTEM_PROMPT }] },
          contents: [{ role: "user", parts: [{ text:
            "TRAIL DIGEST:\n" + digestText +
            "\n\nQUESTION:\n" + question }] }],
          generationConfig: {
            temperature: 0.2,
            /* 4000, not 1200: the longer unanswered replies (warm
               opening + partial picture + work sizing) were clipped
               mid-sentence at 1200 in testing (Nov 13, 2026). */
            maxOutputTokens: 4000,
            responseMimeType: "application/json",
          },
        }),
        signal: AbortSignal.timeout(30000),
      });
  } catch (e) {
    return json(502, { ok: false,
      error: "Model call failed: " + e.message }, origin);
  }
  if (!genRes.ok) {
    return json(502, { ok: false,
      error: "Model call failed (" + genRes.status + ")." }, origin);
  }
  var genBody;
  try {
    genBody = await genRes.json();
  } catch (e) {
    return json(502, { ok: false,
      error: "Model returned unreadable output." }, origin);
  }
  var rawText = "";
  try {
    rawText = genBody.candidates[0].content.parts
      .map(function (p) { return p.text || ""; }).join("");
  } catch (e) {}
  var modelOut;
  try {
    modelOut = parseModelJson(rawText);
  } catch (e) {
    return json(502, { ok: false,
      error: "Model did not return a usable answer." }, origin);
  }
  if (!modelOut || typeof modelOut.answer !== "string") {
    return json(502, { ok: false,
      error: "Model did not return a usable answer." }, origin);
  }
  var focus = validFocus(modelOut.focus, digest);
  var out = {
    ok: true,
    answer: modelOut.answer,
    sources: Array.isArray(modelOut.sources) ? modelOut.sources : [],
    focus: focus,
    unanswered: modelOut.answerable === false,
    queued: false,
    queue_id: null,
    email_sent: false,
  };
  if (modelOut.answerable === false) {
    /* Route to BOTH Paul and Muse: the durable queue file in the
       repo is the coordinator's source (the weekly watch reads it),
       and Paul gets the email. Neither is a fallback for the other.
       A queue/email failure never blocks the asker's answer. */
    var queueId = null;
    if (env.GITHUB_TOKEN) {
      queueId = await queueUnanswered(env.GITHUB_TOKEN, modelOut,
        question);
    }
    var emailSent = false;
    if (queueId && env.RESEND_API_KEY) {
      try {
        emailSent = await emailUnanswered(env.RESEND_API_KEY, {
          id: queueId,
          question: question,
          asked_at: new Date().toISOString(),
          missing_data: modelOut.missing_data,
          partial_answer: modelOut.answer,
          work_estimate: modelOut.work_estimate,
          data_needed: modelOut.data_needed,
          data_exists: modelOut.data_exists,
          approval_needed: modelOut.approval_needed,
          suggested_next_step: modelOut.suggested_next_step,
        });
      } catch (e) {
        emailSent = false;
      }
    }
    out.queued = !!queueId;
    out.queue_id = queueId;
    out.email_sent = emailSent;
  }
  return json(200, out, origin);
}

function notImplemented(name, origin) {
  return json(501, { ok: false,
    error: name + " is not implemented yet." }, origin);
}

export default {
  async fetch(request, env) {
    var origin = request.headers.get("Origin") || "";
    var ip = request.headers.get("CF-Connecting-IP") || "unknown";
    var url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    if (request.method !== "POST") {
      return json(405, { ok: false, error: "POST only." }, origin);
    }
    var body = null;
    try {
      body = await request.json();
    } catch (e) {
      return json(400, { ok: false, error: "Body is not valid JSON." },
        origin);
    }
    if (url.pathname === "/classify") {
      return handleClassify(body, env, origin);
    }
    if (url.pathname === "/ask") {
      return handleAsk(body, env, origin, ip);
    }
    /* Stubs (Paul, Nov 12): same Worker, same GitHub login, one more
       endpoint each when the chapter is ready for them. */
    if (url.pathname === "/report") return notImplemented("report", origin);
    if (url.pathname === "/adopt") return notImplemented("adopt", origin);
    if (url.pathname === "/pin") return notImplemented("pin", origin);
    return json(404, { ok: false, error: "Unknown endpoint." }, origin);
  },
};
