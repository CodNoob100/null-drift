#!/usr/bin/env python3
"""Check the health of a trusted local null-drift gateway."""
import json
import urllib.request


def main():
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
        payload = json.load(response)
    if payload.get("status") != "ok":
        raise SystemExit("Gateway is not ready")
    print("Gateway is healthy")


if __name__ == "__main__":
    main()
