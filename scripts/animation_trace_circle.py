#!/usr/bin/env python3
"""Build a deterministic circle animation trace hash from export-json payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any


CLOCKWISE_TOKENS = {"clockwise", "cw"}
COUNTERCLOCKWISE_TOKENS = {"counterclockwise", "ccw"}


def as_count(beats: Any) -> int:
    try:
        n = float(beats)
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    return int(round(n))


def rotate_forward(arr: list[str], delta: int) -> list[str]:
    if not arr:
        return []
    n = len(arr)
    d = delta % n
    if d < 0:
        d += n
    if d == 0:
        return arr[:]
    return [arr[(i + d) % n] for i in range(n)]


def split_who(who: Any) -> list[str]:
    raw = str(who or "").strip()
    if not raw:
        return []
    return [tok for tok in re.split(r"[\s,|/]+", raw) if tok]


def parse_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def first_order_slots(orders: Any) -> list[str]:
    if not isinstance(orders, list):
        return []
    for order in orders:
        if not isinstance(order, dict):
            continue
        slots = order.get("slots")
        if isinstance(slots, list) and slots:
            return [str(x) for x in slots if str(x)]
    return []


def is_cyclic_equivalent(a: list[str], b: list[str]) -> bool:
    if len(a) != len(b):
        return False
    if not a:
        return True
    try:
        start = b.index(a[0])
    except ValueError:
        return False
    n = len(a)
    for i in range(n):
        if a[i] != b[(start + i) % n]:
            return False
    return True


def swap_in_order(order: list[str], a: str, b: str) -> bool:
    try:
        ia = order.index(a)
        ib = order.index(b)
    except ValueError:
        return False
    if ia == ib:
        return False
    order[ia], order[ib] = order[ib], order[ia]
    return True


def rotate_targets_in_order(order: list[str], targets: list[str], delta_step: int) -> list[str]:
    out = order[:]
    if not out:
        return out
    target_set = {t for t in targets if t}
    indices = [i for i, dancer_id in enumerate(out) if dancer_id in target_set]
    if len(indices) < 2:
        return out

    src = out[:]
    if delta_step > 0:
        for i, idx in enumerate(indices):
            out[idx] = src[indices[(i + 1) % len(indices)]]
    elif delta_step < 0:
        for i, idx in enumerate(indices):
            out[idx] = src[indices[(i - 1 + len(indices)) % len(indices)]]
    return out


def resolve_who_targets(who: Any, order: list[str]) -> list[str]:
    tokens = split_who(who)
    if not tokens:
        return []
    if len(tokens) == 1 and tokens[0] == "all":
        return order[:]
    known = set(order)
    return [tok for tok in tokens if tok in known]


def compute_positions(order: list[str], radius: float = 0.85, angle_offset: float = -math.pi / 2) -> dict[str, dict[str, float]]:
    n = len(order)
    if n == 0:
        return {}
    out: dict[str, dict[str, float]] = {}
    for idx, dancer_id in enumerate(order):
        angle = angle_offset + (2 * math.pi * idx) / n
        out[dancer_id] = {
            "x": round(math.cos(angle) * radius, 6),
            "y": round(math.sin(angle) * radius, 6),
        }
    return out


def build_events(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    figures = payload.get("figures") if isinstance(payload.get("figures"), list) else []
    events: list[dict[str, Any]] = []
    total = 0

    for fig in figures:
        if not isinstance(fig, dict):
            continue
        steps = fig.get("steps") if isinstance(fig.get("steps"), list) else []
        for step in steps:
            if not isinstance(step, dict):
                continue
            total += as_count(step.get("beats"))
            primitives = step.get("primitives") if isinstance(step.get("primitives"), list) else []
            for primitive in primitives:
                if not isinstance(primitive, dict):
                    continue
                events.append(
                    {
                        "t": total,
                        "kind": str(primitive.get("kind", "")),
                        "frame": str(primitive.get("frame", "")),
                        "dir": str(primitive.get("dir", "")),
                        "who": str(primitive.get("who", step.get("who", ""))),
                        "a": str(primitive.get("a", "")),
                        "b": str(primitive.get("b", "")),
                        "preserveOrder": str(primitive.get("preserveOrder", "")),
                    }
                )
    return events, total


def build_initial_order(payload: dict[str, Any]) -> list[str]:
    topology = payload.get("topology") if isinstance(payload.get("topology"), dict) else {}
    circle = topology.get("circle") if isinstance(topology.get("circle"), dict) else {}
    orders = circle.get("orders") if isinstance(circle.get("orders"), list) else []
    return first_order_slots(orders)


def apply_event(order: list[str], event: dict[str, Any]) -> list[str]:
    kind = str(event.get("kind", "")).lower()
    preserve_order = parse_bool(event.get("preserveOrder"))

    if kind == "swapplaces":
        a = str(event.get("a", ""))
        b = str(event.get("b", ""))
        if not a or not b:
            return order
        candidate = order[:]
        if not swap_in_order(candidate, a, b):
            return order
        if preserve_order and not is_cyclic_equivalent(order, candidate):
            return order
        return candidate

    if kind == "move":
        if str(event.get("frame", "")) != "formation":
            return order

        direction = str(event.get("dir", "")).lower()
        delta_step = 0
        if direction in COUNTERCLOCKWISE_TOKENS:
            delta_step = 1
        elif direction in CLOCKWISE_TOKENS:
            delta_step = -1
        if delta_step == 0:
            return order

        targets = resolve_who_targets(event.get("who"), order)
        if not targets or len(targets) == len(order):
            candidate = rotate_forward(order, delta_step)
        else:
            candidate = rotate_targets_in_order(order, targets, delta_step)

        if preserve_order and not is_cyclic_equivalent(order, candidate):
            return order
        return candidate

    return order


def trace_from_payload(payload: dict[str, Any], source: str) -> dict[str, Any]:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    formation_kind = str(meta.get("formationKind", ""))
    order = build_initial_order(payload)
    events, total = build_events(payload)

    snapshots: list[dict[str, Any]] = []
    snapshots.append({"t": 0, "order": order[:], "positions": compute_positions(order)})

    idx = 0
    current = order[:]
    for t in range(1, total + 1):
        while idx < len(events) and int(events[idx].get("t", 0)) <= t:
            current = apply_event(current, events[idx])
            idx += 1
        snapshots.append({"t": t, "order": current[:], "positions": compute_positions(current)})

    hash_payload = {
        "formationKind": formation_kind,
        "events": events,
        "snapshots": snapshots,
        "totalCounts": total,
    }
    digest = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    return {
        "source": source,
        "totalCounts": total,
        "eventCount": len(events),
        "traceHash": digest,
    }


def load_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    if args.json_file:
        payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        return payload if isinstance(payload, dict) else {}, args.source or str(args.json_file)

    cmd = ["bin/fdml", "export-json", args.fdml_xml]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(proc.stdout)
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    return payload if isinstance(payload, dict) else {}, args.source or str(args.fdml_xml)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic circle animation trace hash")
    parser.add_argument("fdml_xml", nargs="?", help="FDML XML file")
    parser.add_argument("--json", dest="json_file", help="Use export-json payload file instead of XML")
    parser.add_argument("--source", help="Source label written into trace output")
    args = parser.parse_args()

    if not args.fdml_xml and not args.json_file:
        parser.error("provide either <fdml_xml> or --json <payload.json>")

    payload, source = load_payload(args)
    out = trace_from_payload(payload, source)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
