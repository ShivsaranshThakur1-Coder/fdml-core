package org.fdml.cli;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class Ingest {
  private static final int NOTES_PREVIEW_CHARS = 200;
  private static final Pattern STEP_LINE = Pattern.compile("^\\s*(?:\\d+\\.\\s+|-\\s+)(.+?)\\s*$");
  private static final List<String> SUPPORTED_PROFILES = List.of(
    "v1-basic",
    "v12-circle",
    "v12-line",
    "v12-twoLinesFacing",
    "v12-couple"
  );

  static int run(String[] args) {
    Map<String, String> kv = parseFlags(args, 1);
    String sourceArg = kv.getOrDefault("--source", "").trim();
    String outArg = kv.getOrDefault("--out", "").trim();
    if (sourceArg.isEmpty() || outArg.isEmpty()) {
      System.err.println("ingest: provide --source <path.txt> --out <out.fdml.xml> [--title T] [--meter M] [--tempo BPM] [--profile " + String.join("|", SUPPORTED_PROFILES) + "]");
      return 4;
    }

    String profile = kv.getOrDefault("--profile", "v1-basic").trim();
    if (!SUPPORTED_PROFILES.contains(profile)) {
      System.err.println("ingest: unsupported --profile '" + profile + "'. Supported: " + String.join(", ", SUPPORTED_PROFILES));
      return 4;
    }

    Path source = Paths.get(sourceArg);
    Path out = Paths.get(outArg);
    String sourceText;
    try {
      sourceText = Files.readString(source, StandardCharsets.UTF_8);
    } catch (Exception e) {
      System.err.println("ingest: failed to read source file: " + source + " (" + e.getMessage() + ")");
      return 4;
    }
    if (sourceText.trim().isEmpty()) {
      System.err.println("ingest: source file is empty: " + source);
      return 4;
    }

    String title = kv.getOrDefault("--title", "Ingested Routine");
    String meter = kv.getOrDefault("--meter", "4/4");
    String tempo = kv.getOrDefault("--tempo", "112");

    List<String> stepTexts = deriveStepTexts(sourceText);
    int minSteps = "v12-twoLinesFacing".equals(profile) ? 6 : 1;
    ensureMinSteps(stepTexts, minSteps);
    int barLengthCounts = parseBarLengthCounts(meter);
    if (barLengthCounts > 0) padToBarLength(stepTexts, barLengthCounts);

    String xml = buildXml(title, meter, tempo, profile, sourceText, stepTexts);

    try {
      Path parent = out.getParent();
      if (parent != null) Files.createDirectories(parent);
      Files.writeString(out, xml, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
      System.out.println("Created: " + out);
    } catch (Exception e) {
      System.err.println("ingest: failed to write output file: " + out + " (" + e.getMessage() + ")");
      return 4;
    }
    return 0;
  }

  private static void ensureMinSteps(List<String> stepTexts, int minSteps) {
    while (stepTexts.size() < minSteps) stepTexts.add("Ingest filler step " + (stepTexts.size() + 1));
  }

  private static void padToBarLength(List<String> stepTexts, int barLengthCounts) {
    while (stepTexts.size() % barLengthCounts != 0) stepTexts.add("Ingest filler step " + (stepTexts.size() + 1));
  }

  private static List<String> deriveStepTexts(String sourceText) {
    String normalized = sourceText.replace("\r\n", "\n").replace('\r', '\n');
    String[] lines = normalized.split("\n", -1);
    List<String> out = new ArrayList<>();
    for (String line : lines) {
      Matcher m = STEP_LINE.matcher(line);
      if (!m.matches()) continue;
      String snippet = collapseWhitespace(m.group(1));
      if (!snippet.isEmpty()) out.add(snippet);
    }
    if (!out.isEmpty()) return out;

    for (String line : lines) {
      String t = collapseWhitespace(line);
      if (!t.isEmpty()) {
        out.add(t);
        break;
      }
    }
    if (out.isEmpty()) out.add("Ingested step");
    return out;
  }

  private static String buildXml(String title,
                                 String meter,
                                 String tempo,
                                 String profile,
                                 String sourceText,
                                 List<String> stepTexts) {
    boolean v12 = profile.startsWith("v12-");
    String formationKind = formationForProfile(profile);
    String who = "v12-couple".equals(profile) ? "man" : "both";
    if (v12 && !"v12-couple".equals(profile)) who = "all";

    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"").append(v12 ? "1.2" : "1.0").append("\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if ("9/16".equals(meter.trim()) && v12) {
      sb.append("    <meter value=\"").append(escape(meter)).append("\" rhythmPattern=\"2+2+2+3\"/>\n");
    } else {
      sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    }
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    if (v12) {
      sb.append("    <formation text=\"").append(escape(formationKind)).append("\"/>\n");
      appendMetaGeometry(sb, profile);
    }
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    if (v12) appendBodyGeometry(sb, profile);
    sb.append("    <section type=\"notes\">\n");
    sb.append("      <p>").append(escape(notesPreview(sourceText))).append("</p>\n");
    sb.append("    </section>\n");
    sb.append("    <figure id=\"f-ingest\" name=\"Ingested Figure\" formation=\"").append(escape(formationKind)).append("\">\n");
    appendFigureSteps(sb, stepTexts, profile, who);
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static void appendFigureSteps(StringBuilder sb, List<String> stepTexts, String profile, String who) {
    for (int i = 0; i < stepTexts.size(); i++) {
      String text = stepTexts.get(i);
      String action = truncate(text, 48);
      String count = Integer.toString(i + 1);
      sb.append("      <step who=\"").append(escape(who)).append("\" action=\"").append(escape(action))
        .append("\" beats=\"1\" count=\"").append(escape(count)).append("\">");

      if ("v12-circle".equals(profile) && i == 0) {
        sb.append("\n");
        sb.append("        <geo>\n");
        sb.append("          <primitive kind=\"move\" who=\"all\"/>\n");
        sb.append("        </geo>\n");
        sb.append("        ").append(escape(text)).append("\n");
        sb.append("      </step>\n");
      } else if ("v12-line".equals(profile) && i == 0) {
        sb.append("\n");
        sb.append("        <geo>\n");
        sb.append("          <primitive kind=\"progress\" who=\"all\" delta=\"1\"/>\n");
        sb.append("        </geo>\n");
        sb.append("        ").append(escape(text)).append("\n");
        sb.append("      </step>\n");
      } else if ("v12-twoLinesFacing".equals(profile) && i < 6) {
        sb.append("\n");
        sb.append("        <geo>\n");
        if (i < 5) {
          sb.append("          <primitive kind=\"approach\" who=\"bride_line\"/>\n");
          sb.append("          <primitive kind=\"approach\" who=\"groom_line\"/>\n");
        } else {
          sb.append("          <primitive kind=\"retreat\" who=\"bride_line\"/>\n");
          sb.append("          <primitive kind=\"retreat\" who=\"groom_line\"/>\n");
        }
        sb.append("        </geo>\n");
        sb.append("        ").append(escape(text)).append("\n");
        sb.append("      </step>\n");
      } else if ("v12-couple".equals(profile) && i == 0) {
        sb.append("\n");
        sb.append("        <geo>\n");
        sb.append("          <primitive kind=\"relpos\" a=\"woman\" b=\"man\" relation=\"leftOf\"/>\n");
        sb.append("        </geo>\n");
        sb.append("        ").append(escape(text)).append("\n");
        sb.append("      </step>\n");
      } else {
        sb.append(escape(text)).append("</step>\n");
      }
    }
  }

  private static void appendMetaGeometry(StringBuilder sb, String profile) {
    sb.append("    <geometry>\n");
    if ("v12-circle".equals(profile)) {
      sb.append("      <formation kind=\"circle\"/>\n");
      sb.append("      <roles>\n");
      sb.append("        <role id=\"all\"/>\n");
      sb.append("        <role id=\"d1\"/>\n");
      sb.append("        <role id=\"d2\"/>\n");
      sb.append("        <role id=\"d3\"/>\n");
      sb.append("        <role id=\"d4\"/>\n");
      sb.append("      </roles>\n");
    } else if ("v12-line".equals(profile)) {
      sb.append("      <formation kind=\"line\"/>\n");
      sb.append("      <roles>\n");
      sb.append("        <role id=\"all\"/>\n");
      sb.append("        <role id=\"d1\"/>\n");
      sb.append("        <role id=\"d2\"/>\n");
      sb.append("      </roles>\n");
    } else if ("v12-twoLinesFacing".equals(profile)) {
      sb.append("      <formation kind=\"twoLinesFacing\"/>\n");
      sb.append("      <roles>\n");
      sb.append("        <role id=\"all\"/>\n");
      sb.append("        <role id=\"bride_line\"/>\n");
      sb.append("        <role id=\"groom_line\"/>\n");
      sb.append("        <role id=\"b1\"/>\n");
      sb.append("        <role id=\"b2\"/>\n");
      sb.append("        <role id=\"g1\"/>\n");
      sb.append("        <role id=\"g2\"/>\n");
      sb.append("      </roles>\n");
    } else if ("v12-couple".equals(profile)) {
      sb.append("      <formation kind=\"couple\" womanSide=\"left\"/>\n");
      sb.append("      <roles>\n");
      sb.append("        <role id=\"man\"/>\n");
      sb.append("        <role id=\"woman\"/>\n");
      sb.append("      </roles>\n");
    }
    sb.append("    </geometry>\n");
  }

  private static void appendBodyGeometry(StringBuilder sb, String profile) {
    sb.append("    <geometry>\n");
    if ("v12-circle".equals(profile)) {
      sb.append("      <circle>\n");
      sb.append("        <order role=\"all\">\n");
      sb.append("          <slot who=\"d1\"/>\n");
      sb.append("          <slot who=\"d2\"/>\n");
      sb.append("          <slot who=\"d3\"/>\n");
      sb.append("          <slot who=\"d4\"/>\n");
      sb.append("        </order>\n");
      sb.append("      </circle>\n");
    } else if ("v12-line".equals(profile)) {
      sb.append("      <line id=\"line1\">\n");
      sb.append("        <order>\n");
      sb.append("          <slot who=\"d1\"/>\n");
      sb.append("          <slot who=\"d2\"/>\n");
      sb.append("        </order>\n");
      sb.append("      </line>\n");
    } else if ("v12-twoLinesFacing".equals(profile)) {
      sb.append("      <twoLines>\n");
      sb.append("        <line id=\"bride_line\" role=\"bride_line\">\n");
      sb.append("          <order>\n");
      sb.append("            <slot who=\"b1\"/>\n");
      sb.append("            <slot who=\"b2\"/>\n");
      sb.append("          </order>\n");
      sb.append("        </line>\n");
      sb.append("        <line id=\"groom_line\" role=\"groom_line\">\n");
      sb.append("          <order>\n");
      sb.append("            <slot who=\"g1\"/>\n");
      sb.append("            <slot who=\"g2\"/>\n");
      sb.append("          </order>\n");
      sb.append("        </line>\n");
      sb.append("        <facing a=\"bride_line\" b=\"groom_line\"/>\n");
      sb.append("      </twoLines>\n");
    } else if ("v12-couple".equals(profile)) {
      sb.append("      <couples>\n");
      sb.append("        <pair a=\"man\" b=\"woman\" relationship=\"partners\"/>\n");
      sb.append("      </couples>\n");
    }
    sb.append("    </geometry>\n");
  }

  private static String formationForProfile(String profile) {
    if ("v12-circle".equals(profile)) return "circle";
    if ("v12-line".equals(profile)) return "line";
    if ("v12-twoLinesFacing".equals(profile)) return "twoLinesFacing";
    if ("v12-couple".equals(profile)) return "couple";
    return "ingest";
  }

  private static int parseBarLengthCounts(String meterRaw) {
    if (meterRaw == null) return 0;
    String meter = meterRaw.trim();
    int slash = meter.indexOf('/');
    if (slash <= 0 || slash != meter.lastIndexOf('/')) return 0;
    String numPart = meter.substring(0, slash).trim();
    String denPart = meter.substring(slash + 1).trim();
    Integer den = parsePositiveInt(denPart);
    if (den == null) return 0;

    String[] tokens = numPart.split("\\+");
    if (tokens.length == 0) return 0;
    int total = 0;
    for (String tok : tokens) {
      Integer n = parsePositiveInt(tok.trim());
      if (n == null) return 0;
      total += n;
    }
    if (tokens.length > 1) return tokens.length;
    if (total == 9 && den == 16) return 4;
    return total;
  }

  private static Integer parsePositiveInt(String s) {
    if (s == null || s.isBlank()) return null;
    try {
      int v = Integer.parseInt(s.trim());
      return v > 0 ? v : null;
    } catch (NumberFormatException e) {
      return null;
    }
  }

  private static String notesPreview(String source) {
    String normalized = source.replace("\r\n", "\n").replace('\r', '\n');
    int n = Math.min(NOTES_PREVIEW_CHARS, normalized.length());
    return collapseWhitespace(normalized.substring(0, n));
  }

  private static String truncate(String s, int max) {
    if (s == null) return "";
    String t = s.trim();
    return t.length() <= max ? t : t.substring(0, max);
  }

  private static String collapseWhitespace(String s) {
    if (s == null) return "";
    return s.replaceAll("\\s+", " ").trim();
  }

  private static Map<String, String> parseFlags(String[] args, int from) {
    Map<String, String> m = new HashMap<>();
    for (int i = from; i < args.length; i++) {
      String a = args[i];
      if (!a.startsWith("--")) continue;
      String val = "";
      if (i + 1 < args.length && !args[i + 1].startsWith("--")) val = args[++i];
      m.put(a, val);
    }
    return m;
  }

  private static String escape(String s) {
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
      .replace("\"", "&quot;").replace("'", "&apos;");
  }
}
