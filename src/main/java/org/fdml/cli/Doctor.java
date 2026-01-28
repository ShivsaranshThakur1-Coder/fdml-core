package org.fdml.cli;

import java.nio.file.*;
import java.util.*;

class Doctor {

  static int run(String[] args) {
    boolean json   = hasFlag(args, "--json");
    boolean strict = hasFlag(args, "--strict");
    List<Path> targets = collectNonFlagPaths(args, 1);
    if (targets.isEmpty()) {
      System.err.println("doctor: provide <file-or-dir> [--json] [--strict]");
      return 4;
    }

    Path schemaPath = Paths.get("schema/fdml.xsd");
    FdmlValidator v = new FdmlValidator(schemaPath);
    SchematronValidator s = new SchematronValidator(Paths.get("schematron/fdml-compiled.xsl"));

    var rX = v.validateCollect(targets);
    var rS = s.validateCollect(targets);
    var rL = Linter.lintCollect(targets);

    var rG = GeometryValidator.validateCollect(targets);

    boolean okX = allOkX(rX);
    boolean okS = allOkS(rS);
    boolean okL = allOkL(rL);
    boolean okG = allOkG(rG);

    if (json) {
      System.out.println(MainJson.toJsonDoctor(rX, rS, rL));
    } else {
      System.out.println("DOCTOR SUMMARY");
      System.out.println("  XSD       : " + (okX ? "OK" : "FAILED"));
      System.out.println("  Schematron: " + (okS ? "OK" : "FAILED"));
      System.out.println("  GEO       : " + (okG ? "OK" : "FAILED"));
      long warns = rL.stream().filter(fr -> !fr.ok()).count();
      System.out.println("  Lint      : " + (warns == 0 ? "OK" : (warns + " file(s) with warnings")));
    }

    if (strict) {
      if (!okX || !okS || !okL || !okG) return 2;
    }
    return 0;
  }

  private static boolean hasFlag(String[] a, String f){ for (String s : a) if (f.equals(s)) return true; return false; }
  private static List<Path> collectNonFlagPaths(String[] args, int from) {
    List<Path> t = new ArrayList<>();
    for (int i = from; i < args.length; i++) if (!args[i].startsWith("--")) t.add(Paths.get(args[i]));
    return t;
  }

  private static boolean allOkX(java.util.List<FdmlValidator.Result> xs){ for (var r: xs) if(!r.ok) return false; return true; }
  private static boolean allOkS(java.util.List<SchematronValidator.Result> xs){ for (var r: xs) if(!r.ok) return false; return true; }
  private static boolean allOkL(java.util.List<Linter.FileResult> xs){ for (var r: xs) if(!r.ok()) return false; return true; }
  private static boolean allOkG(java.util.List<GeometryValidator.Result> xs){ for (var r: xs) if(!r.ok) return false; return true; }
}
