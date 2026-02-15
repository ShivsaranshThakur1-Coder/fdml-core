#!/usr/bin/env python3
"""Build a deterministic 2D animation trace hash for line/twoLinesFacing formations."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def as_count(beats: Any) -> int:
    try:
        n = float(beats)
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    return int(round(n))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


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


def first_order_slots(orders: Any, prefer_phase: str | None = None) -> list[str]:
    if not isinstance(orders, list):
        return []
    if prefer_phase:
        for order in orders:
            if not isinstance(order, dict):
                continue
            phase = str(order.get("phase", "")).lower()
            slots = order.get("slots")
            if phase == prefer_phase and isinstance(slots, list) and slots:
                return [str(x) for x in slots if str(x)]
    for order in orders:
        if not isinstance(order, dict):
            continue
        slots = order.get("slots")
        if isinstance(slots, list) and slots:
            return [str(x) for x in slots if str(x)]
    return []


def line_slot_anchors(count: int) -> list[dict[str, float]]:
    if count <= 0:
        return []
    if count == 1:
        return [{"x": 0.0, "y": 0.0}]
    out: list[dict[str, float]] = []
    for i in range(count):
        out.append({"x": -1.0 + (2.0 * i) / (count - 1), "y": 0.0})
    return out


def two_line_slot_anchors(count_top: int, count_bottom: int, sep: float) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    top: list[dict[str, float]] = []
    bottom: list[dict[str, float]] = []
    if count_top == 1:
        top.append({"x": 0.0, "y": sep})
    elif count_top > 1:
        for i in range(count_top):
            top.append({"x": -1.0 + (2.0 * i) / (count_top - 1), "y": sep})

    if count_bottom == 1:
        bottom.append({"x": 0.0, "y": -sep})
    elif count_bottom > 1:
        for i in range(count_bottom):
            bottom.append({"x": -1.0 + (2.0 * i) / (count_bottom - 1), "y": -sep})

    return top, bottom


def sort_unique(xs: list[str]) -> list[str]:
    return sorted({x for x in xs if x})


def build_initial_state(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    topology = payload.get("topology") if isinstance(payload.get("topology"), dict) else {}
    formation_kind = str(meta.get("formationKind", ""))

    state: dict[str, Any] = {
        "formationKind": formation_kind,
        "ids": [],
        "positions": {},
        "separation": 0.8,
        "line": {"lineId": "", "order": []},
        "twoLines": {"topId": "", "bottomId": "", "orders": {}},
    }

    if formation_kind == "line":
        lines = topology.get("line", {}).get("lines") if isinstance(topology.get("line"), dict) else []
        if isinstance(lines, list) and lines:
            first = lines[0] if isinstance(lines[0], dict) else {}
            state["line"]["lineId"] = str(first.get("id", "line"))
            state["line"]["order"] = first_order_slots(first.get("orders"), "initial")
        assign_positions_from_structure(state)
        return state

    if formation_kind == "twoLinesFacing":
        two = topology.get("twoLines") if isinstance(topology.get("twoLines"), dict) else {}
        lines = two.get("lines") if isinstance(two.get("lines"), list) else []
        facing = two.get("facing") if isinstance(two.get("facing"), dict) else {}

        top_id = str(facing.get("a", ""))
        bottom_id = str(facing.get("b", ""))

        if not top_id and lines:
            top_id = str((lines[0] or {}).get("id", ""))
        if not bottom_id and len(lines) > 1:
            bottom_id = str((lines[1] or {}).get("id", ""))

        state["twoLines"]["topId"] = top_id
        state["twoLines"]["bottomId"] = bottom_id

        for line in lines:
            if not isinstance(line, dict):
                continue
            lid = str(line.get("id", ""))
            if not lid:
                continue
            state["twoLines"]["orders"][lid] = first_order_slots(line.get("orders"), "initial")

        assign_positions_from_structure(state)

    return state


def assign_positions_from_structure(state: dict[str, Any]) -> None:
    state["positions"] = {}

    if state.get("formationKind") == "line":
        order = state.get("line", {}).get("order")
        order = order if isinstance(order, list) else []
        anchors = line_slot_anchors(len(order))
        for idx, dancer_id in enumerate(order):
            state["positions"][dancer_id] = {"x": anchors[idx]["x"], "y": anchors[idx]["y"]}
        state["ids"] = sort_unique(order)
        return

    if state.get("formationKind") == "twoLinesFacing":
        tl = state.get("twoLines", {}) if isinstance(state.get("twoLines"), dict) else {}
        top_id = str(tl.get("topId", ""))
        bottom_id = str(tl.get("bottomId", ""))
        orders = tl.get("orders", {}) if isinstance(tl.get("orders"), dict) else {}

        top_order = orders.get(top_id, []) if isinstance(orders.get(top_id, []), list) else []
        bottom_order = orders.get(bottom_id, []) if isinstance(orders.get(bottom_id, []), list) else []

        top_anchors, bottom_anchors = two_line_slot_anchors(len(top_order), len(bottom_order), float(state.get("separation", 0.8)))

        for idx, dancer_id in enumerate(top_order):
            state["positions"][dancer_id] = {"x": top_anchors[idx]["x"], "y": top_anchors[idx]["y"]}
        for idx, dancer_id in enumerate(bottom_order):
            state["positions"][dancer_id] = {"x": bottom_anchors[idx]["x"], "y": bottom_anchors[idx]["y"]}

        state["ids"] = sort_unique(top_order + bottom_order)


def split_who(who: Any) -> list[str]:
    raw = str(who or "").strip()
    if not raw:
        return []
    tokens = [tok for tok in __import__("re").split(r"[\s,|/]+", raw) if tok]
    return tokens


def resolve_who_targets(who: Any, state: dict[str, Any]) -> list[str]:
    ids = state.get("ids", []) if isinstance(state.get("ids"), list) else []
    tokens = split_who(who)
    if not tokens:
        return []
    if len(tokens) == 1 and tokens[0] == "all":
        return ids[:]
    s = set(ids)
    return [t for t in tokens if t in s]


def dir_to_delta_x(direction: Any) -> float:
    d = str(direction or "").lower()
    if d in ("left", "counterclockwise", "ccw", "west"):
        return -0.14
    if d in ("right", "clockwise", "cw", "east"):
        return 0.14
    return 0.0


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    kind = str(event.get("kind", "")).lower()

    if kind == "approach":
        state["separation"] = clamp(float(state.get("separation", 0.8)) - 0.1, 0.25, 1.4)
        if state.get("formationKind") == "twoLinesFacing":
            assign_positions_from_structure(state)
        return

    if kind == "retreat":
        state["separation"] = clamp(float(state.get("separation", 0.8)) + 0.1, 0.25, 1.4)
        if state.get("formationKind") == "twoLinesFacing":
            assign_positions_from_structure(state)
        return

    if kind == "progress":
        try:
            delta = int(str(event.get("delta", "0")))
        except ValueError:
            delta = 0

        if state.get("formationKind") == "line":
            order = state.get("line", {}).get("order")
            if isinstance(order, list):
                state["line"]["order"] = rotate_forward(order, delta)
                assign_positions_from_structure(state)
        elif state.get("formationKind") == "twoLinesFacing":
            orders = state.get("twoLines", {}).get("orders")
            if isinstance(orders, dict):
                for key in list(orders.keys()):
                    if isinstance(orders[key], list):
                        orders[key] = rotate_forward(orders[key], delta)
                assign_positions_from_structure(state)
        return

    if kind == "swapplaces":
        a = str(event.get("a", ""))
        b = str(event.get("b", ""))
        if not a or not b:
            return

        swapped_in_order = False
        if state.get("formationKind") == "line":
            order = state.get("line", {}).get("order")
            if isinstance(order, list):
                swapped_in_order = swap_in_order(order, a, b)
        elif state.get("formationKind") == "twoLinesFacing":
            orders = state.get("twoLines", {}).get("orders")
            if isinstance(orders, dict):
                for key in sorted(orders.keys()):
                    if isinstance(orders[key], list) and swap_in_order(orders[key], a, b):
                        swapped_in_order = True
                        break

        if swapped_in_order:
            assign_positions_from_structure(state)
            return

        pa = state.get("positions", {}).get(a)
        pb = state.get("positions", {}).get(b)
        if isinstance(pa, dict) and isinstance(pb, dict):
            state["positions"][a], state["positions"][b] = pb, pa
        return

    if kind == "move":
        if str(event.get("frame", "")) != "formation":
            return
        dx = dir_to_delta_x(event.get("dir"))
        if abs(dx) < 1e-9:
            return
        targets = resolve_who_targets(event.get("who"), state)
        for dancer_id in targets:
            pos = state.get("positions", {}).get(dancer_id)
            if isinstance(pos, dict):
                pos["x"] = clamp(float(pos.get("x", 0.0)) + dx, -1.2, 1.2)


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
                        "delta": str(primitive.get("delta", "")),
                    }
                )
    return events, total


def r6(value: float) -> float:
    return float(f"{value:.6f}")


def snapshot_state(state: dict[str, Any], t: int) -> dict[str, Any]:
    positions = state.get("positions", {}) if isinstance(state.get("positions"), dict) else {}
    ids = sorted(positions.keys())
    snap_positions: dict[str, dict[str, float]] = {}
    for dancer_id in ids:
        p = positions[dancer_id]
        if not isinstance(p, dict):
            continue
        snap_positions[dancer_id] = {
            "x": r6(float(p.get("x", 0.0))),
            "y": r6(float(p.get("y", 0.0))),
        }
    return {
        "t": t,
        "formationKind": str(state.get("formationKind", "")),
        "separation": r6(float(state.get("separation", 0.0))),
        "positions": snap_positions,
    }


def trace_from_payload(payload: dict[str, Any], source: str) -> dict[str, Any]:
    base = build_initial_state(payload)
    events, total = build_events(payload)

    snapshots: list[dict[str, Any]] = []
    state = json.loads(json.dumps(base))
    snapshots.append(snapshot_state(state, 0))

    idx = 0
    for t in range(1, total + 1):
        while idx < len(events) and int(events[idx].get("t", 0)) <= t:
            apply_event(state, events[idx])
            idx += 1
        snapshots.append(snapshot_state(state, t))

    hash_payload = {
        "formationKind": base.get("formationKind", ""),
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
    parser = argparse.ArgumentParser(description="Generate deterministic 2D animation trace hash")
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
