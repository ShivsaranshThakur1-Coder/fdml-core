#!/usr/bin/env python3
"""Promote accepted M10 ontology candidates into unified FDML contract artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

XS_NS = {"xs": "http://www.w3.org/2001/XMLSchema"}

FORMATION_VALUE_NORMALIZATION = {
    "twolinesfacing": "twoLinesFacing",
}

CONTRACT_FIELD_TEMPLATES: dict[str, dict[str, Any]] = {
    "meta.meter.value": {
        "path": "/fdml/meta/meter/@value",
        "group": "timing",
        "type": "string",
        "cardinality": "0..1 (required for quality workflow)",
        "requiredForV12": True,
        "description": "Declared meter signature used by timing and phrase alignment validators.",
        "chosenOption": "Promote meter as canonical timing anchor across all corpus examples.",
        "alternativesConsidered": [
            "Infer timing only from step beat counts.",
            "Keep meter as free-form optional metadata with no validator dependence.",
        ],
        "tradeoffs": [
            "Pros: deterministic timing validation and reproducible bar alignment checks.",
            "Cons: low-quality inputs may require normalization to valid meter strings.",
        ],
        "reversalCondition": "If more than 5% of corpus files cannot be normalized to meter syntax, relax requirement and treat timing as advisory only.",
    },
    "meta.geometry.formation.kind": {
        "path": "/fdml/meta/geometry/formation/@kind",
        "group": "formation",
        "type": "enum",
        "cardinality": "1 for v1.2 profiles",
        "requiredForV12": True,
        "description": "Canonical formation family used by geometry semantics and topology checks.",
        "chosenOption": "Promote formation kind as required contract field for v1.2 documents.",
        "alternativesConsidered": [
            "Use only legacy meta/formation/@text and infer kind heuristically.",
            "Allow per-subset formation vocabularies.",
        ],
        "tradeoffs": [
            "Pros: one shared field enables a single validator stack across full corpus.",
            "Cons: uncommon regional formations require controlled extension process.",
        ],
        "reversalCondition": "If accepted corpus growth repeatedly introduces unsupported formation families, add new enum values in a versioned schema revision.",
    },
    "meta.geometry.roles.role.id": {
        "path": "/fdml/meta/geometry/roles/role/@id",
        "group": "roles",
        "type": "string[]",
        "cardinality": "0..n (required when step/geo references roles)",
        "requiredForV12": False,
        "description": "Declared role inventory referenced by step/@who and primitive participant attributes.",
        "chosenOption": "Promote role id inventory as canonical participant contract.",
        "alternativesConsidered": [
            "Rely only on free-text who labels inside steps.",
            "Hard-code role sets per formation subtype.",
        ],
        "tradeoffs": [
            "Pros: explicit role registry enables cross-file consistency and deterministic reference checks.",
            "Cons: source narratives with vague performer labels need normalization.",
        ],
        "reversalCondition": "If role normalization fails for more than 5% of files, allow provisional role namespaces and defer strict enforcement.",
    },
    "step.geo.primitive.kind": {
        "path": "/fdml/body//figure//step/geo/primitive/@kind",
        "group": "movement",
        "type": "enum",
        "cardinality": "1 per primitive",
        "requiredForV12": True,
        "description": "Primitive motion semantics used by geometry/logical validators.",
        "chosenOption": "Promote primitive kind as canonical action semantic anchor.",
        "alternativesConsidered": [
            "Treat primitive kind as optional and infer from action prose.",
            "Split primitive vocabularies by formation category.",
        ],
        "tradeoffs": [
            "Pros: explicit primitive semantics supports deterministic macro-rule validation.",
            "Cons: enum governance is needed as new motion patterns are discovered.",
        ],
        "reversalCondition": "If unresolved primitive concepts exceed 10% of newly ingested files, add controlled enum extensions in the next contract revision.",
    },
    "meta.origin.country": {
        "path": "/fdml/meta/origin/@country",
        "group": "context",
        "type": "string",
        "cardinality": "1",
        "requiredForV12": True,
        "description": "Country context anchor for culture-aware interpretation.",
        "chosenOption": "Promote origin country as mandatory context anchor.",
        "alternativesConsidered": [
            "Leave cultural context in free-text section notes only.",
            "Store country in external sidecar metadata.",
        ],
        "tradeoffs": [
            "Pros: deterministic regional filtering and evaluation coverage.",
            "Cons: some sources require fallback placeholders when specific country is unknown.",
        ],
        "reversalCondition": "If provenance policy requires source-only context values, move fallback placeholders to preprocessing only.",
    },
    "meta.origin.region": {
        "path": "/fdml/meta/origin/@region",
        "group": "context",
        "type": "string",
        "cardinality": "0..1",
        "requiredForV12": True,
        "description": "Sub-country region context for finer-grained folk taxonomy.",
        "chosenOption": "Promote origin region into canonical context contract.",
        "alternativesConsidered": [
            "Infer region from style labels.",
            "Drop region-level context from contract fields.",
        ],
        "tradeoffs": [
            "Pros: improves regional granularity for downstream analysis.",
            "Cons: some corpora only provide broad geographic labels.",
        ],
        "reversalCondition": "If region precision remains unavailable for most files, demote strictness while retaining field support.",
    },
    "meta.type.genre": {
        "path": "/fdml/meta/type/@genre",
        "group": "context",
        "type": "string",
        "cardinality": "1",
        "requiredForV12": True,
        "description": "Genre class used for broad dance-family grouping.",
        "chosenOption": "Promote genre as required dance-type classifier.",
        "alternativesConsidered": [
            "Encode genre only in tags.",
            "Infer genre from formation and step patterns.",
        ],
        "tradeoffs": [
            "Pros: explicit type labeling enables deterministic filtering.",
            "Cons: generic genre values may need iterative refinement.",
        ],
        "reversalCondition": "If genre labels cause systematic ambiguity, split into controlled enum profiles.",
    },
    "meta.type.style": {
        "path": "/fdml/meta/type/@style",
        "group": "context",
        "type": "string",
        "cardinality": "1",
        "requiredForV12": True,
        "description": "Style identifier for dance-specific nuance routing.",
        "chosenOption": "Promote style as canonical per-dance context key.",
        "alternativesConsidered": [
            "Reuse only title or source identifiers.",
            "Drop style from contract to keep schema minimal.",
        ],
        "tradeoffs": [
            "Pros: deterministic style axis supports corpus diversity analysis.",
            "Cons: style strings require normalization policy.",
        ],
        "reversalCondition": "If style variance becomes unbounded, enforce namespace conventions per source family.",
    },
    "meta.tempo.bpm": {
        "path": "/fdml/meta/tempo/@bpm",
        "group": "timing",
        "type": "integer",
        "cardinality": "1",
        "requiredForV12": True,
        "description": "Tempo declaration used for pacing and dynamics checks.",
        "chosenOption": "Promote BPM as required timing metadata.",
        "alternativesConsidered": [
            "Derive tempo only from textual notes.",
            "Treat tempo as optional for non-performance corpora.",
        ],
        "tradeoffs": [
            "Pros: deterministic pace context improves comparability.",
            "Cons: approximate BPM values may be needed for legacy prose sources.",
        ],
        "reversalCondition": "If tempo extraction quality drops below acceptance thresholds, allow advisory BPM with explicit confidence flags.",
    },
    "step.direction": {
        "path": "/fdml/body//figure//step/@direction",
        "group": "movement",
        "type": "string",
        "cardinality": "1 per step",
        "requiredForV12": True,
        "description": "Directional intent for each step.",
        "chosenOption": "Promote step direction as mandatory step-level semantic.",
        "alternativesConsidered": [
            "Infer direction from action prose only.",
            "Represent direction only in geo primitive dir/frame fields.",
        ],
        "tradeoffs": [
            "Pros: immediate per-step orientation coverage in one contract field.",
            "Cons: source ambiguity may require deterministic defaults.",
        ],
        "reversalCondition": "If direction defaults prove misleading in evaluations, migrate to explicit uncertainty labels.",
    },
    "step.facing": {
        "path": "/fdml/body//figure//step/@facing",
        "group": "movement",
        "type": "string",
        "cardinality": "1 per step",
        "requiredForV12": True,
        "description": "Facing target for each step.",
        "chosenOption": "Promote step facing as mandatory step-level semantic.",
        "alternativesConsidered": [
            "Infer facing from partner or formation context.",
            "Store facing only in prose notes.",
        ],
        "tradeoffs": [
            "Pros: deterministic orientation checks across full corpus.",
            "Cons: defaults can reduce stylistic precision.",
        ],
        "reversalCondition": "If facing precision is insufficient, add confidence tiers per step.",
    },
    "step.beats": {
        "path": "/fdml/body//figure//step/@beats",
        "group": "timing",
        "type": "integer",
        "cardinality": "1 per step",
        "requiredForV12": True,
        "description": "Beat duration per step used by meter alignment checks.",
        "chosenOption": "Promote step beats as required timing primitive.",
        "alternativesConsidered": [
            "Infer beats from phrase text only.",
            "Represent timing only at section level.",
        ],
        "tradeoffs": [
            "Pros: deterministic timing math at step granularity.",
            "Cons: simplified beats can hide expressive timing nuance.",
        ],
        "reversalCondition": "If expressive timing requires finer model, extend with optional subdivisions.",
    },
    "step.count": {
        "path": "/fdml/body//figure//step/@count",
        "group": "timing",
        "type": "string",
        "cardinality": "1 per step",
        "requiredForV12": True,
        "description": "Step count marker for sequence ordering and phrase indexing.",
        "chosenOption": "Promote count as required sequence token.",
        "alternativesConsidered": [
            "Rely on implicit XML step order only.",
            "Track count in external analysis reports.",
        ],
        "tradeoffs": [
            "Pros: explicit count supports deterministic cross-tool comparison.",
            "Cons: count strings may need normalization in mixed-notation sources.",
        ],
        "reversalCondition": "If count notation diverges heavily, move to normalized numeric plus display token fields.",
    },
    "meta.geometry.formation.womanSide": {
        "path": "/fdml/meta/geometry/formation/@womanSide",
        "group": "formation",
        "type": "enum",
        "cardinality": "0..1 (required for couple formation)",
        "requiredForV12": False,
        "description": "Couple-side orientation contract field.",
        "chosenOption": "Promote womanSide as canonical couple-orientation field.",
        "alternativesConsidered": [
            "Infer woman side from relpos primitives only.",
            "Leave side semantics to prose notes.",
        ],
        "tradeoffs": [
            "Pros: explicit side contract stabilizes couple validators.",
            "Cons: only applicable to couple subsets.",
        ],
        "reversalCondition": "If non-binary role models are introduced, replace with generalized partner-side schema.",
    },
    "body.geometry.couples.pair.relationship": {
        "path": "/fdml/body/geometry/couples/pair/@relationship",
        "group": "roles",
        "type": "string",
        "cardinality": "0..1 per pair",
        "requiredForV12": False,
        "description": "Declared relationship label for couple pair topology.",
        "chosenOption": "Promote couple relationship as explicit topology context.",
        "alternativesConsidered": [
            "Use only pair participant IDs without relation label.",
            "Infer relationship from formation and role IDs.",
        ],
        "tradeoffs": [
            "Pros: preserves relationship semantics explicitly for validators.",
            "Cons: relation labels can vary by source conventions.",
        ],
        "reversalCondition": "If relationship labels become noisy, enforce controlled vocabulary through schema extension.",
    },
    "meta.meter.rhythmPattern": {
        "path": "/fdml/meta/meter/@rhythmPattern",
        "group": "timing",
        "type": "string",
        "cardinality": "0..1",
        "requiredForV12": False,
        "description": "Optional rhythm grouping pattern for additive meter semantics.",
        "chosenOption": "Promote rhythmPattern as optional timing extension field.",
        "alternativesConsidered": [
            "Store rhythm accents only in prose notes.",
            "Avoid rhythmPattern until source density increases.",
        ],
        "tradeoffs": [
            "Pros: clear extension path for richer rhythm modeling.",
            "Cons: sparse source coverage in current corpus.",
        ],
        "reversalCondition": "If rhythmPattern remains unused across releases, retire from required promotion workflows.",
    },
    "meta.geometry.hold.kind": {
        "path": "/fdml/meta/geometry/hold/@kind",
        "group": "formation",
        "type": "enum",
        "cardinality": "0..1",
        "requiredForV12": False,
        "description": "Optional hold/contact topology declaration.",
        "chosenOption": "Promote hold kind as optional relational extension field.",
        "alternativesConsidered": [
            "Infer hold semantics from prose action text.",
            "Model hold only in geo primitives.",
        ],
        "tradeoffs": [
            "Pros: direct support for contact-pattern validators when available.",
            "Cons: currently sparse in promoted corpus.",
        ],
        "reversalCondition": "If hold coverage remains low, keep field optional and defer strict checks.",
    },
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Promote accepted M10 ontology candidates into a unified FDML contract report."
    )
    ap.add_argument(
        "--candidates",
        default="out/m10_ontology_candidates.json",
        help="path to M10 ontology candidate report",
    )
    ap.add_argument(
        "--schema",
        default="schema/fdml.xsd",
        help="path to FDML schema used for contract support checks",
    )
    ap.add_argument(
        "--spec",
        default="docs/FDML-SPEC.md",
        help="path to FDML specification document",
    )
    ap.add_argument(
        "--report-out",
        default="out/m11_contract_promotion.json",
        help="output path for M11 contract promotion report",
    )
    ap.add_argument(
        "--label",
        default="m11-contract-promotion",
        help="report label",
    )
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.60,
        help="minimum candidate confidence in [0,1] for acceptance",
    )
    ap.add_argument(
        "--min-support-count",
        type=int,
        default=1,
        help="minimum support count for acceptance",
    )
    ap.add_argument(
        "--min-accepted",
        type=int,
        default=4,
        help="minimum accepted candidate rows required",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m11_contract_promotion.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def has_evidence(row: dict[str, Any]) -> bool:
    file_value = str(row.get("file") or "").strip()
    evidence = as_dict(row.get("evidence"))
    text = str(evidence.get("text") or "").strip()
    span = as_dict(evidence.get("span"))
    start = span.get("start")
    end = span.get("end")
    return bool(
        file_value
        and text
        and isinstance(start, int)
        and isinstance(end, int)
        and start >= 0
        and end >= start
    )


def parse_formation_value(key: str) -> str:
    raw = key.split(":", 1)[1].strip()
    return FORMATION_VALUE_NORMALIZATION.get(raw.lower(), raw)


def parse_primitive_value(key: str) -> str:
    return key.split(":", 1)[1].strip()


def candidate_field_id(key: str) -> str:
    if key.startswith("formation_kind:"):
        return "meta.geometry.formation.kind"
    if key.startswith("primitive_kind:"):
        return "step.geo.primitive.kind"
    if key == "roles:role_ids":
        return "meta.geometry.roles.role.id"
    if key == "timing:meter_value":
        return "meta.meter.value"
    if key == "timing:rhythm_pattern":
        return "meta.meter.rhythmPattern"
    if key == "timing:tempo_bpm":
        return "meta.tempo.bpm"
    if key == "context:origin_country":
        return "meta.origin.country"
    if key == "context:origin_region":
        return "meta.origin.region"
    if key == "context:type_genre":
        return "meta.type.genre"
    if key == "context:type_style":
        return "meta.type.style"
    if key == "formation:hold_kind":
        return "meta.geometry.hold.kind"
    if key == "formation:woman_side":
        return "meta.geometry.formation.womanSide"
    if key == "step:direction":
        return "step.direction"
    if key == "step:facing":
        return "step.facing"
    if key == "step:beats":
        return "step.beats"
    if key == "step:count":
        return "step.count"
    if key == "couples:pair_relationship":
        return "body.geometry.couples.pair.relationship"
    return ""


def candidate_observed_value(key: str) -> str:
    if key.startswith("formation_kind:"):
        return parse_formation_value(key)
    if key.startswith("primitive_kind:"):
        return parse_primitive_value(key)
    return ""


def schema_support(schema_path: Path) -> dict[str, Any]:
    root = ET.parse(schema_path).getroot()

    def attr_exists(type_name: str, attr_name: str) -> bool:
        node = root.find(
            f"./xs:complexType[@name='{type_name}']/xs:attribute[@name='{attr_name}']",
            XS_NS,
        )
        return node is not None

    def enum_values(simple_type_name: str) -> list[str]:
        values = []
        for enum in root.findall(
            f"./xs:simpleType[@name='{simple_type_name}']/xs:restriction/xs:enumeration",
            XS_NS,
        ):
            value = str(enum.get("value") or "").strip()
            if value:
                values.append(value)
        return sorted(values)

    return {
        "meterValueAttribute": attr_exists("MeterType", "value"),
        "meterRhythmPatternAttribute": attr_exists("MeterType", "rhythmPattern"),
        "tempoBpmAttribute": attr_exists("TempoType", "bpm"),
        "originCountryAttribute": attr_exists("OriginType", "country"),
        "originRegionAttribute": attr_exists("OriginType", "region"),
        "typeGenreAttribute": attr_exists("TypeType", "genre"),
        "typeStyleAttribute": attr_exists("TypeType", "style"),
        "formationKindAttribute": attr_exists("GeoFormationType", "kind"),
        "formationWomanSideAttribute": attr_exists("GeoFormationType", "womanSide"),
        "holdKindAttribute": attr_exists("GeoHoldType", "kind"),
        "roleIdAttribute": attr_exists("GeoRoleType", "id"),
        "pairRelationshipAttribute": attr_exists("BodyPairType", "relationship"),
        "stepDirectionAttribute": attr_exists("StepType", "direction"),
        "stepFacingAttribute": attr_exists("StepType", "facing"),
        "stepBeatsAttribute": attr_exists("StepType", "beats"),
        "stepCountAttribute": attr_exists("StepType", "count"),
        "primitiveKindAttribute": attr_exists("GeoPrimitiveType", "kind"),
        "formationKindEnumValues": enum_values("GeoFormationKind"),
        "holdKindEnumValues": enum_values("GeoHoldKind"),
        "primitiveKindEnumValues": enum_values("GeoPrimitiveKind"),
    }


def build_field_aggregates(
    accepted_rows: list[dict[str, Any]], schema_info: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}

    for row in accepted_rows:
        key = str(row.get("key") or "").strip()
        field_id = candidate_field_id(key)
        if not field_id:
            continue
        template = CONTRACT_FIELD_TEMPLATES[field_id]
        item = grouped.get(field_id)
        if item is None:
            item = {
                "fieldId": field_id,
                "path": template["path"],
                "group": template["group"],
                "type": template["type"],
                "cardinality": template["cardinality"],
                "requiredForV12": template["requiredForV12"],
                "description": template["description"],
                "supportCountTotal": 0,
                "supportCountMax": 0,
                "candidateCount": 0,
                "confidenceRange": {"min": 1.0, "max": 0.0},
                "observedValues": [],
                "candidateKeys": [],
                "evidenceFiles": [],
            }
            grouped[field_id] = item

        support_count = as_int(row.get("supportCount"), 0)
        confidence = clamp01(as_float(row.get("confidence"), 0.0))
        value = candidate_observed_value(key)
        file_value = str(row.get("file") or "").strip()

        item["candidateCount"] = as_int(item.get("candidateCount"), 0) + 1
        item["supportCountTotal"] = as_int(item.get("supportCountTotal"), 0) + support_count
        item["supportCountMax"] = max(as_int(item.get("supportCountMax"), 0), support_count)
        conf_range = as_dict(item.get("confidenceRange"))
        conf_min = as_float(conf_range.get("min"), 1.0)
        conf_max = as_float(conf_range.get("max"), 0.0)
        item["confidenceRange"] = {
            "min": min(conf_min, confidence),
            "max": max(conf_max, confidence),
        }
        keys = set(as_list(item.get("candidateKeys")))
        keys.add(key)
        item["candidateKeys"] = sorted(keys)
        if value:
            values = set(as_list(item.get("observedValues")))
            values.add(value)
            item["observedValues"] = sorted(values)
        if file_value:
            files = set(as_list(item.get("evidenceFiles")))
            files.add(file_value)
            item["evidenceFiles"] = sorted(files)

    field_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    for field_id in sorted(grouped.keys()):
        item = grouped[field_id]
        template = CONTRACT_FIELD_TEMPLATES[field_id]
        if field_id == "meta.geometry.formation.kind":
            item["contractEnumValues"] = as_list(schema_info.get("formationKindEnumValues"))
        elif field_id == "step.geo.primitive.kind":
            item["contractEnumValues"] = as_list(schema_info.get("primitiveKindEnumValues"))

        field_rows.append(item)
        decision_rows.append(
            {
                "fieldId": field_id,
                "chosenOption": template["chosenOption"],
                "alternativesConsidered": template["alternativesConsidered"],
                "tradeoffs": template["tradeoffs"],
                "reversalCondition": template["reversalCondition"],
            }
        )

    return field_rows, decision_rows


def main() -> int:
    args = parse_args()

    if not (0.0 <= args.min_confidence <= 1.0):
        return fail("--min-confidence must be between 0 and 1")
    if args.min_support_count < 1:
        return fail("--min-support-count must be >= 1")
    if args.min_accepted < 1:
        return fail("--min-accepted must be >= 1")

    candidates_path = Path(args.candidates)
    schema_path = Path(args.schema)
    spec_path = Path(args.spec)
    report_out = Path(args.report_out)

    if not candidates_path.is_file():
        return fail(f"candidate report not found: {candidates_path}")
    if not schema_path.is_file():
        return fail(f"schema file not found: {schema_path}")
    if not spec_path.is_file():
        return fail(f"spec file not found: {spec_path}")

    payload = load_json(candidates_path)
    rows = [as_dict(x) for x in as_list(payload.get("rows"))]
    if not rows:
        return fail("candidate report has no rows")

    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    unknown_key_count = 0
    rejected_by_reason: dict[str, int] = {}

    for row in rows:
        key = str(row.get("key") or "").strip()
        confidence = clamp01(as_float(row.get("confidence"), 0.0))
        support_count = as_int(row.get("supportCount"), 0)
        reasons: list[str] = []

        if not key:
            reasons.append("missing_key")
        elif not candidate_field_id(key):
            reasons.append("unmapped_key")
            unknown_key_count += 1
        if support_count < args.min_support_count:
            reasons.append("support_count_below_threshold")
        if confidence < args.min_confidence:
            reasons.append("confidence_below_threshold")
        if not has_evidence(row):
            reasons.append("missing_evidence")

        if reasons:
            for reason in reasons:
                rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1
            rejected_rows.append(
                {
                    "key": key,
                    "name": str(row.get("name") or "").strip(),
                    "group": str(row.get("group") or "").strip(),
                    "confidence": confidence,
                    "supportCount": support_count,
                    "file": str(row.get("file") or "").strip(),
                    "reasons": reasons,
                }
            )
        else:
            accepted_rows.append(row)

    if len(accepted_rows) < args.min_accepted:
        return fail(
            f"accepted rows {len(accepted_rows)} below required minimum {args.min_accepted}"
        )

    schema_info = schema_support(schema_path)
    field_rows, decision_rows = build_field_aggregates(accepted_rows, schema_info)
    if not field_rows:
        return fail("no contract fields produced from accepted rows")

    promoted_field_ids = [str(x.get("fieldId") or "") for x in field_rows]
    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "ontologyCandidates": candidates_path.as_posix(),
            "schema": schema_path.as_posix(),
            "spec": spec_path.as_posix(),
        },
        "thresholds": {
            "minConfidence": args.min_confidence,
            "minSupportCount": args.min_support_count,
            "minAcceptedRows": args.min_accepted,
        },
        "totals": {
            "inputRows": len(rows),
            "acceptedRows": len(accepted_rows),
            "rejectedRows": len(rejected_rows),
            "promotedFields": len(field_rows),
            "unknownKeyCount": unknown_key_count,
        },
        "schemaSupport": schema_info,
        "promotedFieldIds": promoted_field_ids,
        "contractFields": field_rows,
        "decisionRegistry": decision_rows,
        "rejectedByReason": rejected_by_reason,
        "rejectedRows": sorted(rejected_rows, key=lambda x: str(x.get("key", ""))),
    }

    write_json(report_out, report)
    print(
        "M11 CONTRACT PROMOTION DONE "
        f"input={len(rows)} accepted={len(accepted_rows)} "
        f"fields={len(field_rows)} report={report_out.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
