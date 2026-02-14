#!/usr/bin/env python3
"""Build a deterministic animation trace hash from export-json payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def _as_count(beats: Any) -> int:
    try:
        n = float(beats)
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    return int(round(n))


def _first_non_empty_slots(orders: Any) -> list[str]:
    if not isinstance(orders, list):
        return []
    for order in orders:
        if isinstance(order, dict) and isinstance(order.get("slots"), list) and order["slots"]:
            return [str(x) for x in order["slots"]]
    return []


def build_base_state(payload: dict[str, Any]) -> dict[str, Any]:
    topology = payload.get("topology") if isinstance(payload, dict) else {}
    topology = topology if isinstance(topology, dict) else {}

    state: dict[str, Any] = {
        "circleOrder": [],
        "lineIds": [],
        "lineOrders": {},
        "twoLinesLineIds": [],
        "twoLinesOrders": {},
        "twoLinesOpposites": [],
        "twoLinesNeighbors": [],
        "twoLinesSeparation": 0,
    }

    circle = topology.get("circle") if isinstance(topology.get("circle"), dict) else {}
    c_orders = circle.get("orders") if isinstance(circle.get("orders"), list) else []
    if c_orders and isinstance(c_orders[0], dict) and isinstance(c_orders[0].get("slots"), list):
        state["circleOrder"] = [str(x) for x in c_orders[0]["slots"]]

    line = topology.get("line") if isinstance(topology.get("line"), dict) else {}
    lines = line.get("lines") if isinstance(line.get("lines"), list) else []
    for ln in lines:
        if not isinstance(ln, dict):
            continue
        line_id = str(ln.get("id", ""))
        if not line_id:
            continue
        state["lineIds"].append(line_id)
        chosen: list[str] = []
        orders = ln.get("orders") if isinstance(ln.get("orders"), list) else []
        for order in orders:
            if not isinstance(order, dict):
                continue
            if order.get("phase") == "initial" and isinstance(order.get("slots"), list) and order["slots"]:
                chosen = [str(x) for x in order["slots"]]
                break
        if not chosen:
            chosen = _first_non_empty_slots(orders)
        state["lineOrders"][line_id] = chosen

    twolines = topology.get("twoLines") if isinstance(topology.get("twoLines"), dict) else {}
    t_lines = twolines.get("lines") if isinstance(twolines.get("lines"), list) else []
    for row in t_lines:
        if not isinstance(row, dict):
            continue
        line_id = str(row.get("id", ""))
        if not line_id:
            continue
        state["twoLinesLineIds"].append(line_id)
        state["twoLinesOrders"][line_id] = _first_non_empty_slots(row.get("orders"))

    state["twoLinesOpposites"] = twolines.get("opposites") if isinstance(twolines.get("opposites"), list) else []
    state["twoLinesNeighbors"] = twolines.get("neighbors") if isinstance(twolines.get("neighbors"), list) else []

    return state


def build_events(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    figures = payload.get("figures") if isinstance(payload.get("figures"), list) else []
    events: list[dict[str, Any]] = []
    t = 0

    for figure in figures:
        if not isinstance(figure, dict):
            continue
        steps = figure.get("steps") if isinstance(figure.get("steps"), list) else []
        for step in steps:
            if not isinstance(step, dict):
                continue
            t += _as_count(step.get("beats"))
            primitives = step.get("primitives") if isinstance(step.get("primitives"), list) else []
            for primitive in primitives:
                if not isinstance(primitive, dict):
                    continue
                events.append(
                    {
                        "t": t,
                        "kind": str(primitive.get("kind", "")),
                        "a": str(primitive.get("a", "")),
                        "b": str(primitive.get("b", "")),
                        "delta": str(primitive.get("delta", "")),
                    }
                )
    return events, t


def _rotate_forward(items: list[str], delta: int) -> list[str]:
    if not items:
        return []
    n = len(items)
    shift = delta % n
    if shift < 0:
        shift += n
    if shift == 0:
        return items[:]
    return [items[(i + shift) % n] for i in range(n)]


def _swap_in_order(order: list[str], a: str, b: str) -> bool:
    try:
        ia = order.index(a)
        ib = order.index(b)
    except ValueError:
        return False
    if ia == ib:
        return False
    order[ia], order[ib] = order[ib], order[ia]
    return True


def _order_lists(state: dict[str, Any]) -> list[list[str]]:
    out: list[list[str]] = []
    if isinstance(state.get("circleOrder"), list):
        out.append(state["circleOrder"])
    for _, slots in sorted((state.get("lineOrders") or {}).items()):
        if isinstance(slots, list):
            out.append(slots)
    for _, slots in sorted((state.get("twoLinesOrders") or {}).items()):
        if isinstance(slots, list):
            out.append(slots)
    return out


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    kind = str(event.get("kind", "")).lower()

    if kind == "swapplaces":
        a = str(event.get("a", ""))
        b = str(event.get("b", ""))
        if not a or not b:
            return
        for order in _order_lists(state):
            if _swap_in_order(order, a, b):
                return
        return

    if kind == "progress":
        try:
            delta = int(str(event.get("delta", "0")))
        except ValueError:
            delta = 0
        line_orders = state.get("lineOrders") if isinstance(state.get("lineOrders"), dict) else {}
        for key in list(line_orders.keys()):
            slots = line_orders.get(key)
            if isinstance(slots, list):
                line_orders[key] = _rotate_forward(slots, delta)
        return

    if kind == "approach":
        state["twoLinesSeparation"] = int(state.get("twoLinesSeparation", 0)) - 1
        return

    if kind == "retreat":
        state["twoLinesSeparation"] = int(state.get("twoLinesSeparation", 0)) + 1


def snapshot_state(state: dict[str, Any], t: int) -> dict[str, Any]:
    return {
        "t": t,
        "circleOrder": list(state.get("circleOrder") or []),
        "lineOrders": {k: list(v) for k, v in sorted((state.get("lineOrders") or {}).items())},
        "twoLinesOrders": {k: list(v) for k, v in sorted((state.get("twoLinesOrders") or {}).items())},
        "twoLinesSeparation": int(state.get("twoLinesSeparation", 0)),
    }


def trace_from_payload(payload: dict[str, Any], source: str) -> dict[str, Any]:
    base = build_base_state(payload)
    events, total = build_events(payload)

    snapshots: list[dict[str, Any]] = []
    for t in range(0, total + 1):
        state = json.loads(json.dumps(base))
        for event in events:
            if int(event.get("t", 0)) <= t:
                apply_event(state, event)
            else:
                break
        snapshots.append(snapshot_state(state, t))

    hash_payload = {
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
    parser = argparse.ArgumentParser(description="Generate deterministic animation trace hash")
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
