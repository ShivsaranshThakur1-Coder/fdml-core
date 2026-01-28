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

        // Formation-specific primitive checks
        if (("approach".equals(kind) || "retreat".equals(kind)) && !"twoLinesFacing".equals(formationKind)) {
          issues.add(new Issue(
            "bad_formation_for_approach_retreat",
            "primitive kind='" + kind + "' requires formation kind='twoLinesFacing' (found '" + formationKind + "')"
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

      // Circle order preservation (minimal proxy): if any primitive demands preserveOrder, forbid crossing primitives.
      if ("circle".equals(formationKind) && hasPreserveOrder && hasCrossingPrimitive) {
        issues.add(new Issue(
          "circle_order_violation",
          "circle formation with preserveOrder=true must not include crossing primitives (pass/weave/swapPlaces)"
        ));
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
