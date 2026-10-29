#!/usr/bin/env python3
"""Reference logic for the weekly model switcher (design prototype, research artefact).

Three parts, no third-party dependencies:

  screen    Stage 1. Pull OpenRouter's public model and ZDR-endpoint lists and rank
            eligible endpoints by ESTIMATED cost per game session (list price x assumed tokens).
  decide    Stage 4. Pure decision function: given MEASURED results per endpoint (from the
            shadow evaluation), keep or switch the champion. Reads JSON on stdin or a file.
  selftest  Checks the decision rules on small hand-written cases (test inputs, not data).

Stages 2-3 (shadow evaluation on seeded "golden" games, canary rollout) need the game engine
and are described in research.md section 5; `decide` consumes their output.

All thresholds are PLACEHOLDERS to calibrate; they are not research findings.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from dataclasses import dataclass, field

API = "https://openrouter.ai/api/v1"


# ---------------------------------------------------------------- stage 1: screen
def fetch(path: str) -> dict:
    req = urllib.request.Request(API + path, headers={"User-Agent": "beergame-model-screen/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:  # public endpoints, no API key needed
        return json.load(r)


def screen(in_tok: int, out_tok: int, required: set[str], min_uptime: float, min_ctx: int,
           top: int, baseline_id: str) -> dict:
    models = {m["id"]: m for m in fetch("/models")["data"]}
    zdr = fetch("/endpoints/zdr")["data"]  # endpoints with a Zero Data Retention policy
    rows, dropped = {}, {}
    for e in zdr:
        mid = e["model_id"]
        m = models.get(mid)
        why = None
        p = e.get("pricing") or {}
        try:
            pi, po = float(p.get("prompt", 0)), float(p.get("completion", 0))
        except (TypeError, ValueError):
            pi = po = -1.0
        if m is None or "text" not in (m.get("architecture", {}).get("output_modalities") or []):
            why = "not a text model in /models"
        elif ":free" in mid or pi <= 0 or po <= 0:
            why = "free, zero or sentinel price"
        elif e.get("status") != 0:
            why = "endpoint status not OK"
        elif not required <= set(e.get("supported_parameters") or []):
            why = "missing required parameter"
        elif (e.get("uptime_last_1d") or 0) < min_uptime:
            why = "uptime below gate"
        elif (e.get("context_length") or 0) < min_ctx:
            why = "context below gate"
        if why:
            dropped[why] = dropped.get(why, 0) + 1
            continue
        cost = pi * in_tok + po * out_tok
        key = (mid, e["provider_name"], e.get("quantization"))
        row = dict(model=mid, provider=e["provider_name"], quant=e.get("quantization"),
                   est_cost=cost, in_per_m=pi * 1e6, out_per_m=po * 1e6,
                   uptime_1d=e.get("uptime_last_1d"),
                   reasoning="reasoning" in (m.get("supported_parameters") or []),
                   cache=bool(e.get("supports_implicit_caching")))
        if key not in rows or cost < rows[key]["est_cost"]:
            rows[key] = row
    ranked = sorted(rows.values(), key=lambda r: r["est_cost"])
    # Baseline is shown even if it fails the parameter gate, so the comparison stays honest.
    base_eps = [e for e in zdr if e["model_id"] == baseline_id]
    base = dict(model=baseline_id, zdr_endpoints=len(base_eps), est_cost=None, passes_required_params=None)
    if base_eps:
        cheapest = min(base_eps, key=lambda e: float(e["pricing"]["prompt"]) * in_tok
                       + float(e["pricing"]["completion"]) * out_tok)
        base["est_cost"] = (float(cheapest["pricing"]["prompt"]) * in_tok
                            + float(cheapest["pricing"]["completion"]) * out_tok)
        base["passes_required_params"] = required <= set(cheapest.get("supported_parameters") or [])
        base["missing_params"] = sorted(required - set(cheapest.get("supported_parameters") or []))
    return dict(assumed_tokens=dict(input=in_tok, output=out_tok), required=sorted(required),
                gates=dict(min_uptime_1d=min_uptime, min_context=min_ctx),
                eligible_endpoints=len(ranked), dropped=dropped, baseline=base, top=ranked[:top])


# ---------------------------------------------------------------- stage 4: decide
@dataclass
class Result:
    """Measured on the golden games for one endpoint (model + provider + quantisation)."""
    endpoint: str
    tasks: int            # decisions attempted
    valid: int            # decisions that passed schema + rule validation without retry/fallback
    cost_usd: float       # sum of usage.cost for ALL calls incl. retries and reasoning tokens
    fidelity_ok: bool     # bullwhip/behaviour inside the calibrated band (see research.md)
    p95_latency_s: float
    uptime: float         # 0..1 over the evaluation window

    @property
    def cost_per_valid(self) -> float:
        return self.cost_usd / self.valid if self.valid else math.inf

    @property
    def invalid_ub(self) -> float:
        return wilson_upper(self.tasks - self.valid, self.tasks)


@dataclass
class Policy:
    min_tasks: int = 3000          # e.g. 30 games x 108 decisions
    max_invalid_ub: float = 0.02   # 95% upper bound on invalid-decision rate
    max_p95_latency_s: float = 8.0
    min_uptime: float = 0.99
    min_saving: float = 0.15       # hysteresis: switch only if >= 15% cheaper per valid task
    cooldown_days: int = 7
    frozen: bool = False           # study or class freeze: never auto-switch


@dataclass
class Decision:
    action: str                    # keep | switch | alert
    endpoint: str
    reason: str
    saving: float | None = None
    ranked: list = field(default_factory=list)


def wilson_upper(fails: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 1.0
    p = fails / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (c + h) / d)


def passes(r: Result, pol: Policy) -> tuple[bool, str]:
    if r.tasks < pol.min_tasks:
        return False, f"only {r.tasks} tasks measured (< {pol.min_tasks})"
    if r.invalid_ub > pol.max_invalid_ub:
        return False, f"invalid-rate upper bound {r.invalid_ub:.3f} > {pol.max_invalid_ub}"
    if not r.fidelity_ok:
        return False, "behavioural fidelity outside calibrated band"
    if r.p95_latency_s > pol.max_p95_latency_s:
        return False, f"p95 latency {r.p95_latency_s:.1f}s > {pol.max_p95_latency_s}s"
    if r.uptime < pol.min_uptime:
        return False, f"uptime {r.uptime:.3f} < {pol.min_uptime}"
    return True, "ok"


def decide(results: list[Result], incumbent: str, days_since_switch: int, pol: Policy) -> Decision:
    by = {r.endpoint: r for r in results}
    inc = by.get(incumbent)
    inc_ok, inc_why = passes(inc, pol) if inc else (False, "incumbent not measured")
    ok = sorted((r for r in results if passes(r, pol)[0]), key=lambda r: r.cost_per_valid)
    ranked = [(r.endpoint, round(r.cost_per_valid, 5)) for r in ok]
    best = ok[0] if ok else None

    if pol.frozen:
        if not inc_ok:
            return Decision("alert", incumbent, f"frozen but incumbent fails gates: {inc_why}", ranked=ranked)
        return Decision("keep", incumbent, "frozen (study/class freeze)", ranked=ranked)
    if not inc_ok:
        if best:  # emergency: incumbent is bad, cooldown does not apply
            return Decision("switch", best.endpoint, f"incumbent fails gates ({inc_why})", ranked=ranked)
        return Decision("alert", incumbent, f"incumbent fails gates ({inc_why}) and no candidate passes", ranked=ranked)
    if best is None or best.endpoint == incumbent:
        return Decision("keep", incumbent, "incumbent is cheapest passing endpoint", ranked=ranked)
    saving = 1 - best.cost_per_valid / inc.cost_per_valid
    if days_since_switch < pol.cooldown_days:
        return Decision("keep", incumbent, f"cooldown ({days_since_switch}d < {pol.cooldown_days}d)", saving, ranked)
    if saving < pol.min_saving:
        return Decision("keep", incumbent, f"saving {saving:.1%} below hysteresis {pol.min_saving:.0%}", saving, ranked)
    return Decision("switch", best.endpoint, f"{saving:.1%} cheaper per valid task, all gates pass", saving, ranked)


def rollback(live_tasks: int, live_invalid: int, errors: int, requests: int, pol: Policy) -> bool:
    """Canary/live guard: True means go back to the previous champion."""
    if live_tasks >= 200 and wilson_upper(live_invalid, live_tasks) > 2 * pol.max_invalid_ub:
        return True
    return requests >= 100 and errors / requests > 0.05


# ---------------------------------------------------------------- self-test
def selftest() -> int:
    def R(name, valid, cost, tasks=3240, fid=True, lat=3.0, up=0.999):
        return Result(name, tasks, valid, cost, fid, lat, up)
    pol = Policy()
    inc = R("A", 3240, 3.24)               # $0.0010 per valid task
    cases = [
        ("cheaper candidate passes -> switch", [inc, R("B", 3240, 2.43)], "A", 30, pol, "switch", "B"),
        ("cheaper but invalid rate too high -> keep", [inc, R("B", 3000, 1.0)], "A", 30, pol, "keep", "A"),
        ("saving below hysteresis -> keep", [inc, R("B", 3240, 3.0)], "A", 30, pol, "keep", "A"),
        ("cooldown -> keep", [inc, R("B", 3240, 2.0)], "A", 3, pol, "keep", "A"),
        ("frozen -> keep", [inc, R("B", 3240, 2.0)], "A", 30, Policy(frozen=True), "keep", "A"),
        ("incumbent fails fidelity, B passes -> switch despite cooldown",
         [R("A", 3240, 3.24, fid=False), R("B", 3240, 5.0)], "A", 1, pol, "switch", "B"),
        ("incumbent fails and nobody passes -> alert", [R("A", 3240, 3.24, up=0.9)], "A", 30, pol, "alert", "A"),
        ("too few tasks measured -> not eligible", [inc, R("B", 500, 0.1, tasks=500)], "A", 30, pol, "keep", "A"),
        ("cost counts retries: cheap per call, dear per valid task",
         [inc, R("B", 3200, 5.0)], "A", 30, pol, "keep", "A"),
    ]
    bad = 0
    for name, res, incumbent, days, p, want_action, want_ep in cases:
        d = decide(res, incumbent, days, p)
        ok = (d.action, d.endpoint) == (want_action, want_ep)
        bad += not ok
        print(("PASS " if ok else "FAIL ") + name + f"  -> {d.action} {d.endpoint} ({d.reason})")
    guard = [(rollback(400, 40, 0, 0, pol), True), (rollback(400, 2, 0, 0, pol), False),
             (rollback(0, 0, 10, 100, pol), True), (rollback(0, 0, 2, 100, pol), False)]
    for i, (got, want) in enumerate(guard):
        bad += got != want
        print(("PASS " if got == want else "FAIL ") + f"rollback guard case {i + 1}")
    print(f"wilson_upper(0 failures, 3240) = {wilson_upper(0, 3240):.5f}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen")
    s.add_argument("--in-tokens", type=int, default=216000, help="assumed input tokens per session")
    s.add_argument("--out-tokens", type=int, default=16200, help="assumed output tokens per session")
    s.add_argument("--require", default="seed,temperature,structured_outputs")
    s.add_argument("--min-uptime", type=float, default=99.0, help="percent, last 24 h")
    s.add_argument("--min-context", type=int, default=32768)
    s.add_argument("--top", type=int, default=20)
    s.add_argument("--baseline", default="anthropic/claude-haiku-5.5")
    d = sub.add_parser("decide")
    d.add_argument("file", help="JSON: {incumbent, days_since_switch, policy{}, results[]}")
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "screen":
        out = screen(a.in_tokens, a.out_tokens, set(filter(None, a.require.split(","))),
                     a.min_uptime, a.min_context, a.top, a.baseline)
        json.dump(out, sys.stdout, indent=1)
        print()
        return 0
    cfg = json.load(open(a.file, encoding="utf-8"))
    res = [Result(**r) for r in cfg["results"]]
    dec = decide(res, cfg["incumbent"], cfg.get("days_since_switch", 99), Policy(**cfg.get("policy", {})))
    json.dump(dec.__dict__, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
