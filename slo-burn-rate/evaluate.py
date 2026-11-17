"""Evaluate two windows of request-based availability telemetry."""

import argparse
import csv
from dataclasses import dataclass
from decimal import Decimal

ERROR_BUDGET = Decimal("0.001")
PAGE_BURN = Decimal("14.4")


@dataclass(frozen=True)
class Minute:
    requests: int
    errors: int

    def __post_init__(self):
        if not 0 <= self.errors <= self.requests:
            raise ValueError("Expected 0 <= errors <= requests")


@dataclass(frozen=True)
class Window:
    minutes: int
    missing: int
    requests: int
    errors: int

    @property
    def burn(self):
        if self.missing or not self.requests:
            return None
        return Decimal(self.errors) / Decimal(self.requests) / ERROR_BUDGET


def summarize(samples, end_minute, duration):
    observed = [
        samples[minute]
        for minute in range(end_minute - duration, end_minute)
        if minute in samples
    ]
    return Window(
        duration,
        duration - len(observed),
        sum(sample.requests for sample in observed),
        sum(sample.errors for sample in observed),
    )


def evaluate(samples, end_minute):
    short = summarize(samples, end_minute, 5)
    long = summarize(samples, end_minute, 60)
    if short.missing or long.missing:
        decision = "INVESTIGATE_TELEMETRY"
    elif short.burn is None or long.burn is None:
        decision = "INSUFFICIENT_TRAFFIC"
    elif short.burn >= PAGE_BURN and long.burn >= PAGE_BURN:
        decision = "PAGE"
    else:
        decision = "MONITOR"
    return decision, short, long


def scenario(name):
    samples = {minute: Minute(1000, 1) for minute in range(60)}
    if name == "incident":
        for minute in range(45, 60):
            samples[minute] = Minute(1000, 80)
    elif name == "telemetry-gap":
        del samples[59]
    elif name == "no-traffic":
        samples = {minute: Minute(0, 0) for minute in range(60)}
    return samples


def read_samples(stream):
    rows = csv.DictReader(stream, strict=True)
    if rows.fieldnames != ["minute", "requests", "errors"]:
        raise ValueError("Expected CSV header: minute,requests,errors")
    samples = {}
    for row in rows:
        try:
            if None in row:
                raise ValueError("Unexpected extra column")
            minute = int(row["minute"])
            if minute in samples:
                raise ValueError(f"Duplicate minute {minute}")
            samples[minute] = Minute(int(row["requests"]), int(row["errors"]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CSV line {rows.line_num}: {exc}") from exc
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", help="CSV file with minute,requests,errors columns")
    source.add_argument("--scenario", choices=(
        "healthy", "incident", "telemetry-gap", "no-traffic"
    ))
    parser.add_argument("--end-minute", type=int, help="Exclusive end of the CSV evaluation window")
    args = parser.parse_args()
    if args.csv:
        if args.end_minute is None:
            parser.error("--csv requires --end-minute")
        try:
            with open(args.csv, encoding="utf-8", newline="") as stream:
                samples = read_samples(stream)
        except (OSError, ValueError, csv.Error) as exc:
            parser.error(str(exc))
        end_minute = args.end_minute
    else:
        if args.end_minute is not None:
            parser.error("--end-minute is only supported with --csv")
        samples = scenario(args.scenario)
        end_minute = 60
    decision, short, long = evaluate(samples, end_minute)
    print(decision)
    for window in (short, long):
        burn = window.burn
        display = "unknown" if burn is None else f"{burn:.2f}x"
        print(f"{window.minutes}m: burn={display}, requests={window.requests}, "
              f"errors={window.errors}, missing_minutes={window.missing}")


if __name__ == "__main__":
    main()
