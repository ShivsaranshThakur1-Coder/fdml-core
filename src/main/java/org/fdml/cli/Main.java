package org.fdml.cli;

import java.nio.file.*;
import java.util.*;

public class Main {
  private static final int EXIT_OK = 0;
  private static final int EXIT_VALIDATION_ERR = 2;
  private static final int EXIT_TRANSFORM_ERR = 3;
  private static final int EXIT_IO_ERR = 4;

  public static void main(String[] args) {
    if (args.length < 1) { usage(); System.exit(EXIT_IO_ERR); }
    String cmd = args[0];
    try {
      switch (cmd) {
        case "validate": {
          boolean json = hasFlag(args, "--json");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("validate: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schemaPath = Paths.get("schema/fdml.xsd");
          FdmlValidator v = new FdmlValidator(schemaPath);
          if (json) {
            List<FdmlValidator.Result> r = v.validateCollect(targets);
            printJsonValidate(r);
            System.exit(allOk(r) ? EXIT_OK : EXIT_VALIDATION_ERR);
          } else {
            boolean ok = v.validatePaths(targets);
            System.exit(ok ? EXIT_OK : EXIT_VALIDATION_ERR);
          }
        }

        case "validate-sch": {
          boolean json = hasFlag(args, "--json");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("validate-sch: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schXsl = Paths.get("schematron/fdml-compiled.xsl");
          SchematronValidator sch = new SchematronValidator(schXsl);
          if (json) {
            List<SchematronValidator.Result> r = sch.validateCollect(targets);
            printJsonValidateSch(r);
            System.exit(allOkSch(r) ? EXIT_OK : EXIT_VALIDATION_ERR);
          } else {
            boolean ok = sch.validatePaths(targets);
            System.exit(ok ? EXIT_OK : EXIT_VALIDATION_ERR);
          }
        }

        case "validate-all": {
          boolean json = hasFlag(args, "--json");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("validate-all: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schemaPath = Paths.get("schema/fdml.xsd");
          FdmlValidator v = new FdmlValidator(schemaPath);
          Path schXsl = Paths.get("schematron/fdml-compiled.xsl");
          SchematronValidator sch = new SchematronValidator(schXsl);
          if (json) {
            List<FdmlValidator.Result> r1 = v.validateCollect(targets);
            List<SchematronValidator.Result> r2 = sch.validateCollect(targets);
            printJsonValidateAll(r1, r2);
            System.exit(allOk(r1) && allOkSch(r2) ? EXIT_OK : EXIT_VALIDATION_ERR);
          } else {
            boolean ok1 = v.validatePaths(targets);
            boolean ok2 = sch.validatePaths(targets);
            System.exit(ok1 && ok2 ? EXIT_OK : EXIT_VALIDATION_ERR);
          }
        }

        case "render": {
          List<String> rest = new ArrayList<>();
          Path out = Paths.get("out/render.html");
          for (int i = 1; i < args.length; i++) {
            if ("--out".equals(args[i]) && i + 1 < args.length) out = Paths.get(args[++i]);
            else rest.add(args[i]);
          }
          if (rest.isEmpty()) { System.err.println("render: provide <fdml-file> [--out path]"); System.exit(EXIT_IO_ERR); }
          Path in  = Paths.get(rest.get(0));
          Path xsl = Paths.get("xslt/fdml-to-card.xsl");
          Renderer.render(in, xsl, out);
          System.exit(EXIT_OK);
        }

        default: { usage(); System.exit(EXIT_IO_ERR); }
      }
    } catch (Exception e) {
      e.printStackTrace();
      System.exit(EXIT_IO_ERR);
    }
  }

  // ----- helpers -----
  private static boolean hasFlag(String[] args, String flag) {
    for (String a : args) if (flag.equals(a)) return true;
    return false;
  }

  private static List<Path> collectNonFlagPaths(String[] args, int from) {
    List<Path> t = new ArrayList<>();
    for (int i = from; i < args.length; i++) {
      String a = args[i];
      if (a.startsWith("--")) continue;
      t.add(Paths.get(a));
    }
    return t;
  }

  private static boolean allOk(List<FdmlValidator.Result> xs) {
    for (FdmlValidator.Result r : xs) if (!r.ok) return false;
    return true;
  }
  private static boolean allOkSch(List<SchematronValidator.Result> xs) {
    for (SchematronValidator.Result r : xs) if (!r.ok) return false;
    return true;
  }

  private static String esc(String s) {
    if (s == null) return null;
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n","\\n").replace("\r","");
  }

  private static void printJsonValidate(List<FdmlValidator.Result> rs) {
    StringBuilder sb = new StringBuilder();
    sb.append("{\"command\":\"validate\",\"results\":[");
    for (int i=0;i<rs.size();i++) {
      var r = rs.get(i);
      sb.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok);
      if (!r.ok) {
        if (r.message != null) sb.append(",\"error\":\"").append(esc(r.message)).append("\"");
        if (r.line != null) sb.append(",\"line\":").append(r.line);
        if (r.column != null) sb.append(",\"column\":").append(r.column);
      }
      sb.append("}");
      if (i < rs.size()-1) sb.append(",");
    }
    sb.append("]}");
    System.out.println(sb.toString());
  }

  private static void printJsonValidateSch(List<SchematronValidator.Result> rs) {
    StringBuilder sb = new StringBuilder();
    sb.append("{\"command\":\"validate-sch\",\"results\":[");
    for (int i=0;i<rs.size();i++) {
      var r = rs.get(i);
      sb.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok)
        .append(",\"failures\":").append(r.failures).append(",\"messages\":[");
      for (int j=0;j<r.messages.size();j++) {
        sb.append("\"").append(esc(r.messages.get(j))).append("\"");
        if (j<r.messages.size()-1) sb.append(",");
      }
      sb.append("]}");
      if (i < rs.size()-1) sb.append(",");
    }
    sb.append("]}");
    System.out.println(sb.toString());
  }

  private static void printJsonValidateAll(List<FdmlValidator.Result> r1, List<SchematronValidator.Result> r2) {
    StringBuilder sb = new StringBuilder();
    sb.append("{\"command\":\"validate-all\",\"xsd\":");
    // reuse
    StringBuilder sb1 = new StringBuilder();
    sb1.append("[");
    for (int i=0;i<r1.size();i++) {
      var r = r1.get(i);
      sb1.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok);
      if (!r.ok) {
        if (r.message != null) sb1.append(",\"error\":\"").append(esc(r.message)).append("\"");
        if (r.line != null) sb1.append(",\"line\":").append(r.line);
        if (r.column != null) sb1.append(",\"column\":").append(r.column);
      }
      sb1.append("}");
      if (i < r1.size()-1) sb1.append(",");
    }
    sb1.append("]");
    sb.append(sb1).append(",\"schematron\":");
    StringBuilder sb2 = new StringBuilder();
    sb2.append("[");
    for (int i=0;i<r2.size();i++) {
      var r = r2.get(i);
      sb2.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok)
         .append(",\"failures\":").append(r.failures).append(",\"messages\":[");
      for (int j=0;j<r.messages.size();j++) {
        sb2.append("\"").append(esc(r.messages.get(j))).append("\"");
        if (j<r.messages.size()-1) sb2.append(",");
      }
      sb2.append("]}");
      if (i < r2.size()-1) sb2.append(",");
    }
    sb2.append("]");
    sb.append(sb2).append("}");
    System.out.println(sb.toString());
  }

  private static void usage() {
    System.out.println("FDML CLI");
    System.out.println("Usage:");
    System.out.println("  validate <file-or-dir> [more...] [--json]      # XSD");
    System.out.println("  validate-sch <file-or-dir> [more...] [--json]  # Schematron");
    System.out.println("  validate-all <file-or-dir> [...] [--json]      # XSD + Schematron");
    System.out.println("  render <fdml-file> [--out out.html]            # XSLT → HTML");
  }
}
