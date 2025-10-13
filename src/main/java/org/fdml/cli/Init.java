package org.fdml.cli;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

class Init {
  static void run(String[] args) {
    if (args.length < 2) {
      System.err.println("init: provide <output-file> [--title T] [--dance D] [--meter M/N] [--tempo BPM] [--figure-id f-...] [--figure-name NAME] [--formation FORM]");
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

    try {
      Files.createDirectories(out.getParent() == null ? Paths.get(".") : out.getParent());
      Files.writeString(out, sb.toString(), StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
      System.out.println("Created: " + out);
    } catch (Exception e) {
      e.printStackTrace();
      System.exit(4);
    }
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
