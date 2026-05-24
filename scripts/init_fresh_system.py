#!/usr/bin/env python3
"""Init script for a system we owned.

For a system under our control, this script would seed catalog, users,
and categories using the same services and components used in regression
— same code path, same coverage, no separate "fixture rig" to maintain.

For eBay (public, read-only, guest-only) the seed functions are
unimplemented; this script only verifies connectivity to the target
environment. The pattern is here; the seed work happens when we own
the SUT.
"""

import argparse
import urllib.error
import urllib.request

from ebay_automation.db.client import TestDatabase


def verify_connectivity(env) -> bool:
    # GET, not HEAD: eBay's root returns 4xx to HEAD even when the site
    # is fully reachable, via a redirect to a page that rejects HEAD.
    try:
        with urllib.request.urlopen(env.base_url, timeout=10) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, OSError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="dev", help="env id from db/data.yaml (environments)")
    env = TestDatabase("db").environments.get(parser.parse_args().env)
    print(f"verifying {env.base_url}...")
    ok = verify_connectivity(env)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
