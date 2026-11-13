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
   data already exists, whose approval is needed) plus the design
   criteria the asker gave when the Worker asked follow-up
   questions. /transcribe (speech-to-text) and /speak (text-to-
   speech) serve the panel's voice-conversation mode; both use the
   same GEMINI_API_KEY, so voice needs no extra secret.

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
       The same key also serves /transcribe and /speak.
     RESEND_API_KEY — the Resend API key for the unanswered-question
       email to Paul. Optional: without it the queue file still
       records every question, but no email goes out.
   Env vars (plain, not secrets):
     LLM_MODEL — default "gemini-3.5-flash" (gemini-2.5-flash
       returns 404 on these accounts).
     TTS_MODEL — default "gemini-3.8-flash-tts" (the 2.5 preview
       TTS models retire Nov 17, 2026).
     TTS_VOICE — default "Sulafat" (Google's label: Warm — the
       closest prebuilt voice in tone to a warm, friendly
       assistant; no provider offers Muse's own voice).
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
var DEFAULT_TTS_MODEL = "gemini-3.8-flash-tts"; /* GA replacement
  for the 2.5 preview TTS models, which retire Nov 17, 2026. */
var DEFAULT_TTS_VOICE = "Sulafat"; /* Google's label: Warm. */
var ASK_RATE_PER_HOUR = 60; /* shared by /ask, /transcribe and
  /speak: one spoken turn is three calls (transcribe + ask +
  speak), so the old 20/hour would throttle a short voice
  conversation. Still abuse control for the paid key, not a
  user-facing quota — a board meeting asks a handful of
  questions. */
var DIGEST_TTL_MS = 10 * 60 * 1000;
var QUEUE_FILE_URL =
  "https://github.com/pauljmorin/itasca-moraine-trail-map" +
  "/blob/main/data/ask-queue.json";

/* The model answers ONLY from the digest. The reply is JSON, so the
   Worker can validate the focus target and queue the unanswered
   ones. "answerable" is the model's own verdict — the Worker trusts
   it, because the digest is the only evidence the model was given.
   Identity: the assistant IS the Itasca Moraine trail assistant,
   and says so. Scope: the North Country Trail and the Itasca
   Moraine chapter only — anything else gets a brief redirect and
   is never queued, because it is not a data gap. An in-scope
   question the digest cannot answer starts a short elicitation:
   the model asks ONE clarifying question at a time (at most three
   rounds) about what the asker actually needs — what "good" would
   look like, which area or section, what form the answer should
   take — and the criteria gathered go into the queue entry, so
   Paul and Muse get an actionable to-do, not just a question. */
var ASK_SYSTEM_PROMPT =
  "You are the Itasca Moraine trail assistant, answering questions " +
  "about the North Country Trail and the Itasca Moraine chapter in " +
  "Minnesota, for the chapter board. Introduce yourself as the " +
  "Itasca Moraine trail assistant when asked who you are. You are " +
  "given a TRAIL DIGEST: a compact summary of the chapter map's " +
  "own data. Answer ONLY from the digest. Every factual claim in " +
  "your answer must come from the digest; cite the digest section " +
  "it came from in 'sources' (e.g. 'trail.sections', " +
  "'assets.by_type', 'buildout_verified'). Never invent mileage, " +
  "prices, counts, or figures. If a number is not in the digest, " +
  "say so — do not estimate it.\n\n" +
  "SCOPE: you answer ONLY about the North Country Trail and the " +
  "Itasca Moraine chapter — the trail, the chapter's sections and " +
  "assets, the gaps and build-out, volunteers, land and ownership, " +
  "and the chapter's work. If a question is NOT about the North " +
  "Country Trail or the Itasca Moraine chapter, set scope=\"out\" " +
  "and answer with exactly this, nothing more: \"I only answer " +
  "questions about the North Country Trail and the Itasca Moraine " +
  "chapter.\" Do not answer it, do not guess at it, and do not " +
  "treat it as a data gap. A question about the trail in general " +
  "(the whole North Country Trail, other chapters, the national " +
  "trail) is IN scope. A question about another trail, another " +
  "place, the weather, or anything else is OUT of scope.\n\n" +
  "FIELD INSTRUCTIONS: the digest carries a 'field_protocol' " +
  "section — the chapter's volunteer data-collection protocol. " +
  "Questions about how to do the field work are IN scope and are " +
  "answered from that section, in plain step-by-step language: " +
  "how to photograph a trail feature (regular Camera app; front, " +
  "back if anything is on it, close-up of text, numbers, or " +
  "damage), how to run Geo Tracker (start recording BEFORE " +
  "walking, keep it running, export the GPX), how to upload " +
  "(originals + GPX to your own initials subfolder in the " +
  "chapter's photos-inbox, never by text, chat, or share button), " +
  "and what happens next (the chapter classifies it and it gets a " +
  "serial number). Cite 'field_protocol' in 'sources'. If a " +
  "volunteer asks something the protocol does NOT cover, treat it " +
  "as an unanswerable question: give the partial answer from what " +
  "the protocol DOES say, size the work, and let elicitation " +
  "gather what they would want — it goes to Paul and Muse through " +
  "the queue like any other unanswerable question. Never invent " +
  "protocol steps that are not in the digest.\n\n" +
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
  "CONVERSATION: a CONVERSATION SO FAR block may precede the " +
  "question. Use it to resolve follow-ups ('how many miles is " +
  "that?', 'which section did you mean?') — 'that' refers to the " +
  "previous answer. Keep answers short enough to speak aloud.\n\n" +
  "If the digest DOES answer the question, set scope=\"in\", " +
  "answerable=true, elicit=false, elicitation_done=false, give " +
  "the answer with sources, and set focus when the question is " +
  "about a specific section, gap, or asset: " +
  "focus={type:'section',name:'<section name>'} or " +
  "focus={type:'gap',name:'<gap id, e.g. GAP-W>'} or " +
  "focus={type:'asset',serial:'<serial>'} — only names, gap ids, " +
  "and serials that appear in the digest. Otherwise focus=null.\n\n" +
  "If the digest does NOT answer an IN-SCOPE question, set " +
  "scope=\"in\", answerable=false and write the answer in this " +
  "shape, in plain language:\n" +
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
  "ELICITATION — before closing an unanswerable in-scope " +
  "question, gently find out what the asker actually needs, so " +
  "the to-do is actionable. Warm and curious, never an " +
  "interrogation: ONE clarifying question at a time, at most " +
  "three rounds, then stop. Ask about the design criteria — what " +
  "they actually need, what 'good' would look like, which area " +
  "or section they care about, what form the answer should take. " +
  "On the FIRST unanswerable turn, set elicit=true and put your " +
  "one clarifying question in clarify_question; the 'answer' " +
  "field still carries the partial picture + sizing above, and " +
  "criteria starts as [] (or what the question itself already " +
  "reveals). On each FOLLOW-UP turn (an ELICITATION IN PROGRESS " +
  "block precedes the question): read the user's reply, add what " +
  "it reveals to 'criteria' — the design criteria IN THE USER'S " +
  "OWN WORDS, as short phrases — and either ask the next single " +
  "clarifying question (elicit=true, answer = a short warm " +
  "acknowledgement plus the question) or close (elicit=false, " +
  "elicitation_done=true, answer = the warm close: 'That's a " +
  "really good question' + one line summing up what was gathered " +
  "for the to-do + \"I'll get this to Paul now.\"). CLOSE as soon " +
  "as the user has nothing more to add — 'that's all', 'no', " +
  "'I don't know', a shrug, or a third round is done. If the " +
  "user's message is a NEW question instead of a reply to the " +
  "clarifying question, answer the new question normally (scope " +
  "and answerable as usual) and set elicitation_done=true with " +
  "the criteria gathered so far. If the question is already fully " +
  "specified and no clarifying question could help, set " +
  "elicit=false and elicitation_done=true on the first turn.\n\n" +
  "Respond with JSON only, no markdown fences, exactly this shape:\n" +
  "{\"answer\": \"...\", \"sources\": [\"...\"], \"focus\": null or " +
  "{\"type\": \"section|gap|asset\", \"name\"|\"serial\": \"...\"}, " +
  "\"scope\": \"in\"|\"out\", \"answerable\": true|false, " +
  "\"elicit\": true|false, \"clarify_question\": \"...\"|null, " +
  "\"criteria\": [\"...\"]|null, \"elicitation_done\": true|false, " +
  "\"missing_data\": \"...\"|null, " +
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
        /* Design criteria the asker gave during elicitation, in
           their own words — what they actually need, what "good"
           would look like, which area, what form the answer should
           take. Empty until elicitation gathers some. */
        design_criteria: Array.isArray(modelOut.criteria)
          ? modelOut.criteria : [],
        elicitation_complete: modelOut.elicitation_done === true,
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

/* Update an already-queued entry by id (a later elicitation turn
   adds the design criteria and marks elicitation complete). The
   entry keeps its id and asked_at; last_asked_at is not bumped —
   this is the same question, not a repeat. Returns the entry, or
   null when it cannot be found or written. */
async function queueUpdateEntry(token, queueId, patch) {
  for (var attempt = 0; attempt < 2; attempt++) {
    var read;
    try {
      read = await readRepoJson(token, QUEUE_PATH);
    } catch (e) {
      return null;
    }
    var queue = read.data;
    if (!queue || !Array.isArray(queue.entries)) return null;
    var entry = null;
    for (var i = 0; i < queue.entries.length; i++) {
      if (queue.entries[i].id === queueId) {
        entry = queue.entries[i];
        break;
      }
    }
    if (!entry) return null;
    var keys = Object.keys(patch);
    for (var k = 0; k < keys.length; k++) {
      entry[keys[k]] = patch[keys[k]];
    }
    try {
      await writeRepoJson(token, QUEUE_PATH, read.sha, queue,
        "Ask the trail: update queued question " + queueId);
      return entry;
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
async function emailUnanswered(key, entry, isUpdate) {
  var short_q = entry.question.length > 60
    ? entry.question.slice(0, 60) + "..." : entry.question;
  if (isUpdate) {
    /* Second mail, only when elicitation gathered criteria: Paul
       already got the question on the first mail; this one carries
       what the asker added, so he sees it without opening the
       queue file. */
    var criteriaLines = (entry.design_criteria || []).map(
      function (c) { return "- " + c; });
    var lines = [
      "An update on a trail question you were already emailed about:",
      "",
      "Question: " + entry.question,
      "Queue entry: " + entry.id + " (" + QUEUE_FILE_URL + ")",
      "",
      "What the asker said they would want (design criteria, in "
        + "their words):",
    ].concat(criteriaLines.length ? criteriaLines : ["(none given)"]).concat([
      "",
      "Work sizing, as before:",
      "- Effort: " + (entry.work_estimate || "not estimated"),
      "- Data needed: " + (entry.data_needed || "not stated"),
      "- Data already exists: " + (entry.data_exists || "unknown"),
      "- Approval needed from: " + (entry.approval_needed || "none stated"),
      "",
      "Suggested next step: " + (entry.suggested_next_step || "none stated"),
    ]);
    var res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "Muse <onboarding@resend.dev>",
        to: ["pauljmorin@gmail.com"],
        subject: "Update: trail question — design criteria gathered: " +
          short_q,
        text: lines.join("\n"),
      }),
      signal: AbortSignal.timeout(15000),
    });
    return res.ok;
  }
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
    "The asker is being asked what they would want the answer to "
      + "do; anything they add will update the queue entry, and a "
      + "second email will follow if they give design criteria.",
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

/* POST /ask — {question, history?, elicitation?}. history is the
   conversation so far ([{role: "user"|"assistant", text}]) so
   follow-ups resolve ("how many miles is that?"). elicitation is
   the state of an in-progress unanswered question ({queue_id,
   original_question, missing_data, rounds, last_question}).
   Returns {ok, answer, sources, focus, scope, unanswered, queued,
   queue_id, email_sent, elicitation}. */
async function handleAsk(body, env, origin, ip) {
  if (!body || typeof body !== "object" ||
      typeof body.question !== "string" ||
      body.question.trim().length === 0) {
    return json(400, { ok: false,
      error: "question is required." }, origin);
  }
  var question = body.question.trim().slice(0, 500);
  /* History: at most 8 turns (4 exchanges), each capped — the
     digest is already ~5,000 tokens and every turn re-sends it. */
  var history = [];
  if (Array.isArray(body.history)) {
    body.history.slice(-8).forEach(function (h) {
      if (h && typeof h.text === "string" &&
          (h.role === "user" || h.role === "assistant")) {
        history.push({ role: h.role,
          text: h.text.slice(0, 500) });
      }
    });
  }
  var elicitation = null;
  if (body.elicitation && typeof body.elicitation === "object") {
    elicitation = {
      queue_id: body.elicitation.queue_id || null,
      original_question:
        String(body.elicitation.original_question || "").slice(0, 500),
      missing_data:
        String(body.elicitation.missing_data || "").slice(0, 500),
      rounds: parseInt(body.elicitation.rounds, 10) || 0,
      last_question:
        String(body.elicitation.last_question || "").slice(0, 500),
      criteria: Array.isArray(body.elicitation.criteria)
        ? body.elicitation.criteria.filter(function (c) {
            return typeof c === "string";
          }).slice(0, 10).map(function (c) { return c.slice(0, 200); })
        : [],
    };
  }
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
  var userText = "TRAIL DIGEST:\n" + digestText;
  if (history.length) {
    userText += "\n\nCONVERSATION SO FAR (most recent last):\n" +
      history.map(function (h) {
        return (h.role === "user" ? "User: " : "Assistant: ") + h.text;
      }).join("\n");
  }
  if (elicitation && elicitation.queue_id) {
    userText += "\n\nELICITATION IN PROGRESS: the user asked '" +
      elicitation.original_question + "' and the digest could not " +
      "answer it (missing: " + (elicitation.missing_data ||
      "not stated") + "). Design criteria gathered so far, in the " +
      "user's words: " +
      JSON.stringify(elicitation.criteria || []) + ". This is round " +
      (elicitation.rounds + 1) +
      " of 3. The user's message below is a reply to the " +
      "clarifying question '" + elicitation.last_question + "' — " +
      "unless it is a new question, in which case answer it " +
      "normally and set elicitation_done=true with the criteria " +
      "gathered so far.";
  }
  userText += "\n\nQUESTION:\n" + question;
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
          contents: [{ role: "user", parts: [{ text: userText }] }],
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
  var scope = modelOut.scope === "out" ? "out" : "in";
  var focus = scope === "in" ? validFocus(modelOut.focus, digest) : null;
  var out = {
    ok: true,
    answer: modelOut.answer,
    sources: Array.isArray(modelOut.sources) ? modelOut.sources : [],
    focus: focus,
    scope: scope,
    unanswered: scope === "in" && modelOut.answerable === false,
    queued: false,
    queue_id: null,
    email_sent: false,
    elicitation: null,
  };
  if (scope === "out") {
    /* Out of scope is not a data gap: brief redirect, no queue,
       no email. The panel shows the answer as-is. */
    return json(200, out, origin);
  }
  /* An elicitation was already in progress: the model returns the
     full criteria list each turn, so update the original entry
     with whatever was gathered — whether this turn continues the
     elicitation, closes it, or answers a new question instead. */
  var criteria = Array.isArray(modelOut.criteria)
    ? modelOut.criteria : null;
  var done = modelOut.elicitation_done === true;
  if (elicitation && elicitation.queue_id && env.GITHUB_TOKEN &&
      (criteria !== null || done)) {
    var patch = {};
    if (criteria !== null) patch.design_criteria = criteria;
    if (done) patch.elicitation_complete = true;
    if (modelOut.work_estimate) {
      patch.work_estimate = modelOut.work_estimate;
    }
    if (modelOut.data_needed) patch.data_needed = modelOut.data_needed;
    if (modelOut.data_exists) patch.data_exists = modelOut.data_exists;
    if (modelOut.approval_needed) {
      patch.approval_needed = modelOut.approval_needed;
    }
    if (modelOut.suggested_next_step) {
      patch.suggested_next_step = modelOut.suggested_next_step;
    }
    var updated = await queueUpdateEntry(env.GITHUB_TOKEN,
      elicitation.queue_id, patch);
    out.queued = !!updated;
    out.queue_id = elicitation.queue_id;
    /* Second email only when elicitation closed WITH criteria —
       Paul already got the question on the first mail. */
    if (updated && done && criteria && criteria.length > 0 &&
        env.RESEND_API_KEY) {
      try {
        out.email_sent = await emailUnanswered(env.RESEND_API_KEY,
          {
            id: elicitation.queue_id,
            question: elicitation.original_question,
            asked_at: new Date().toISOString(),
            design_criteria: criteria,
            work_estimate: modelOut.work_estimate,
            data_needed: modelOut.data_needed,
            data_exists: modelOut.data_exists,
            approval_needed: modelOut.approval_needed,
            suggested_next_step: modelOut.suggested_next_step,
          }, true);
      } catch (e) {
        out.email_sent = false;
      }
    }
  }
  if (modelOut.answerable === false) {
    /* Route to BOTH Paul and Muse: the durable queue file in the
       repo is the coordinator's source (the weekly watch reads it),
       and Paul gets the email. Neither is a fallback for the other.
       A queue/email failure never blocks the asker's answer. */
    if (!elicitation || !elicitation.queue_id) {
      /* First unanswerable turn: create the entry now, so the
         question reaches Paul and Muse even if the asker walks
         away mid-elicitation. Later turns update this entry. */
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
          }, false);
        } catch (e) {
          emailSent = false;
        }
      }
      out.queued = !!queueId;
      out.queue_id = queueId;
      out.email_sent = emailSent;
    }
    /* Elicitation state for the panel: keep asking one question
       at a time, at most three rounds, then close. */
    var rounds = elicitation ? elicitation.rounds : 0;
    var keepGoing = modelOut.elicit === true && !done && rounds < 3 &&
      typeof modelOut.clarify_question === "string" &&
      modelOut.clarify_question.trim().length > 0;
    out.elicitation = {
      active: keepGoing,
      question: keepGoing ? modelOut.clarify_question : null,
      rounds: keepGoing ? rounds + 1 : rounds,
      queue_id: out.queue_id,
      original_question: elicitation ? elicitation.original_question
        : question,
      missing_data: modelOut.missing_data || (elicitation
        ? elicitation.missing_data : null),
      criteria: criteria || (elicitation ? elicitation.criteria : []),
    };
  } else if (elicitation && elicitation.queue_id) {
    /* The user asked a new question mid-elicitation and it was
       answered: the loop closes, the original entry keeps the
       criteria gathered so far (updated above). */
    out.elicitation = {
      active: false,
      question: null,
      rounds: elicitation.rounds,
      queue_id: elicitation.queue_id,
      original_question: elicitation.original_question,
      missing_data: elicitation.missing_data,
      criteria: criteria || elicitation.criteria,
    };
  }
  return json(200, out, origin);
}

/* ------------------------------------------------ Voice: talk to
   the trail. The panel's voice mode is a turn-based pipeline, not
   full duplex: the browser records one spoken turn (MediaRecorder),
   /transcribe turns it into text with the same Gemini key, /ask
   answers it with the same grounding and history, and /speak reads
   the answer aloud with Gemini TTS (voice Sulafat — Warm). A full
   duplex realtime session (Gemini Live, gemini-3.8-live, WebSocket)
   is the named v2: it would need a Worker WebSocket proxy because
   the key cannot live in the page, and it bills ~$0.005/min audio
   in + $0.018/min audio out before history re-billing
   (~$0.25–0.30/min in practice). The pipeline costs ~2 cents per
   minute of conversation, almost all of it the spoken answer. */

/* POST /transcribe — {audio_b64, mime}. The browser sends one
   recorded turn (webm/opus from Chrome, mp4/aac from Safari — both
   are accepted audio inputs). Returns {ok, transcript}. */
async function handleTranscribe(body, env, origin, ip) {
  if (!body || typeof body.audio_b64 !== "string" ||
      body.audio_b64.length === 0 ||
      body.audio_b64.length > 7000000 ||
      typeof body.mime !== "string" ||
      body.mime.indexOf("audio/") !== 0) {
    return json(400, { ok: false,
      error: "audio_b64 (base64 audio) and mime (audio/...) are "
        + "required." }, origin);
  }
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
          contents: [{ role: "user", parts: [
            { text: "Transcribe this spoken question exactly, word "
              + "for word. It is a question about a hiking trail. "
              + "Return only the transcription, no other text." },
            { inlineData: { mimeType: body.mime,
              data: body.audio_b64 } },
          ] }],
          generationConfig: { temperature: 0, maxOutputTokens: 500 },
        }),
        signal: AbortSignal.timeout(30000),
      });
  } catch (e) {
    return json(502, { ok: false,
      error: "Transcription failed: " + e.message }, origin);
  }
  if (!genRes.ok) {
    return json(502, { ok: false,
      error: "Transcription failed (" + genRes.status + ")." }, origin);
  }
  var genBody;
  try {
    genBody = await genRes.json();
  } catch (e) {
    return json(502, { ok: false,
      error: "Transcription returned unreadable output." }, origin);
  }
  var transcript = "";
  try {
    transcript = genBody.candidates[0].content.parts
      .map(function (p) { return p.text || ""; }).join("").trim();
  } catch (e) {}
  return json(200, { ok: true, transcript: transcript }, origin);
}

/* POST /speak — {text}. Gemini TTS (Interactions API, the
   documented surface for gemini-3.8-flash-tts) returns complete
   WAV, so the panel can play it in a plain <audio> element.
   Returns {ok, audio_b64, mime: "audio/wav", voice}. */
async function handleSpeak(body, env, origin, ip) {
  if (!body || typeof body.text !== "string" ||
      body.text.trim().length === 0) {
    return json(400, { ok: false, error: "text is required." }, origin);
  }
  var text = body.text.trim().slice(0, 2000);
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
  var ttsModel = env.TTS_MODEL || DEFAULT_TTS_MODEL;
  var voice = env.TTS_VOICE || DEFAULT_TTS_VOICE;
  var ttsRes;
  try {
    ttsRes = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/interactions",
      {
        method: "POST",
        headers: {
          "x-goog-api-key": env.GEMINI_API_KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: ttsModel,
          input: [{ type: "user_input", content: [{ type: "text",
            text: text,
            annotations: [{ type: "speech_metadata",
              style: "warm and friendly" }],
          }] }],
          response_format: { type: "audio" },
          generation_config: { speech_config: [{ voice: voice }] },
        }),
        signal: AbortSignal.timeout(30000),
      });
  } catch (e) {
    return json(502, { ok: false,
      error: "Speech failed: " + e.message }, origin);
  }
  if (!ttsRes.ok) {
    return json(502, { ok: false,
      error: "Speech failed (" + ttsRes.status + ")." }, origin);
  }
  var ttsBody;
  try {
    ttsBody = await ttsRes.json();
  } catch (e) {
    return json(502, { ok: false,
      error: "Speech returned unreadable output." }, origin);
  }
  var audioB64 = null;
  try {
    var steps = ttsBody.steps || [];
    for (var i = steps.length - 1; i >= 0; i--) {
      var content = steps[i].content || [];
      for (var j = content.length - 1; j >= 0; j--) {
        if (content[j].type === "audio" && content[j].data) {
          audioB64 = content[j].data;
          break;
        }
      }
      if (audioB64) break;
    }
  } catch (e) {}
  if (!audioB64) {
    return json(502, { ok: false,
      error: "Speech returned no audio." }, origin);
  }
  return json(200, { ok: true, audio_b64: audioB64,
    mime: "audio/wav", voice: voice }, origin);
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
    if (url.pathname === "/transcribe") {
      return handleTranscribe(body, env, origin, ip);
    }
    if (url.pathname === "/speak") {
      return handleSpeak(body, env, origin, ip);
    }
    /* Stubs (Paul, Nov 12): same Worker, same GitHub login, one more
       endpoint each when the chapter is ready for them. */
    if (url.pathname === "/report") return notImplemented("report", origin);
    if (url.pathname === "/adopt") return notImplemented("adopt", origin);
    if (url.pathname === "/pin") return notImplemented("pin", origin);
    return json(404, { ok: false, error: "Unknown endpoint." }, origin);
  },
};
