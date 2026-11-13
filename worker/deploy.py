#!/usr/bin/env python3
"""Deploy the itm-save Cloudflare Worker script.

Uploads a JavaScript file as the `itm-save` Worker on the
Pauljmorin@gmail.com Cloudflare account. The Cloudflare credential
comes from the registered custom.cloudflare connection via the
authd surrogate exchange; no credential appears in this file, in
arguments, or in logs.

Usage:
  python3 worker/deploy.py worker/itm-save.js

The script uses ES-module syntax (`export default`), so the upload
is a multipart PUT to
  /accounts/<account>/workers/scripts/itm-save
with a JSON metadata part naming the main module and the script
part itself. A plain raw-JS PUT is treated as a classic service
worker and rejects `export` (HTTP 400, error 10021). The generic
cf-api helper cannot do this (it sends JSON bodies).
"""
import json
import sys

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import dynamic_credential_entry

import requests

API = "https://api.cloudflare.com/client/v4"
ACCOUNT_ID = "2a85f76947df5901cc13e2dba2f02082"
SCRIPT_NAME = "itm-save"
CONNECTOR = "custom.cloudflare"


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], "rb") as f:
        script_bytes = f.read()
    metadata = {
        "main_module": "worker.js",
        "compatibility_date": "2024-01-01",
    }
    entry = dynamic_credential_entry(CONNECTOR, "access_token")
    token = str(entry["surrogate"]).strip()
    url = "%s/accounts/%s/workers/scripts/%s" % (API, ACCOUNT_ID, SCRIPT_NAME)
    files = {
        "metadata": (None, json.dumps(metadata), "application/json"),
        "worker.js": ("worker.js", script_bytes, "application/javascript+module"),
    }
    resp = requests.put(
        url,
        files=files,
        headers={"Authorization": "Bearer " + token},
        timeout=120,
    )
    try:
        print(json.dumps(resp.json(), indent=1))
    except Exception:
        print("HTTP %d %s" % (resp.status_code, resp.text[:1000]))
    return 0 if resp.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
