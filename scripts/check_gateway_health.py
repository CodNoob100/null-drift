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


def check_health(base_url):
    with urllib.request.urlopen(base_url.rstrip("/") + "/health", timeout=5) as response:
        payload = json.load(response)
    return isinstance(payload, dict) and payload.get("status") == "ok"


def main():
    parser = argparse.ArgumentParser(description="Wait for null-drift gateway readiness")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.wait_seconds < 0:
        parser.error("--wait-seconds must be nonnegative")
    if not args.url.startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:")):
        parser.error("Only local loopback gateway URLs are supported")
    deadline = time.monotonic() + args.wait_seconds
    while True:
        try:
            if check_health(args.url):
                print("Gateway is healthy")
                return 0
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print("Waiting for gateway: {}".format(exc), file=sys.stderr)
        if time.monotonic() >= deadline:
            print("Gateway did not become ready; inspect Compose logs", file=sys.stderr)
            return 1
        time.sleep(min(5, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    sys.exit(main())
