package org.fdml.cli;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
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
          String jsonOut = flagValue(args, "--json-out");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("validate: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schemaPath = Paths.get("schema/fdml.xsd");
          FdmlValidator v = new FdmlValidator(schemaPath);
          if (json || jsonOut != null) {
            var r = v.validateCollect(targets);
            String payload = toJsonValidate(r);
            System.out.println(payload);
            if (jsonOut != null) Files.writeString(Paths.get(jsonOut), payload, StandardCharsets.UTF_8);
            System.exit(allOk(r) ? EXIT_OK : EXIT_VALIDATION_ERR);
          } else {
            boolean ok = v.validatePaths(targets);
            System.exit(ok ? EXIT_OK : EXIT_VALIDATION_ERR);
          }
        }

        case "validate-sch": {
          boolean json = hasFlag(args, "--json");
          String jsonOut = flagValue(args, "--json-out");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("validate-sch: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schXsl = Paths.get("schematron/fdml-compiled.xsl");
          SchematronValidator sch = new SchematronValidator(schXsl);
          if (json || jsonOut != null) {
            var r = sch.validateCollect(targets);
            String payload = toJsonValidateSch(r);
            System.out.println(payload);
            if (jsonOut != null) Files.writeString(Paths.get(jsonOut), payload, StandardCharsets.UTF_8);
            System.exit(allOkSch(r) ? EXIT_OK : EXIT_VALIDATION_ERR);
          } else {
            boolean ok = sch.validatePaths(targets);
            System.exit(ok ? EXIT_OK : EXIT_VALIDATION_ERR);
          }
        }

        case "validate-all": {
          boolean json = hasFlag(args, "--json");
          String jsonOut = flagValue(args, "--json-out");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("validate-all: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schemaPath = Paths.get("schema/fdml.xsd");
          FdmlValidator v = new FdmlValidator(schemaPath);
          Path schXsl = Paths.get("schematron/fdml-compiled.xsl");
          SchematronValidator sch = new SchematronValidator(schXsl);
          if (json || jsonOut != null) {
            var r1 = v.validateCollect(targets);
            var r2 = sch.validateCollect(targets);
            String payload = toJsonValidateAll(r1, r2);
            System.out.println(payload);
            if (jsonOut != null) Files.writeString(Paths.get(jsonOut), payload, StandardCharsets.UTF_8);
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

        case "export-pdf": {
          List<String> rest = new ArrayList<>();
          Path out = Paths.get("out/export.pdf");
          for (int i = 1; i < args.length; i++) {
            if ("--out".equals(args[i]) && i + 1 < args.length) out = Paths.get(args[++i]);
            else rest.add(args[i]);
          }
          if (rest.isEmpty()) { System.err.println("export-pdf: provide <fdml-file> [--out out.pdf]"); System.exit(EXIT_IO_ERR); }
          Path in  = Paths.get(rest.get(0));
          Path xsl = Paths.get("xslt/fdml-to-xhtml.xsl");
          Path examplesDir = Paths.get("docs/examples");
          PdfExporter.export(in, xsl, examplesDir, out);
          System.exit(EXIT_OK);
        }

        case "index": {
          List<String> rest = new ArrayList<>();
          Path out = Paths.get("out/index.json");
          for (int i = 1; i < args.length; i++) {
            if ("--out".equals(args[i]) && i + 1 < args.length) out = Paths.get(args[++i]);
            else rest.add(args[i]);
          }
          if (rest.isEmpty()) { System.err.println("index: provide <file-or-dir> [more...] [--out path]"); System.exit(EXIT_IO_ERR); }
          List<Path> targets = new ArrayList<>();
          for (String r : rest) targets.add(Paths.get(r));
          String payload = Indexer.buildIndex(targets);
          System.out.println(payload);
          try { Files.createDirectories(out.getParent()); } catch (Exception ignored) {}
          Files.writeString(out, payload, StandardCharsets.UTF_8);
          System.exit(EXIT_OK);
        }

        case "lint": {
          boolean json = hasFlag(args, "--json");
          String jsonOut = flagValue(args, "--json-out");
          boolean strict = hasFlag(args, "--strict");
          List<Path> targets = collectNonFlagPaths(args, 1);
          if (targets.isEmpty()) { System.err.println("lint: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          var rs = Linter.lintCollect(targets);
          if (json || jsonOut != null) {
            String payload = toJsonLint(rs);
            System.out.println(payload);
            if (jsonOut != null) Files.writeString(Paths.get(jsonOut), payload, StandardCharsets.UTF_8);
          } else {
            for (var r : rs) {
              if (r.ok()) System.out.println("LINT OK : " + r.file);
              else {
                System.out.println("LINT WARN: " + r.file + " (" + r.warnings.size() + " warning(s))");
                for (var w : r.warnings) {
                  System.out.println("  → [" + w.code + "] figure=" + String.valueOf(w.figureId) +
                                     " beats=" + w.beats +
                                     (w.meter == null ? "" : " meter=" + w.meter) +
                                     (w.bars == null ? "" : " bars≈" + w.bars) +
                                     " : " + w.message);
                }
              }
            }
          }
          boolean anyWarn = false; for (var r : rs) if (!r.ok()) { anyWarn = true; break; }
          if (strict && anyWarn) System.exit(EXIT_VALIDATION_ERR);
          System.exit(EXIT_OK);
        }

        case "init": { Init.run(args); System.exit(EXIT_OK); }
        case "doctor": { int code = Doctor.run(args); System.exit(code); }

        default: { usage(); System.exit(EXIT_IO_ERR); }
      }
    } catch (Exception e) {
      e.printStackTrace();
      System.exit(EXIT_IO_ERR);
    }
  }

  private static boolean hasFlag(String[] args, String flag) {
    for (String a : args) if (flag.equals(a)) return true;
    return false;
  }
  private static String flagValue(String[] args, String flag) {
    for (int i = 0; i < args.length - 1; i++) if (flag.equals(args[i])) return args[i+1];
    return null;
  }
  private static List<Path> collectNonFlagPaths(String[] args, int from) {
    List<Path> t = new ArrayList<>();
    for (int i = from; i < args.length; i++) {
      String a = args[i];
      if (a.startsWith("--")) { if ("--out".equals(a) || "--json-out".equals(a)) i++; continue; }
      t.add(Paths.get(a));
    }
    return t;
  }

  // ---- helpers restored ----
  private static boolean allOk(java.util.List<FdmlValidator.Result> xs) {
    for (var r : xs) if (!r.ok) return false; return true;
  }
  private static boolean allOkSch(java.util.List<SchematronValidator.Result> xs) {
    for (var r : xs) if (!r.ok) return false; return true;
  }
  private static String esc(String s) {
    if (s == null) return null;
    return s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","");
  }
  private static String toJsonValidate(java.util.List<FdmlValidator.Result> rs) {
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
    return sb.toString();
  }
  private static String toJsonValidateSch(java.util.List<SchematronValidator.Result> rs) {
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
    return sb.toString();
  }
  private static String toJsonValidateAll(java.util.List<FdmlValidator.Result> r1,
                                          java.util.List<SchematronValidator.Result> r2) {
    StringBuilder sb = new StringBuilder();
    sb.append("{\"command\":\"validate-all\",\"xsd\":");
    StringBuilder sb1 = new StringBuilder(); sb1.append("[");
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
    StringBuilder sb2 = new StringBuilder(); sb2.append("[");
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
    return sb.toString();
  }
  private static String toJsonLint(java.util.List<Linter.FileResult> rs) {
    StringBuilder sb = new StringBuilder();
    sb.append("{\"command\":\"lint\",\"results\":[");
    for (int i=0;i<rs.size();i++) {
      var r = rs.get(i);
      sb.append("{\"file\":\"").append(esc(r.file.toString())).append("\",\"ok\":").append(r.ok()).append(",\"warnings\":[");
      for (int j=0;j<r.warnings.size();j++) {
        var w = r.warnings.get(j);
        sb.append("{\"code\":\"").append(esc(w.code)).append("\"");
        if (w.figureId != null) sb.append(",\"figure\":\"").append(esc(w.figureId)).append("\"");
        if (w.meter != null) sb.append(",\"meter\":\"").append(esc(w.meter)).append("\"");
        if (w.bars != null) sb.append(",\"bars\":\"").append(esc(w.bars)).append("\"");
        if (w.message != null) sb.append(",\"message\":\"").append(esc(w.message)).append("\"");
        sb.append(",\"beats\":").append(w.beats).append("}");
        if (j<r.warnings.size()-1) sb.append(",");
      }
      sb.append("]}");
      if (i<rs.size()-1) sb.append(",");
    }
    sb.append("]}");
    return sb.toString();
  }

  private static void usage() {
    System.out.println("FDML CLI");
    System.out.println("Usage:");
    System.out.println("  validate <path> [...] [--json] [--json-out file]");
    System.out.println("  validate-sch <path> [...] [--json] [--json-out file]");
    System.out.println("  validate-all <path> [...] [--json] [--json-out file]");
    System.out.println("  render <fdml-file> [--out out.html]");
    System.out.println("  export-pdf <fdml-file> [--out out.pdf]");
    System.out.println("  index  <path> [...] [--out out.json]");
    System.out.println("  lint   <path> [...] [--json] [--json-out file] [--strict]");
    System.out.println("  init   <output-file> [--title T] [--dance D] [--meter M/N] [--tempo BPM] [--figure-id f-...] [--figure-name NAME] [--formation FORM]");
    System.out.println("  doctor <path> [...] [--json] [--strict]");
  }
}
