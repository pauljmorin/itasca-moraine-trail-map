#!/usr/bin/env python3
"""Deploy the itm-save Cloudflare Worker script.

Uploads a JavaScript file as the `itm-save` Worker on the
Pauljmorin@gmail.com Cloudflare account. The Cloudflare credential
comes from the registered custom.cloudflare connection via the
authd surrogate exchange; no credential appears in this file, in
arguments, or in logs.

Usage:
  python3 worker/deploy.py worker/itm-save.js

The upload is a PUT of the raw JavaScript (Content-Type:
application/javascript) to
  /accounts/<account>/workers/scripts/itm-save
which the generic cf-api helper cannot do (it sends JSON bodies).
"""
import json
import sys
import urllib.request
import urllib.error

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

API = "https://api.cloudflare.com/client/v4"
ACCOUNT_ID = "2a85f76947df5901cc13e2dba2f02082"
SCRIPT_NAME = "itm-save"
CONNECTOR = "custom.cloudflare"
HOSTS = ["api.cloudflare.com"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], "rb") as f:
        body = f.read()
    url = "%s/accounts/%s/workers/scripts/%s" % (API, ACCOUNT_ID, SCRIPT_NAME)
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "application/javascript")
    add_surrogate_to_request(req, CONNECTOR, allowed_hosts=HOSTS)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=120) as resp:
            print(json.dumps(read_json_response(resp), indent=1))
            return 0
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        print("HTTP %d %s" % (e.code, detail[:1000]), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
