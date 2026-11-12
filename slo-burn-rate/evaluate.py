"""Evaluate two windows of request-based availability telemetry."""

import argparse
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=(
        "healthy", "incident", "telemetry-gap", "no-traffic"
    ))
    args = parser.parse_args()
    decision, short, long = evaluate(scenario(args.scenario), end_minute=60)
    print(decision)
    for window in (short, long):
        burn = window.burn
        display = "unknown" if burn is None else f"{burn:.2f}x"
        print(f"{window.minutes}m: burn={display}, requests={window.requests}, "
              f"errors={window.errors}, missing_minutes={window.missing}")


if __name__ == "__main__":
    main()
