package org.fdml.cli;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class DoctorExplain {
  private static final Pattern XSD_CODE = Pattern.compile(":\\s*([A-Za-z][A-Za-z0-9_.-]+)\\s*:");

  private static final Map<String, String> GUIDANCE = buildGuidance();

  private DoctorExplain() {}

  static Map<String, String> build(List<FdmlValidator.Result> rX,
                                   List<SchematronValidator.Result> rS,
                                   List<Linter.FileResult> rL,
                                   List<TimingValidator.FileResult> rT,
                                   List<GeometryValidator.Result> rG) {
    Set<String> codes = new TreeSet<>();

    for (FdmlValidator.Result r : rX) {
      if (!r.ok) codes.add(xsdCode(r.message));
    }
    for (SchematronValidator.Result r : rS) {
      if (!r.ok) {
        if (r.messages == null || r.messages.isEmpty()) {
          codes.add("schematron_failed_assert");
        } else {
          for (String msg : r.messages) codes.add(schematronCode(msg));
        }
      }
    }
    for (Linter.FileResult r : rL) for (Linter.Warning w : r.warnings) codes.add(w.code);
    for (TimingValidator.FileResult r : rT) for (TimingValidator.Issue i : r.issues) codes.add(i.code);
    for (GeometryValidator.Result r : rG) for (GeometryValidator.Issue i : r.issues) codes.add(i.code);

    Map<String, String> out = new TreeMap<>();
    for (String code : codes) out.put(code, guidanceFor(code));
    return out;
  }

  static String guidanceFor(String code) {
    if (code == null || code.isBlank()) return genericGuidance("");
    String g = GUIDANCE.get(code);
    if (g != null) return g;
    if (code.startsWith("sch_") || code.equals("schematron_failed_assert")) {
      return "Schematron assertion failed. See schematron/fdml.sch and the failed assertion text; then fix the referenced XML node(s).";
    }
    if (code.startsWith("xsd_")) {
      return "XSD validation failed. Use the reported line/column and check schema/fdml.xsd to correct structure or required attributes.";
    }
    return genericGuidance(code);
  }

  static String schematronCode(String message) {
    String norm = normalizeCodePart(message);
    return norm.isEmpty() ? "schematron_failed_assert" : ("sch_" + norm);
  }

  static String xsdCode(String message) {
    if (message == null || message.isBlank()) return "xsd_invalid";
    Matcher m = XSD_CODE.matcher(message);
    if (m.find()) {
      String code = normalizeCodePart(m.group(1));
      if (!code.isEmpty()) return "xsd_" + code;
    }
    return "xsd_invalid";
  }

  private static String normalizeCodePart(String value) {
    if (value == null) return "";
    String s = value.toLowerCase(Locale.ROOT).trim();
    if (s.isEmpty()) return "";
    s = s.replaceAll("[^a-z0-9]+", "_");
    s = s.replaceAll("^_+", "").replaceAll("_+$", "").replaceAll("_+", "_");
    return s;
  }

  private static String genericGuidance(String code) {
    String c = code == null || code.isBlank() ? "this code" : ("'" + code + "'");
    return "No custom remediation for " + c + ". See docs/FDML-SPEC.md, docs/TIMING-SPEC.md, docs/TOPOLOGY-SPEC.md, and inspect the referenced node(s).";
  }

  private static Map<String, String> buildGuidance() {
    List<String[]> rows = new ArrayList<>();

    rows.add(new String[]{"xsd_invalid", "XML does not satisfy schema shape. Check the reported line/column, then fix required elements/attributes in schema/fdml.xsd terms."});
    rows.add(new String[]{"schematron_failed_assert", "A Schematron business rule failed. Read the assertion text and rule context in schematron/fdml.sch, then update the matching XML nodes."});

    rows.add(new String[]{"parse_error", "Document is not parseable XML. Fix malformed XML syntax first (tags, quoting, nesting)."});
    rows.add(new String[]{"missing_meter", "Add meta/meter/@value (for example 3/4 or 2+2+2+3/16) so timing and lint checks can evaluate beats."});
    rows.add(new String[]{"off_meter", "Figure total beats are not divisible by meter numerator. Adjust step/@beats or figure content to align with bars."});
    rows.add(new String[]{"bad_meter_format", "Use meter as N/D (like 3/4) or additive A+B+.../D (like 2+2+2+3/16)."});
    rows.add(new String[]{"bad_step_beats", "Each step/@beats must be a positive numeric value (counts semantics in this corpus)."});
    rows.add(new String[]{"off_meter_figure", "Figure total counts do not align with configured bar length/grouping. Rebalance step counts or fix meter value."});

    rows.add(new String[]{"missing_formation_kind", "For fdml version 1.2, set meta/geometry/formation/@kind (circle|line|twoLinesFacing|couple)."});
    rows.add(new String[]{"missing_primitive_kind", "Each step/geo/primitive must include @kind so geometry semantics can be evaluated."});
    rows.add(new String[]{"unknown_role", "Primitive/step references a role id not declared in meta/geometry/roles/role. Declare it or fix the reference."});
    rows.add(new String[]{"bad_formation_for_approach_retreat", "approach/retreat primitives are only valid for formation kind='twoLinesFacing'."});
    rows.add(new String[]{"missing_two_lines_facing", "twoLinesFacing files must declare body/geometry/twoLines/facing with the two line ids."});
    rows.add(new String[]{"missing_approach_retreat_pair", "If twoLinesFacing uses approach/retreat, include both so topology state can return consistently."});
    rows.add(new String[]{"two_lines_no_sep_dip", "Approach/retreat sequence did not produce enough separation change; review primitive sequence and counts."});
    rows.add(new String[]{"circle_order_violation", "In circle formation with preserveOrder=true, avoid crossing primitives like pass/weave/swapPlaces."});
    rows.add(new String[]{"circle_travel_ambiguous", "Circle travel mixes clockwise and counterclockwise markers. Keep one clear direction for the sequence."});
    rows.add(new String[]{"line_travel_too_small", "Line travel directives net to near zero. Verify direction primitives and intended progression distance."});
    rows.add(new String[]{"missing_partner_pairing", "Couple semantics require body/geometry/couples/pair linking man and woman."});
    rows.add(new String[]{"missing_relpos_evidence", "Couple semantics need relpos evidence consistent with womanSide (left/right)."});
    rows.add(new String[]{"relpos_contradiction", "relpos primitives assert contradictory side relations. Keep partner-side statements consistent over time."});
    rows.add(new String[]{"hold_broken", "Hold continuity is inconsistent (e.g., release without compatible hold semantics). Align hold primitives with declared hold kind."});
    rows.add(new String[]{"twirl_missing_half", "Twirl semantics expect half-turn evidence; add/adjust primitive attributes to describe the half turn."});
    rows.add(new String[]{"missing_primitive_frame", "A primitive with @dir must include @frame to disambiguate dancer vs formation coordinates."});
    rows.add(new String[]{"frame_dir_mismatch", "Primitive @dir value does not match @frame expectations. Use formation frame for clockwise/inward and dancer frame for left/right/forward/backward."});
    rows.add(new String[]{"progress_missing_delta", "progress primitive requires integer @delta (line progression shift amount)."});
    rows.add(new String[]{"missing_line_order_slots", "Line progression checks need body/geometry/line/order with slot/@who entries."});
    rows.add(new String[]{"line_order_mismatch", "Computed line order after progress events differs from expected final order. Fix delta sequence or after-order slots."});
    rows.add(new String[]{"missing_circle_order_slots", "Circle order checks require body/geometry/circle/order/slot entries."});
    rows.add(new String[]{"circle_order_changed", "Circle order changed despite preserveOrder semantics. Review swap/crossing primitives or preserveOrder usage."});
    rows.add(new String[]{"two_lines_order_length_mismatch", "twoLines per-line order lists must have equal slot counts to infer opposites."});
    rows.add(new String[]{"unknown_dancer_in_order", "Primitive references dancer ids absent from declared twoLines line orders."});
    rows.add(new String[]{"not_opposites", "swapPlaces frame='opposite' must use dancers opposite by index between the two facing lines."});
    rows.add(new String[]{"not_neighbors", "swapPlaces frame='neighbor' must use adjacent dancers in the same twoLines line order."});
    rows.add(new String[]{"geo_exception", "Geometry validator encountered an internal exception. Inspect the file and stack trace for unsupported structure."});

    Map<String, String> out = new LinkedHashMap<>();
    for (String[] row : rows) out.put(row[0], row[1]);
    return out;
  }
}
