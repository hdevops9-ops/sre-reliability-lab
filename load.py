"""Bounded sequential traffic generator for the local lab only."""
import argparse
import time
from urllib.error import HTTPError
from urllib.request import urlopen

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--requests", type=int, default=600)
    args = p.parse_args()
    if not 1 <= args.requests <= 10000: p.error("requests must be 1..10000")
    counts = {}
    for _ in range(args.requests):
        try:
            with urlopen("http://127.0.0.1:8080/work", timeout=10) as r: status = r.status
        except HTTPError as e:
            status = e.code
            e.close()
        counts[status] = counts.get(status, 0) + 1
        time.sleep(.1)
    print(counts)
