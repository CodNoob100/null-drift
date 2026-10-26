#!/usr/bin/env python3
"""Probe the health of a trusted local null-drift gateway.

Usage: python3 scripts/check_gateway_health.py [--url http://127.0.0.1:8000] [--wait-seconds 180]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def validate_local_url(base_url):
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid gateway URL") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
        or parsed.username is not None
        or parsed.password is not None
        or port is None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Only loopback HTTP gateway URLs with an explicit port are supported"
        )
    return base_url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_health(base_url):
    validate_local_url(base_url)
    no_proxy = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(no_proxy, NoRedirect())
    with opener.open(base_url.rstrip("/") + "/health", timeout=5) as response:
        payload = json.load(response)
    return isinstance(payload, dict) and payload.get("status") == "ok"


def main():
    parser = argparse.ArgumentParser(
        description="Wait for null-drift gateway readiness"
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.wait_seconds < 0:
        parser.error("--wait-seconds must be nonnegative")
    try:
        validate_local_url(args.url)
    except ValueError as exc:
        parser.error(str(exc))
    deadline = time.monotonic() + args.wait_seconds
    while True:
        try:
            if check_health(args.url):
                print("Gateway is healthy")
                return 0
        except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as exc:
            print("Waiting for gateway: {}".format(exc), file=sys.stderr)
        if time.monotonic() >= deadline:
            print("Gateway did not become ready; inspect Compose logs", file=sys.stderr)
            return 1
        time.sleep(min(5, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    sys.exit(main())
