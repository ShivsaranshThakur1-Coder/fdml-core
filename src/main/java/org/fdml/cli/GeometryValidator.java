package org.fdml.cli;

import net.sf.saxon.s9api.*;

import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.util.*;

/**
 * FDML v1.2 geometry validator.
 *
 * Purpose:
 * - Provide stateful / computed validation that cannot be expressed cleanly in XSD or Schematron.
 * - Validate a subset of invariants described in docs/GEOMETRY-SPEC.md.
 *
 * Current scope (minimal, evidence-driven):
 * - Require meta/geometry/formation/@kind for fdml[@version='1.2'].
 * - Validate that step/geo/primitive has @kind, and (if roles declared) @who references a role.
 * - Apply lightweight formation-specific checks:
 *   - circle: primitives with preserveOrder=true must not include crossing primitives (pass/weave/swapPlaces)
 *   - twoLinesFacing: approach/retreat primitives only allowed in that formation
 */
class GeometryValidator {

  static final class Issue {
    final String code;
    final String message;
    Issue(String code, String message) { this.code = code; this.message = message; }
  }

  static final class Result {
    final Path file;
    final boolean ok;
    final List<Issue> issues;
    Result(Path file, boolean ok, List<Issue> issues) {
      this.file = file;
      this.ok = ok;
      this.issues = issues;
    }
  }

  static List<Result> validateCollect(List<Path> inputs) {
    List<Path> files = expandAll(inputs);
    List<Result> out = new ArrayList<>();
    for (Path f : files) {
      if (!looksLikeXml(f)) continue;
      out.add(validateOne(f));
    }
    return out;
  }

  static boolean validatePaths(List<Path> inputs) {
    List<Result> results = validateCollect(inputs);
    boolean allOk = true;
    for (Result r : results) {
      if (r.ok) System.out.println("GEO OK  : " + r.file);
      else {
        System.out.println("GEO FAIL: " + r.file + " (" + r.issues.size() + " issue(s))");
        for (Issue i : r.issues) System.out.println("  → [" + i.code + "] " + i.message);
      }
      allOk &= r.ok;
    }
    System.out.printf("Geometry checked %d file(s).%n", results.size());
    return allOk;
  }

  static Result validateOne(Path f) {
    List<Issue> issues = new ArrayList<>();

    try {
      Processor proc = new Processor(false);
      DocumentBuilder db = proc.newDocumentBuilder();
      XdmNode doc = db.build(new StreamSource(f.toFile()));
      XPathCompiler xpc = proc.newXPathCompiler();

      String version = str(xpc, "string(/fdml/@version)", doc);
      if (!"1.2".equals(version)) {
        // Not a v1.2 file; geometry validation is a no-op and passes.
        return new Result(f, true, issues);
      }

      String formationKind = str(xpc, "string(/fdml/meta/geometry/formation/@kind)", doc);
      if (formationKind.isEmpty()) {
        issues.add(new Issue("missing_formation_kind", "meta/geometry/formation/@kind is required for fdml version=1.2"));
      }

      // Roles
      Set<String> roles = new HashSet<>();
      XdmValue roleIds = xpc.evaluate("/fdml/meta/geometry/roles/role/@id", doc);
      for (XdmItem it : roleIds) roles.add(it.getStringValue());
      boolean hasRoles = !roles.isEmpty();

      // Validate primitive kinds exist and collect flags
      XdmValue prims = xpc.evaluate("//step/geo/primitive", doc);
      boolean hasCrossingPrimitive = false;
      boolean hasPreserveOrder = false;

      // New numeric / computed checks need some file-wide signals.
      boolean sawClockwiseTravel = false;
      boolean sawCounterClockwiseTravel = false;

      boolean sawApproach = false;
      boolean sawRetreat = false;

      boolean sawReleaseHold = false;

      boolean sawProgress = false;
      boolean sawProgressMissingDelta = false;

      for (XdmItem it : prims) {
        XdmNode p = (XdmNode) it;
        String kind = str(xpc, "string(@kind)", p);
        if (kind.isEmpty()) {
          issues.add(new Issue("missing_primitive_kind", "geo/primitive is missing @kind"));
        }

        String who = str(xpc, "string(@who)", p);
        if (hasRoles && !who.isEmpty() && !roles.contains(who)) {
          issues.add(new Issue("unknown_role", "geo/primitive/@who='" + who + "' is not declared in meta/geometry/roles"));
        }

        String preserve = str(xpc, "string(@preserveOrder)", p);
        if (!preserve.isEmpty() && ("true".equals(preserve) || "1".equals(preserve))) {
          hasPreserveOrder = true;
        }

        if ("pass".equals(kind) || "weave".equals(kind) || "swapPlaces".equals(kind)) {
          hasCrossingPrimitive = true;
        }

        // Ontology Batch 4C: direction must be disambiguated by explicit frame.
        String dir = str(xpc, "string(@dir)", p);
        if (dir != null && !dir.isBlank()) {
          String frame = str(xpc, "string(@frame)", p);
          if (frame == null || frame.isBlank()) {
            issues.add(new Issue(
              "missing_primitive_frame",
              "geo/primitive with dir='" + dir + "' is missing required @frame"
            ));
          } else {
            String d = dir.trim();
            boolean formationDir = "clockwise".equals(d) || "counterclockwise".equals(d) || "inward".equals(d) || "outward".equals(d) || "center".equals(d);
            boolean dancerDir = "forward".equals(d) || "backward".equals(d) || "left".equals(d) || "right".equals(d);
            if (formationDir && !"formation".equals(frame)) {
              issues.add(new Issue(
                "frame_dir_mismatch",
                "dir='" + dir + "' requires frame='formation' (found frame='" + frame + "')"
              ));
            } else if (dancerDir && !"dancer".equals(frame)) {
              issues.add(new Issue(
                "frame_dir_mismatch",
                "dir='" + dir + "' requires frame='dancer' (found frame='" + frame + "')"
              ));
            }
          }
        }

        // A) circle: detect travel direction ambiguity
        // Scan all primitive @dir (and also @axis if present) for cw/ccw markers.
        String axis = str(xpc, "string(@axis)", p);
        String dirAxis = ((dir == null ? "" : dir) + " " + axis).toLowerCase(Locale.ROOT);
        if (isCcw(dirAxis)) sawCounterClockwiseTravel = true;
        if (isCw(dirAxis)) sawClockwiseTravel = true;

        // Track approach / retreat presence for twoLinesFacing numeric check.
        if ("approach".equals(kind)) sawApproach = true;
        if ("retreat".equals(kind)) sawRetreat = true;

        if ("releaseHold".equals(kind)) sawReleaseHold = true;

        if ("progress".equals(kind)) {
          sawProgress = true;
          String delta = str(xpc, "string(@delta)", p);
          if (delta == null || delta.isBlank() || parseInt(delta.trim()) == null) sawProgressMissingDelta = true;
        }

        // Formation-specific primitive checks
        if (("approach".equals(kind) || "retreat".equals(kind)) && !"twoLinesFacing".equals(formationKind)) {
          issues.add(new Issue(
            "bad_formation_for_approach_retreat",
            "primitive kind='" + kind + "' requires formation kind='twoLinesFacing' (found '" + formationKind + "')"
          ));
        }
      }

      if ("circle".equals(formationKind) && sawClockwiseTravel && sawCounterClockwiseTravel) {
        issues.add(new Issue(
          "circle_travel_ambiguous",
          "circle formation includes both clockwise and counterclockwise travel markers across step/geo/primitive/@dir (or @axis)"
        ));
      }

      // B) twoLinesFacing: enforce approach/retreat pair + separation dip (numeric)
      if ("twoLinesFacing".equals(formationKind) && (sawApproach || sawRetreat)) {
        if (!sawApproach || !sawRetreat) {
          issues.add(new Issue(
            "missing_approach_retreat_pair",
            "twoLinesFacing formation includes approach/retreat primitives but does not include both an approach and a retreat"
          ));
        }

        double sep = 2.0;
        double minSep = sep;
        double maxSep = sep;

        XdmValue steps = xpc.evaluate("//step", doc);
        for (XdmItem it : steps) {
          XdmNode step = (XdmNode) it;
          double beats = dbl(xpc, "number(@beats)", step);

          boolean stepHasApproach = bool(xpc, "exists(geo/primitive[@kind='approach'])", step);
          boolean stepHasRetreat = bool(xpc, "exists(geo/primitive[@kind='retreat'])", step);

          if (stepHasApproach) sep -= 0.12 * (beats / 2.0);
          if (stepHasRetreat) sep += 0.12 * (beats / 2.0);

          minSep = Math.min(minSep, sep);
          maxSep = Math.max(maxSep, sep);
        }

        if ((maxSep - minSep) < 0.3) {
          issues.add(new Issue(
            "two_lines_no_sep_dip",
            "twoLinesFacing approach/retreat sequence does not vary separation enough (max-min < 0.3)"
          ));
        }
      }

      // C) line: travel direction presence check (numeric)
      if ("line".equals(formationKind)) {
        double totalDx = 0.0;
        boolean sawTravelDir = false;

        XdmValue steps = xpc.evaluate("//step", doc);
        for (XdmItem it : steps) {
          XdmNode step = (XdmNode) it;
          double beats = dbl(xpc, "number(@beats)", step);

          XdmValue stepPrims = xpc.evaluate("geo/primitive", step);
          for (XdmItem pit : stepPrims) {
            XdmNode p = (XdmNode) pit;
            String dir = str(xpc, "string(@dir)", p).toLowerCase(Locale.ROOT);
            if (dir.contains("right") || isCw(dir)) {
              sawTravelDir = true;
              totalDx += 0.10 * (beats / 4.0);
            } else if (dir.contains("left") || isCcw(dir)) {
              sawTravelDir = true;
              totalDx -= 0.10 * (beats / 4.0);
            }
          }
        }

        if (sawTravelDir && Math.abs(totalDx) < 0.05) {
          issues.add(new Issue(
            "line_travel_too_small",
            "line formation includes travel direction primitives but computed total travel is too small (abs(dx) < 0.05)"
          ));
        }
      }

      // If roles declared, also validate step/@who references a role.
      if (hasRoles) {
        XdmValue whos = xpc.evaluate("//step/@who", doc);
        for (XdmItem it : whos) {
          String who = it.getStringValue();
          if (!who.isEmpty() && !roles.contains(who)) {
            issues.add(new Issue("unknown_role", "step/@who='" + who + "' is not declared in meta/geometry/roles"));
          }
        }

        // body/geometry circle/order role reference
        XdmValue circleRole = xpc.evaluate("/fdml/body/geometry/circle/order/@role", doc);
        for (XdmItem it : circleRole) {
          String r = it.getStringValue();
          if (!r.isEmpty() && !roles.contains(r)) {
            issues.add(new Issue("unknown_role", "body/geometry/circle/order/@role='" + r + "' is not declared in meta/geometry/roles"));
          }
        }
      }

      // Circle order preservation (proxy): if any primitive demands preserveOrder, forbid crossing primitives.
      if ("circle".equals(formationKind) && hasPreserveOrder && hasCrossingPrimitive) {
        issues.add(new Issue(
          "circle_order_violation",
          "circle formation with preserveOrder=true must not include crossing primitives (pass/weave/swapPlaces)"
        ));
      }

      // Ontology Batch 1: twoLinesFacing should declare which roles/lines face each other.
      if ("twoLinesFacing".equals(formationKind)) {
        boolean hasFacing = bool(xpc, "exists(/fdml/body/geometry/twoLines/facing)", doc);
        if (!hasFacing) {
          issues.add(new Issue(
            "missing_two_lines_facing",
            "twoLinesFacing formation must declare body/geometry/twoLines/facing"
          ));
        }

        // Optional per-line dancer order in twoLines/line/order.
        Map<String, List<String>> twoLineOrders = new LinkedHashMap<>();
        Set<String> orderedDancers = new LinkedHashSet<>();
        boolean hasBlankInOrder = false;

        XdmValue twoLineNodes = xpc.evaluate("/fdml/body/geometry/twoLines/line[@id]", doc);
        for (XdmItem lit : twoLineNodes) {
          XdmNode lineNode = (XdmNode) lit;
          String lineId = str(xpc, "string(@id)", lineNode);
          XdmValue orderWho = xpc.evaluate("order[1]/slot/@who", lineNode);
          if (orderWho == null || orderWho.size() == 0) continue;

          List<String> slots = new ArrayList<>();
          for (XdmItem sit : orderWho) {
            String who = sit.getStringValue();
            if (who == null || who.isBlank()) {
              hasBlankInOrder = true;
              issues.add(new Issue(
                "unknown_dancer_in_order",
                "twoLines line id='" + lineId + "' has blank order slot who value"
              ));
              continue;
            }
            String w = who.trim();
            slots.add(w);
            orderedDancers.add(w);
          }
          twoLineOrders.put(lineId, slots);
        }

        Map<String, String> inferredOpposite = new HashMap<>();
        List<String> orderLineIds = new ArrayList<>(twoLineOrders.keySet());
        if (orderLineIds.size() >= 2) {
          String facingA = str(xpc, "string(/fdml/body/geometry/twoLines/facing[1]/@a)", doc);
          String facingB = str(xpc, "string(/fdml/body/geometry/twoLines/facing[1]/@b)", doc);

          String lineA = null;
          String lineB = null;
          if (twoLineOrders.containsKey(facingA) && twoLineOrders.containsKey(facingB)) {
            lineA = facingA;
            lineB = facingB;
          } else {
            lineA = orderLineIds.get(0);
            lineB = orderLineIds.get(1);
          }

          List<String> aOrder = twoLineOrders.get(lineA);
          List<String> bOrder = twoLineOrders.get(lineB);
          if (aOrder != null && bOrder != null) {
            if (aOrder.size() != bOrder.size()) {
              issues.add(new Issue(
                "two_lines_order_length_mismatch",
                "twoLines line orders for '" + lineA + "' and '" + lineB + "' must have equal length"
              ));
            } else if (!hasBlankInOrder) {
              for (int i = 0; i < aOrder.size(); i++) {
                String a = aOrder.get(i);
                String b = bOrder.get(i);
                inferredOpposite.put(a, b);
                inferredOpposite.put(b, a);
              }
            }
          }
        }

        // If orders exist, validate primitive a/b references and opposite-frame swap rules.
        if (!twoLineOrders.isEmpty()) {
          for (XdmItem pit : prims) {
            XdmNode p = (XdmNode) pit;
            String a = str(xpc, "string(@a)", p);
            String b = str(xpc, "string(@b)", p);

            if (a != null && !a.isBlank() && !orderedDancers.contains(a.trim())) {
              issues.add(new Issue(
                "unknown_dancer_in_order",
                "primitive references @a='" + a + "' not present in twoLines line orders"
              ));
            }
            if (b != null && !b.isBlank() && !orderedDancers.contains(b.trim())) {
              issues.add(new Issue(
                "unknown_dancer_in_order",
                "primitive references @b='" + b + "' not present in twoLines line orders"
              ));
            }

            String kind = str(xpc, "string(@kind)", p);
            String frame = str(xpc, "string(@frame)", p);
            if ("swapPlaces".equals(kind) && "opposite".equals(frame) && a != null && b != null && !a.isBlank() && !b.isBlank()) {
              String aa = a.trim();
              String bb = b.trim();
              if (inferredOpposite.containsKey(aa) && inferredOpposite.containsKey(bb)) {
                String expected = inferredOpposite.get(aa);
                if (!bb.equals(expected)) {
                  issues.add(new Issue(
                    "not_opposites",
                    "swapPlaces frame='opposite' expects opposite pair, but got a='" + aa + "', b='" + bb + "'"
                  ));
                }
              }
            }
          }
        }
      }

      // Ontology Batch 2: hold integrity.
      String holdKind = str(xpc, "string(/fdml/meta/geometry/hold/@kind)", doc);
      if (holdKind != null && !holdKind.isBlank() && !"none".equals(holdKind) && sawReleaseHold) {
        issues.add(new Issue(
          "hold_broken",
          "meta/geometry/hold/@kind='" + holdKind + "' but a primitive uses kind='releaseHold'"
        ));
      }

      // Ontology Batch 4A: line progression requires explicit line order slots and progress delta.
      if ("line".equals(formationKind) && sawProgress) {
        XdmValue lineNodes = xpc.evaluate("/fdml/body/geometry/line[@id]", doc);
        boolean hasAnyLineSlots = false;
        boolean checkedAnyLineOrder = false;

        for (XdmItem lit : lineNodes) {
          XdmNode lineNode = (XdmNode) lit;
          String lineId = str(xpc, "string(@id)", lineNode);
          XdmValue orderNodes = xpc.evaluate("order", lineNode);
          if (orderNodes == null || orderNodes.size() == 0) continue;

          List<XdmNode> orders = new ArrayList<>();
          for (XdmItem oit : orderNodes) orders.add((XdmNode) oit);
          checkedAnyLineOrder = true;

          XdmNode initialOrderNode = selectInitialOrder(orders, xpc);
          List<String> currentOrder = readOrderSlots(initialOrderNode, xpc);
          if (!currentOrder.isEmpty()) hasAnyLineSlots = true;

          XdmNode expectedOrderNode = selectExpectedAfterOrder(orders, xpc);
          List<String> expectedOrder = readOrderSlots(expectedOrderNode, xpc);

          if (currentOrder.isEmpty()) continue;

          for (XdmItem pit : prims) {
            XdmNode p = (XdmNode) pit;
            String kind = str(xpc, "string(@kind)", p);
            if (!"progress".equals(kind)) continue;

            String deltaRaw = str(xpc, "string(@delta)", p);
            Integer delta = parseInt(deltaRaw);
            if (delta == null) continue; // Already reported as progress_missing_delta.
            currentOrder = rotateForward(currentOrder, delta);
          }

          if (!expectedOrder.isEmpty() && !currentOrder.equals(expectedOrder)) {
            issues.add(new Issue(
              "line_order_mismatch",
              "line id='" + lineId + "' expected order " + expectedOrder + " but computed " + currentOrder
            ));
          }
        }

        if (!checkedAnyLineOrder) {
          XdmValue lineSlots = xpc.evaluate("/fdml/body/geometry/line/order/slot/@who", doc);
          for (XdmItem it : lineSlots) {
            String who = it.getStringValue();
            if (who != null && !who.isBlank()) {
              hasAnyLineSlots = true;
              break;
            }
          }
        }

        if (!hasAnyLineSlots) {
          issues.add(new Issue(
            "missing_line_order_slots",
            "line formation includes progress primitives but body/geometry/line/order/slot list is missing"
          ));
        }

        if (sawProgressMissingDelta) {
          issues.add(new Issue(
            "progress_missing_delta",
            "progress primitive is missing required @delta"
          ));
        }
      }

      // Ontology Batch 2: twirl primitives must contain both halves (cw + ccw) within each figure.
      XdmValue figs = xpc.evaluate("/fdml/body//figure", doc);
      for (XdmItem fit : figs) {
        XdmNode fig = (XdmNode) fit;
        String figId = str(xpc, "string(@id)", fig);

        boolean figSawTwirl = false;
        boolean figSawCw = false;
        boolean figSawCcw = false;

        XdmValue figPrims = xpc.evaluate(".//step/geo/primitive", fig);
        for (XdmItem pit : figPrims) {
          XdmNode p = (XdmNode) pit;
          String k = str(xpc, "string(@kind)", p);
          if (k == null) k = "";
          if (!"twirl".equals(k.toLowerCase(Locale.ROOT))) continue;

          figSawTwirl = true;
          String dir = str(xpc, "string(@dir)", p);
          if (isCw(dir)) figSawCw = true;
          if (isCcw(dir)) figSawCcw = true;
        }

        if (figSawTwirl && !(figSawCw && figSawCcw)) {
          issues.add(new Issue(
            "twirl_missing_half",
            "figure" + (figId.isEmpty() ? "" : " '" + figId + "'") + " contains twirl but is missing cw or ccw half"
          ));
        }
      }

      // Ontology Batch 1: couple formation with womanSide should declare canonical partner roles + pairing.
      if ("couple".equals(formationKind)) {
        String womanSide = str(xpc, "string(/fdml/meta/geometry/formation/@womanSide)", doc);
        if (womanSide != null && !womanSide.isBlank()) {
          boolean hasMan = roles.contains("man");
          boolean hasWoman = roles.contains("woman");
          boolean hasPartnerPair = bool(xpc,
            "exists(/fdml/body/geometry/couples/pair[(@a='man' and @b='woman') or (@a='woman' and @b='man')])",
            doc
          );

          if (!hasMan || !hasWoman || !hasPartnerPair) {
            issues.add(new Issue(
              "missing_partner_pairing",
              "couple formation with womanSide requires roles man+woman and a couples/pair linking them"
            ));
          }

          // Ontology Batch 4B: stateful side semantics using relpos + swap tracking.
          if (hasMan && hasWoman) {
            String sideState = "left".equals(womanSide) ? "left" : ("right".equals(womanSide) ? "right" : "");
            boolean sawRelposEvidence = false;

            if (!sideState.isEmpty()) {
              for (XdmItem it : prims) {
                XdmNode p = (XdmNode) it;
                String kind = str(xpc, "string(@kind)", p);
                if (kind == null) kind = "";
                String k = kind.toLowerCase(Locale.ROOT);

                String a = str(xpc, "string(@a)", p);
                String b = str(xpc, "string(@b)", p);
                boolean isManWomanPair = ("man".equals(a) && "woman".equals(b)) || ("woman".equals(a) && "man".equals(b));

                if ("swapplaces".equals(k) && isManWomanPair) {
                  // swapPlaces between man/woman flips the expected side.
                  sideState = "left".equals(sideState) ? "right" : "left";
                }

                if ("relpos".equals(k) && isManWomanPair) {
                  String relation = str(xpc, "string(@relation)", p);
                  if (relation == null) relation = "";

                  String assertedSide = "";
                  if ("woman".equals(a) && "man".equals(b)) {
                    if ("leftOf".equals(relation)) assertedSide = "left";
                    else if ("rightOf".equals(relation)) assertedSide = "right";
                  } else if ("man".equals(a) && "woman".equals(b)) {
                    if ("leftOf".equals(relation)) assertedSide = "right";
                    else if ("rightOf".equals(relation)) assertedSide = "left";
                  }

                  if (!assertedSide.isEmpty()) {
                    sawRelposEvidence = true;
                    if (!assertedSide.equals(sideState)) {
                      String figId = str(xpc, "string(ancestor::figure[1]/@id)", p);
                      issues.add(new Issue(
                        "relpos_contradiction",
                        "figure" + (figId.isEmpty() ? "" : " '" + figId + "'")
                          + " sideState=" + sideState + " but relpos asserts " + relation + " (a='" + a + "', b='" + b + "')"
                      ));
                    }
                  }
                }
              }

              if (!sawRelposEvidence) {
                issues.add(new Issue(
                  "missing_relpos_evidence",
                  "couple formation with womanSide cannot be validated without relpos evidence between man and woman"
                ));
              }
            }
          }
        }
      }

      // Circle order preservation (true / explicit role order slots)
      if ("circle".equals(formationKind) && hasPreserveOrder) {
        XdmValue slots = xpc.evaluate("/fdml/body/geometry/circle/order/slot/@who", doc);
        List<String> initialOrder = new ArrayList<>();
        for (XdmItem it : slots) {
          String who = it.getStringValue();
          if (who != null && !who.isBlank()) initialOrder.add(who);
        }

        if (initialOrder.isEmpty()) {
          issues.add(new Issue(
            "missing_circle_order_slots",
            "circle formation uses preserveOrder=true but body/geometry/circle/order/slot list is missing"
          ));
        } else {
          List<String> working = new ArrayList<>(initialOrder);

          // Scan primitives in document order and apply swapPlaces(a,b) to the order list.
          for (XdmItem it : prims) {
            XdmNode p = (XdmNode) it;
            String kind = str(xpc, "string(@kind)", p);
            if (kind == null) kind = "";
            String k = kind.toLowerCase(Locale.ROOT);
            if ("swapplaces".equals(k)) {
              String a = str(xpc, "string(@a)", p);
              String b = str(xpc, "string(@b)", p);
              if (a != null && b != null && !a.isBlank() && !b.isBlank()) {
                int ia = working.indexOf(a);
                int ib = working.indexOf(b);
                if (ia >= 0 && ib >= 0 && ia != ib) {
                  working.set(ia, b);
                  working.set(ib, a);
                }
              }
            }
          }

          if (!working.equals(initialOrder)) {
            issues.add(new Issue(
              "circle_order_changed",
              "circle preserveOrder=true but swapPlaces primitives changed the explicit circle order"
            ));
          }
        }
      }

    } catch (Exception e) {
      issues.add(new Issue("geo_exception", "Geometry validator exception: " + e.getMessage()));
    }

    boolean ok = issues.isEmpty();
    return new Result(f, ok, issues);
  }

  private static String str(XPathCompiler xpc, String expr, XdmNode node) {
    try {
      XdmItem i = xpc.evaluateSingle(expr, node);
      return i == null ? "" : i.getStringValue();
    } catch (SaxonApiException e) {
      return "";
    }
  }

  private static boolean bool(XPathCompiler xpc, String expr, XdmNode node) {
    try {
      XdmItem i = xpc.evaluateSingle(expr, node);
      if (i == null) return false;
      String v = i.getStringValue();
      // Saxon represents xs:boolean as "true"/"false".
      return "true".equalsIgnoreCase(v) || "1".equals(v);
    } catch (SaxonApiException e) {
      return false;
    }
  }

  private static double dbl(XPathCompiler xpc, String expr, XdmNode node) {
    try {
      XdmItem i = xpc.evaluateSingle(expr, node);
      if (i == null) return 0.0;
      String v = i.getStringValue();
      if (v == null || v.isBlank()) return 0.0;
      // XPath number() can produce NaN. Treat that as 0.
      double d = Double.parseDouble(v);
      return Double.isFinite(d) ? d : 0.0;
    } catch (Exception e) {
      return 0.0;
    }
  }

  private static boolean isCcw(String s) {
    if (s == null) return false;
    String t = s.toLowerCase(Locale.ROOT);
    return t.contains("counterclockwise") || containsToken(t, "ccw");
  }

  private static boolean isCw(String s) {
    if (s == null) return false;
    String t = s.toLowerCase(Locale.ROOT);
    // Avoid treating "counterclockwise" as clockwise.
    if (t.contains("counterclockwise") || containsToken(t, "ccw")) return false;
    return t.contains("clockwise") || containsToken(t, "cw");
  }

  private static boolean containsToken(String haystack, String token) {
    if (haystack == null || token == null || token.isEmpty()) return false;
    // Token boundary: non-letter on both sides (or start/end).
    int idx = -1;
    while ((idx = haystack.indexOf(token, idx + 1)) >= 0) {
      boolean leftOk = idx == 0 || !Character.isLetter(haystack.charAt(idx - 1));
      int r = idx + token.length();
      boolean rightOk = r == haystack.length() || !Character.isLetter(haystack.charAt(r));
      if (leftOk && rightOk) return true;
    }
    return false;
  }

  private static Integer parseInt(String s) {
    if (s == null) return null;
    String t = s.trim();
    if (t.isEmpty()) return null;
    try {
      return Integer.parseInt(t);
    } catch (NumberFormatException e) {
      return null;
    }
  }

  private static XdmNode selectInitialOrder(List<XdmNode> orders, XPathCompiler xpc) {
    if (orders == null || orders.isEmpty()) return null;
    for (XdmNode o : orders) {
      String phase = str(xpc, "string(@phase)", o);
      if ("initial".equalsIgnoreCase(phase)) return o;
    }
    return orders.get(0);
  }

  private static XdmNode selectExpectedAfterOrder(List<XdmNode> orders, XPathCompiler xpc) {
    if (orders == null || orders.isEmpty()) return null;
    for (XdmNode o : orders) {
      String phase = str(xpc, "string(@phase)", o);
      if ("after".equalsIgnoreCase(phase)) return o;
    }
    if (orders.size() >= 2) return orders.get(orders.size() - 1);
    return null;
  }

  private static List<String> readOrderSlots(XdmNode orderNode, XPathCompiler xpc) {
    List<String> out = new ArrayList<>();
    if (orderNode == null) return out;
    XdmValue slots = eval(xpc, "slot/@who", orderNode);
    for (XdmItem it : slots) {
      String who = it.getStringValue();
      if (who != null && !who.isBlank()) out.add(who);
    }
    return out;
  }

  private static List<String> rotateForward(List<String> in, int delta) {
    if (in == null || in.isEmpty()) return in == null ? new ArrayList<>() : new ArrayList<>(in);
    int n = in.size();
    int shift = delta % n;
    if (shift < 0) shift += n;
    if (shift == 0) return new ArrayList<>(in);

    List<String> out = new ArrayList<>(n);
    for (int i = 0; i < n; i++) out.add(in.get((i + shift) % n));
    return out;
  }

  private static XdmValue eval(XPathCompiler xpc, String expr, XdmNode node) {
    try {
      return xpc.evaluate(expr, node);
    } catch (SaxonApiException e) {
      return XdmEmptySequence.getInstance();
    }
  }

  private static boolean looksLikeXml(Path p) {
    String n = p.getFileName().toString().toLowerCase(Locale.ROOT);
    return n.endsWith(".xml") || n.endsWith(".fdml") || n.endsWith(".fdml.xml");
  }

  private static List<Path> expandAll(List<Path> inputs) {
    List<Path> out = new ArrayList<>();
    for (Path p : inputs) {
      try {
        if (Files.isDirectory(p)) Files.walk(p).filter(Files::isRegularFile).forEach(out::add);
        else out.add(p);
      } catch (Exception e) {
        throw new RuntimeException(e);
      }
    }
    return out;
  }
}
