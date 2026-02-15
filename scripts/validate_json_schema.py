#!/usr/bin/env python3
"""Validate a JSON instance against a JSON Schema file."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def _json_pointer(parts: list[Any]) -> str:
    if not parts:
        return "/"
    out: list[str] = []
    for p in parts:
        s = str(p).replace("~", "~0").replace("/", "~1")
        out.append(s)
    return "/" + "/".join(out)


def _fallback_validate_export_json(instance: Any) -> list[str]:
    """Fallback validator for schema/export-json.schema.json when jsonschema is unavailable."""
    errs: list[str] = []

    def expect_type(path: str, val: Any, kind: type) -> bool:
      if not isinstance(val, kind):
        errs.append(f"{path}: expected {kind.__name__}, got {type(val).__name__}")
        return False
      return True

    def expect_keys(path: str, obj: dict[str, Any], required: list[str], allow_extra: bool = False) -> None:
      missing = [k for k in required if k not in obj]
      if missing:
        errs.append(f"{path}: missing required keys {missing}")
      if not allow_extra:
        extra = [k for k in obj.keys() if k not in required]
        if extra:
          errs.append(f"{path}: unexpected keys {extra}")

    def validate_payload(path: str, payload: Any) -> None:
      if not expect_type(path, payload, dict):
        return
      req = ["file", "meta", "figures", "topology"]
      expect_keys(path, payload, req)
      if "file" in payload and not isinstance(payload["file"], str):
        errs.append(f"{path}/file: expected str")
      if "meta" in payload:
        validate_meta(f"{path}/meta", payload["meta"])
      if "figures" in payload:
        validate_figures(f"{path}/figures", payload["figures"])
      if "topology" in payload:
        validate_topology(f"{path}/topology", payload["topology"])

    def validate_meta(path: str, meta: Any) -> None:
      if not expect_type(path, meta, dict):
        return
      req = ["version", "title", "meter", "tempoBpm", "originCountry", "typeGenre", "formationText", "formationKind"]
      expect_keys(path, meta, req)
      for k in req:
        if k in meta and not isinstance(meta[k], str):
          errs.append(f"{path}/{k}: expected str")

    def validate_figures(path: str, figures: Any) -> None:
      if not expect_type(path, figures, list):
        return
      for i, fig in enumerate(figures):
        fp = f"{path}/{i}"
        if not expect_type(fp, fig, dict):
          continue
        req = ["id", "name", "steps"]
        expect_keys(fp, fig, req)
        for k in ("id", "name"):
          if k in fig and not isinstance(fig[k], str):
            errs.append(f"{fp}/{k}: expected str")
        if "steps" in fig:
          validate_steps(f"{fp}/steps", fig["steps"])

    def validate_steps(path: str, steps: Any) -> None:
      if not expect_type(path, steps, list):
        return
      req = ["who", "action", "beats", "count", "direction", "facing", "startFoot", "endFoot", "text", "primitives"]
      for i, step in enumerate(steps):
        sp = f"{path}/{i}"
        if not expect_type(sp, step, dict):
          continue
        expect_keys(sp, step, req)
        for k in req:
          if k == "primitives":
            continue
          if k in step and not isinstance(step[k], str):
            errs.append(f"{sp}/{k}: expected str")
        if "primitives" in step:
          validate_primitives(f"{sp}/primitives", step["primitives"])

    def validate_primitives(path: str, primitives: Any) -> None:
      if not expect_type(path, primitives, list):
        return
      req = ["kind", "who", "frame", "dir", "a", "b", "delta"]
      for i, prim in enumerate(primitives):
        pp = f"{path}/{i}"
        if not expect_type(pp, prim, dict):
          continue
        allow = req + ["preserveOrder"]
        expect_keys(pp, prim, allow, allow_extra=False)
        for k in req:
          if k in prim and not isinstance(prim[k], str):
            errs.append(f"{pp}/{k}: expected str")
        if "preserveOrder" in prim and not isinstance(prim["preserveOrder"], str):
          errs.append(f"{pp}/preserveOrder: expected str")

    def validate_slots(path: str, slots: Any) -> None:
      if not expect_type(path, slots, list):
        return
      for i, who in enumerate(slots):
        if not isinstance(who, str):
          errs.append(f"{path}/{i}: expected str")

    def validate_topology(path: str, topology: Any) -> None:
      if not expect_type(path, topology, dict):
        return
      req = ["circle", "line", "twoLines"]
      expect_keys(path, topology, req)
      if "circle" in topology:
        c = topology["circle"]
        if expect_type(f"{path}/circle", c, dict):
          expect_keys(f"{path}/circle", c, ["orders"])
          orders = c.get("orders")
          if expect_type(f"{path}/circle/orders", orders, list):
            for i, order in enumerate(orders):
              op = f"{path}/circle/orders/{i}"
              if expect_type(op, order, dict):
                expect_keys(op, order, ["role", "slots"])
                if "role" in order and not isinstance(order["role"], str):
                  errs.append(f"{op}/role: expected str")
                if "slots" in order:
                  validate_slots(f"{op}/slots", order["slots"])
      if "line" in topology:
        l = topology["line"]
        if expect_type(f"{path}/line", l, dict):
          expect_keys(f"{path}/line", l, ["lines"])
          lines = l.get("lines")
          if expect_type(f"{path}/line/lines", lines, list):
            for i, line in enumerate(lines):
              lp = f"{path}/line/lines/{i}"
              if expect_type(lp, line, dict):
                expect_keys(lp, line, ["id", "orders"])
                if "id" in line and not isinstance(line["id"], str):
                  errs.append(f"{lp}/id: expected str")
                orders = line.get("orders")
                if expect_type(f"{lp}/orders", orders, list):
                  for j, order in enumerate(orders):
                    op = f"{lp}/orders/{j}"
                    if expect_type(op, order, dict):
                      expect_keys(op, order, ["phase", "slots"])
                      if "phase" in order and not isinstance(order["phase"], str):
                        errs.append(f"{op}/phase: expected str")
                      if "slots" in order:
                        validate_slots(f"{op}/slots", order["slots"])
      if "twoLines" in topology:
        t = topology["twoLines"]
        if expect_type(f"{path}/twoLines", t, dict):
          expect_keys(f"{path}/twoLines", t, ["lines", "facing", "opposites", "neighbors"])
          lines = t.get("lines")
          if expect_type(f"{path}/twoLines/lines", lines, list):
            for i, line in enumerate(lines):
              lp = f"{path}/twoLines/lines/{i}"
              if expect_type(lp, line, dict):
                expect_keys(lp, line, ["id", "role", "orders"])
                for k in ("id", "role"):
                  if k in line and not isinstance(line[k], str):
                    errs.append(f"{lp}/{k}: expected str")
                orders = line.get("orders")
                if expect_type(f"{lp}/orders", orders, list):
                  for j, order in enumerate(orders):
                    op = f"{lp}/orders/{j}"
                    if expect_type(op, order, dict):
                      expect_keys(op, order, ["slots"])
                      if "slots" in order:
                        validate_slots(f"{op}/slots", order["slots"])
          facing = t.get("facing")
          if expect_type(f"{path}/twoLines/facing", facing, dict):
            expect_keys(f"{path}/twoLines/facing", facing, ["a", "b"])
            for k in ("a", "b"):
              if k in facing and not isinstance(facing[k], str):
                errs.append(f"{path}/twoLines/facing/{k}: expected str")
          for list_name, req in (("opposites", ["a", "b"]), ("neighbors", ["line", "a", "b"])):
            vals = t.get(list_name)
            if expect_type(f"{path}/twoLines/{list_name}", vals, list):
              for i, obj in enumerate(vals):
                op = f"{path}/twoLines/{list_name}/{i}"
                if expect_type(op, obj, dict):
                  expect_keys(op, obj, req)
                  for k in req:
                    if k in obj and not isinstance(obj[k], str):
                      errs.append(f"{op}/{k}: expected str")

    if isinstance(instance, list):
      for i, obj in enumerate(instance):
        validate_payload(f"/{i}", obj)
    else:
      validate_payload("/", instance)
    return errs


def _fallback_validate_provenance(instance: Any) -> list[str]:
    """Fallback validator for schema/provenance.schema.json when jsonschema is unavailable."""
    errs: list[str] = []

    def expect_type(path: str, val: Any, kind: type) -> bool:
      if not isinstance(val, kind):
        errs.append(f"{path}: expected {kind.__name__}, got {type(val).__name__}")
        return False
      return True

    def expect_keys(path: str, obj: dict[str, Any], required: list[str], optional: list[str] | None = None) -> None:
      optional = optional or []
      missing = [k for k in required if k not in obj]
      if missing:
        errs.append(f"{path}: missing required keys {missing}")
      allow = set(required + optional)
      extra = [k for k in obj.keys() if k not in allow]
      if extra:
        errs.append(f"{path}: unexpected keys {extra}")

    if not expect_type("/", instance, dict):
      return errs

    expect_keys("/", instance, ["sourcePath", "sourceSha256", "steps"], ["generatedAt"])
    if "sourcePath" in instance and not isinstance(instance["sourcePath"], str):
      errs.append("/sourcePath: expected str")
    if "sourceSha256" in instance:
      if not isinstance(instance["sourceSha256"], str):
        errs.append("/sourceSha256: expected str")
      elif re.fullmatch(r"[0-9a-f]{64}", instance["sourceSha256"]) is None:
        errs.append("/sourceSha256: expected 64 lowercase hex chars")
    if "generatedAt" in instance and not isinstance(instance["generatedAt"], str):
      errs.append("/generatedAt: expected str")

    steps = instance.get("steps")
    if not expect_type("/steps", steps, list):
      return errs

    for i, step in enumerate(steps):
      sp = f"/steps/{i}"
      if not expect_type(sp, step, dict):
        continue
      expect_keys(sp, step, ["figureId", "stepIndex", "action", "beats", "sourceSpan", "sourceSnippet"])
      if "figureId" in step and not isinstance(step["figureId"], str):
        errs.append(f"{sp}/figureId: expected str")
      if "stepIndex" in step:
        if not isinstance(step["stepIndex"], int):
          errs.append(f"{sp}/stepIndex: expected int")
        elif step["stepIndex"] < 1:
          errs.append(f"{sp}/stepIndex: expected >= 1")
      if "action" in step and not isinstance(step["action"], str):
        errs.append(f"{sp}/action: expected str")
      if "beats" in step:
        if not isinstance(step["beats"], int):
          errs.append(f"{sp}/beats: expected int")
        elif step["beats"] < 1:
          errs.append(f"{sp}/beats: expected >= 1")
      if "sourceSnippet" in step and not isinstance(step["sourceSnippet"], str):
        errs.append(f"{sp}/sourceSnippet: expected str")
      if "sourceSpan" in step:
        ss = step["sourceSpan"]
        if expect_type(f"{sp}/sourceSpan", ss, dict):
          expect_keys(f"{sp}/sourceSpan", ss, ["start", "end"])
          if "start" in ss:
            if not isinstance(ss["start"], int):
              errs.append(f"{sp}/sourceSpan/start: expected int")
            elif ss["start"] < 0:
              errs.append(f"{sp}/sourceSpan/start: expected >= 0")
          if "end" in ss:
            if not isinstance(ss["end"], int):
              errs.append(f"{sp}/sourceSpan/end: expected int")
            elif ss["end"] < 0:
              errs.append(f"{sp}/sourceSpan/end: expected >= 0")
    return errs


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_json_schema.py <schema.json> <instance.json>")
        return 2

    schema_path = Path(sys.argv[1])
    instance_path = Path(sys.argv[2])
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(instance_path.read_text(encoding="utf-8"))

    try:
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        if errors:
            print(f"FAIL: {instance_path} violates {schema_path}")
            for e in errors:
                ptr = _json_pointer(list(e.absolute_path))
                print(f"  - {ptr}: {e.message}")
            return 1
        print(f"OK: {instance_path} matches {schema_path}")
        return 0
    except ModuleNotFoundError:
        # Minimal fallback for environments without jsonschema.
        if schema_path.name == "export-json.schema.json":
            errors = _fallback_validate_export_json(instance)
            label = "fallback export-json checks"
        elif schema_path.name == "provenance.schema.json":
            errors = _fallback_validate_provenance(instance)
            label = "fallback provenance checks"
        else:
            errors = [f"unsupported fallback schema: {schema_path.name}"]
            label = "fallback checks"
        if errors:
            print(f"FAIL: {instance_path} violates {label}")
            for e in errors:
                print(f"  - {e}")
            return 1
        print(f"OK: {instance_path} matches {label}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
