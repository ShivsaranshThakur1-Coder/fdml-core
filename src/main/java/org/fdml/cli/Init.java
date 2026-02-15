package org.fdml.cli;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

class Init {
  private static final List<String> SUPPORTED_PROFILES = List.of(
    "v1-basic",
    "v12-circle",
    "v12-line",
    "v12-twoLinesFacing",
    "v12-couple"
  );

  static void run(String[] args) {
    if (args.length < 2) {
      System.err.println("init: provide <output-file> [--title T] [--dance D] [--meter M/N] [--tempo BPM] [--figure-id f-...] [--figure-name NAME] [--formation FORM] [--profile " + String.join("|", SUPPORTED_PROFILES) + "]");
      System.exit(4);
    }
    Path out = Paths.get(args[1]);
    Map<String,String> kv = parseFlags(args, 2);

    String title       = kv.getOrDefault("--title", "Untitled Routine");
    String dance       = kv.getOrDefault("--dance", "");
    String meter       = kv.getOrDefault("--meter", "4/4");
    String tempo       = kv.getOrDefault("--tempo", "112");
    String figId       = kv.getOrDefault("--figure-id", "f-basic");
    String figName     = kv.getOrDefault("--figure-name", "Basic Step");
    String formation   = kv.getOrDefault("--formation", "circle");
    String profile     = kv.getOrDefault("--profile", "").trim();

    String xml;
    if (profile.isBlank()) {
      // Keep no-profile behavior unchanged for backward compatibility.
      xml = buildLegacyV10(title, dance, meter, tempo, figId, figName, formation);
    } else {
      switch (profile) {
        case "v1-basic":
          xml = buildProfileV1Basic(title, dance, meter, tempo, figId, figName, formation);
          break;
        case "v12-circle":
          xml = buildProfileV12Circle(title, dance, meter, tempo, figId, figName, formation);
          break;
        case "v12-line":
          xml = buildProfileV12Line(title, dance, meter, tempo, figId, figName, formation);
          break;
        case "v12-twoLinesFacing":
          xml = buildProfileV12TwoLinesFacing(title, dance, meter, tempo, figId, figName, formation);
          break;
        case "v12-couple":
          xml = buildProfileV12Couple(title, dance, meter, tempo, figId, figName, formation);
          break;
        default:
          System.err.println("init: unsupported --profile '" + profile + "'. Supported: " + String.join(", ", SUPPORTED_PROFILES));
          System.exit(4);
          return;
      }
    }

    try {
      Files.createDirectories(out.getParent() == null ? Paths.get(".") : out.getParent());
      Files.writeString(out, xml, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
      System.out.println("Created: " + out);
    } catch (Exception e) {
      e.printStackTrace();
      System.exit(4);
    }
  }

  private static String buildLegacyV10(String title, String dance, String meter, String tempo, String figId, String figName, String formation) {
    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"1.0\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if (!dance.isBlank()) sb.append("    <dance name=\"").append(escape(dance)).append("\"/>\n");
    sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    sb.append("    <figure id=\"").append(escape(figId)).append("\" name=\"").append(escape(figName)).append("\" formation=\"").append(escape(formation)).append("\">\n");
    sb.append("      <step who=\"both\" action=\"Step L\" beats=\"1\" count=\"1\" startFoot=\"L\">Weight to L</step>\n");
    sb.append("      <step who=\"both\" action=\"Close R\" beats=\"1\" count=\"2\" startFoot=\"R\" endFoot=\"B\">Close R to L</step>\n");
    sb.append("      <step who=\"both\" action=\"Step L\" beats=\"1\" count=\"3\" startFoot=\"L\">Weight to L</step>\n");
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static String buildProfileV1Basic(String title, String dance, String meter, String tempo, String figId, String figName, String formation) {
    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"1.0\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if (!dance.isBlank()) sb.append("    <dance name=\"").append(escape(dance)).append("\"/>\n");
    sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    sb.append("    <figure id=\"").append(escape(figId)).append("\" name=\"").append(escape(figName)).append("\" formation=\"").append(escape(formation)).append("\">\n");
    sb.append("      <step who=\"both\" action=\"Basic\" beats=\"4\" count=\"1-4\" startFoot=\"L\">Basic phrase</step>\n");
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static String buildProfileV12Circle(String title, String dance, String meter, String tempo, String figId, String figName, String formation) {
    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"1.2\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if (!dance.isBlank()) sb.append("    <dance name=\"").append(escape(dance)).append("\"/>\n");
    sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    sb.append("    <formation text=\"").append(escape(formation)).append("\"/>\n");
    sb.append("    <geometry>\n");
    sb.append("      <formation kind=\"circle\"/>\n");
    sb.append("      <roles>\n");
    sb.append("        <role id=\"all\"/>\n");
    sb.append("        <role id=\"d1\"/>\n");
    sb.append("        <role id=\"d2\"/>\n");
    sb.append("        <role id=\"d3\"/>\n");
    sb.append("        <role id=\"d4\"/>\n");
    sb.append("      </roles>\n");
    sb.append("    </geometry>\n");
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    sb.append("    <geometry>\n");
    sb.append("      <circle>\n");
    sb.append("        <order role=\"all\">\n");
    sb.append("          <slot who=\"d1\"/>\n");
    sb.append("          <slot who=\"d2\"/>\n");
    sb.append("          <slot who=\"d3\"/>\n");
    sb.append("          <slot who=\"d4\"/>\n");
    sb.append("        </order>\n");
    sb.append("      </circle>\n");
    sb.append("    </geometry>\n");
    sb.append("    <figure id=\"").append(escape(figId)).append("\" name=\"").append(escape(figName)).append("\" formation=\"circle\">\n");
    sb.append("      <step who=\"all\" action=\"Move\" beats=\"4\" count=\"1-4\" startFoot=\"L\">\n");
    sb.append("        <geo>\n");
    sb.append("          <primitive kind=\"move\" who=\"all\"/>\n");
    sb.append("        </geo>\n");
    sb.append("      </step>\n");
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static String buildProfileV12Line(String title, String dance, String meter, String tempo, String figId, String figName, String formation) {
    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"1.2\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if (!dance.isBlank()) sb.append("    <dance name=\"").append(escape(dance)).append("\"/>\n");
    sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    sb.append("    <formation text=\"").append(escape(formation)).append("\"/>\n");
    sb.append("    <geometry>\n");
    sb.append("      <formation kind=\"line\"/>\n");
    sb.append("      <roles>\n");
    sb.append("        <role id=\"all\"/>\n");
    sb.append("        <role id=\"d1\"/>\n");
    sb.append("        <role id=\"d2\"/>\n");
    sb.append("      </roles>\n");
    sb.append("    </geometry>\n");
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    sb.append("    <geometry>\n");
    sb.append("      <line id=\"line1\">\n");
    sb.append("        <order>\n");
    sb.append("          <slot who=\"d1\"/>\n");
    sb.append("          <slot who=\"d2\"/>\n");
    sb.append("        </order>\n");
    sb.append("      </line>\n");
    sb.append("    </geometry>\n");
    sb.append("    <figure id=\"").append(escape(figId)).append("\" name=\"").append(escape(figName)).append("\" formation=\"line\">\n");
    sb.append("      <step who=\"all\" action=\"Progress\" beats=\"4\" count=\"1-4\" startFoot=\"L\">\n");
    sb.append("        <geo>\n");
    sb.append("          <primitive kind=\"progress\" who=\"all\" delta=\"1\"/>\n");
    sb.append("        </geo>\n");
    sb.append("      </step>\n");
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static String buildProfileV12TwoLinesFacing(String title, String dance, String meter, String tempo, String figId, String figName, String formation) {
    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"1.2\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if (!dance.isBlank()) sb.append("    <dance name=\"").append(escape(dance)).append("\"/>\n");
    sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    sb.append("    <formation text=\"").append(escape(formation)).append("\"/>\n");
    sb.append("    <geometry>\n");
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
    sb.append("    </geometry>\n");
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    sb.append("    <geometry>\n");
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
    sb.append("    </geometry>\n");
    sb.append("    <figure id=\"").append(escape(figId)).append("\" name=\"").append(escape(figName)).append("\" formation=\"twoLinesFacing\">\n");
    sb.append("      <step who=\"all\" action=\"Approach\" beats=\"8\" count=\"1-8\" startFoot=\"R\">\n");
    sb.append("        <geo>\n");
    sb.append("          <primitive kind=\"approach\" who=\"bride_line\"/>\n");
    sb.append("          <primitive kind=\"approach\" who=\"groom_line\"/>\n");
    sb.append("        </geo>\n");
    sb.append("      </step>\n");
    sb.append("      <step who=\"all\" action=\"Retreat\" beats=\"8\" count=\"9-16\" startFoot=\"L\">\n");
    sb.append("        <geo>\n");
    sb.append("          <primitive kind=\"retreat\" who=\"bride_line\"/>\n");
    sb.append("          <primitive kind=\"retreat\" who=\"groom_line\"/>\n");
    sb.append("        </geo>\n");
    sb.append("      </step>\n");
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static String buildProfileV12Couple(String title, String dance, String meter, String tempo, String figId, String figName, String formation) {
    StringBuilder sb = new StringBuilder();
    sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    sb.append("<fdml version=\"1.2\">\n");
    sb.append("  <meta>\n");
    sb.append("    <title>").append(escape(title)).append("</title>\n");
    if (!dance.isBlank()) sb.append("    <dance name=\"").append(escape(dance)).append("\"/>\n");
    sb.append("    <meter value=\"").append(escape(meter)).append("\"/>\n");
    sb.append("    <tempo bpm=\"").append(escape(tempo)).append("\"/>\n");
    sb.append("    <formation text=\"").append(escape(formation)).append("\"/>\n");
    sb.append("    <geometry>\n");
    sb.append("      <formation kind=\"couple\" womanSide=\"left\"/>\n");
    sb.append("      <roles>\n");
    sb.append("        <role id=\"man\"/>\n");
    sb.append("        <role id=\"woman\"/>\n");
    sb.append("      </roles>\n");
    sb.append("    </geometry>\n");
    sb.append("  </meta>\n");
    sb.append("  <body>\n");
    sb.append("    <geometry>\n");
    sb.append("      <couples>\n");
    sb.append("        <pair a=\"man\" b=\"woman\" relationship=\"partners\"/>\n");
    sb.append("      </couples>\n");
    sb.append("    </geometry>\n");
    sb.append("    <figure id=\"").append(escape(figId)).append("\" name=\"").append(escape(figName)).append("\" formation=\"couple\">\n");
    sb.append("      <step who=\"man\" action=\"Partner relation\" beats=\"4\" count=\"1-4\" startFoot=\"L\">\n");
    sb.append("        <geo>\n");
    sb.append("          <primitive kind=\"relpos\" a=\"woman\" b=\"man\" relation=\"leftOf\"/>\n");
    sb.append("        </geo>\n");
    sb.append("      </step>\n");
    sb.append("    </figure>\n");
    sb.append("  </body>\n");
    sb.append("</fdml>\n");
    return sb.toString();
  }

  private static Map<String,String> parseFlags(String[] args, int from) {
    Map<String,String> m = new HashMap<>();
    for (int i = from; i < args.length; i++) {
      String a = args[i];
      if (a.startsWith("--")) {
        String val = "";
        if (i+1 < args.length && !args[i+1].startsWith("--")) { val = args[++i]; }
        m.put(a, val);
      }
    }
    return m;
  }

  private static String escape(String s) {
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            .replace("\"","&quot;").replace("'","&apos;");
  }
}
