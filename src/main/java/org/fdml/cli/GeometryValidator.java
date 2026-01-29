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

        // A) circle: detect travel direction ambiguity
        // Scan all primitive @dir (and also @axis if present) for cw/ccw markers.
        String dir = str(xpc, "string(@dir)", p);
        String axis = str(xpc, "string(@axis)", p);
        String dirAxis = (dir + " " + axis).toLowerCase(Locale.ROOT);
        if (isCcw(dirAxis)) sawCounterClockwiseTravel = true;
        if (isCw(dirAxis)) sawClockwiseTravel = true;

        // Track approach / retreat presence for twoLinesFacing numeric check.
        if ("approach".equals(kind)) sawApproach = true;
        if ("retreat".equals(kind)) sawRetreat = true;

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
