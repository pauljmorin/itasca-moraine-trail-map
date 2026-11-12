/* itm-save — the save service for the Itasca Moraine trail map.
   One Worker, several endpoints. /classify ships first (Paul, Nov 12,
   2026); /report, /adopt and /pin are stubs for later — each is one
   more endpoint on this same Worker, not another build.

   The map is a static site, so it cannot write to GitHub on its own.
   This Worker holds the GitHub login server-side (the secret
   GITHUB_TOKEN, set in the Cloudflare dashboard) and commits the
   change to the repo. The token never appears in this file, is never
   logged, and is never sent anywhere except api.github.com.

   Deploy: python3 worker/deploy.py worker/itm-save.js
   (PUTs this file as the `itm-save` Worker on the Pauljmorin@gmail.com
   Cloudflare account. The API token used for the deploy needs
   Workers Scripts:Edit.)

   Secret (set once, in the Cloudflare dashboard — Workers & Pages →
   itm-save → Settings → Variables → Add secret):
     GITHUB_TOKEN — a fine-grained personal access token on the
     pauljmorin GitHub account, scoped to
     pauljmorin/itasca-moraine-trail-map with Contents Read and write.
*/

var REPO = "pauljmorin/itasca-moraine-trail-map";
var GEOJSON_PATH = "site/data/assets.geojson";
var ALLOWED_ORIGINS = ["https://pauljmorin.github.io"];
var ASSET_TYPES = ["BN", "BR", "BW", "CP", "CS", "KI", "LT",
                   "PK", "PO", "RG", "SG", "SH", "UN", "WT"];
var CONDITIONS = ["good", "fair", "poor", "new", "worn", "replace"];

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

/* Read site/data/assets.geojson from the repo. Returns
   {sha, geojson} or throws an Error with a plain message. */
async function readAssets(token) {
  var res = await fetch(
    "https://api.github.com/repos/" + REPO + "/contents/" + GEOJSON_PATH,
    { headers: ghHeaders(token) });
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
  var geojson;
  try {
    geojson = JSON.parse(text);
  } catch (e) {
    throw new Error("assets.geojson is not valid JSON");
  }
  return { sha: body.sha, geojson: geojson };
}

/* Write the updated GeoJSON back. The file is pretty-printed with a
   1-space indent and a trailing newline, matching the file on disk,
   so a classification commit is a small diff. */
async function writeAssets(token, sha, geojson, message) {
  var text = JSON.stringify(geojson, null, 1) + "\n";
  var bytes = new TextEncoder().encode(text);
  var bin = "";
  for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  var res = await fetch(
    "https://api.github.com/repos/" + REPO + "/contents/" + GEOJSON_PATH,
    {
      method: "PUT",
      headers: Object.assign(ghHeaders(token),
        { "Content-Type": "application/json" }),
      body: JSON.stringify({
        message: message,
        content: btoa(bin),
        sha: sha,
        branch: "main",
      }),
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
    return json(400, { ok: false,
      error: "condition must be one of " + CONDITIONS.join(", ") + "." },
      origin);
  }
  if (!env.GITHUB_TOKEN) {
    return json(500, { ok: false,
      error: "GITHUB_TOKEN not configured on the Worker." }, origin);
  }
  var read;
  try {
    read = await readAssets(env.GITHUB_TOKEN);
  } catch (e) {
    return json(500, { ok: false, error: e.message }, origin);
  }
  var feature = null;
  var feats = read.geojson.features || [];
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
    committed = await writeAssets(env.GITHUB_TOKEN, read.sha,
      read.geojson, message);
  } catch (e) {
    return json(500, { ok: false, error: e.message }, origin);
  }
  return json(200, { ok: true, serial: serial,
    commit: (committed.commit || {}).sha || null }, origin);
}

function notImplemented(name, origin) {
  return json(501, { ok: false,
    error: name + " is not implemented yet." }, origin);
}

export default {
  async fetch(request, env) {
    var origin = request.headers.get("Origin") || "";
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
    /* Stubs (Paul, Nov 12): same Worker, same GitHub login, one more
       endpoint each when the chapter is ready for them. */
    if (url.pathname === "/report") return notImplemented("report", origin);
    if (url.pathname === "/adopt") return notImplemented("adopt", origin);
    if (url.pathname === "/pin") return notImplemented("pin", origin);
    return json(404, { ok: false, error: "Unknown endpoint." }, origin);
  },
};
