package org.fdml.cli;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.util.*;

class Indexer {
  static String buildIndex(List<Path> inputs) {
    try {
      Processor proc = new Processor(false);
      DocumentBuilder db = proc.newDocumentBuilder();
      XPathCompiler xpc = proc.newXPathCompiler();

      List<Path> files = expandAll(inputs);
      StringBuilder sb = new StringBuilder();
      sb.append("{\"items\":[");
      for (int i = 0; i < files.size(); i++) {
        Path f = files.get(i);

        // Parse XML; keep going even if one file is bad
        XdmNode doc;
        try {
          doc = db.build(new StreamSource(f.toFile()));
        } catch (SaxonApiException e) {
          sb.append("{\"file\":\"").append(esc(f.toString()))
            .append("\",\"error\":\"").append(esc(e.getMessage())).append("\"}");
          if (i < files.size() - 1) sb.append(",");
          continue;
        }

        String title = evalString(xpc, doc, "normalize-space(/fdml/meta/title)");
        String email = evalString(xpc, doc, "normalize-space(/fdml/meta/author/@email)");

        XdmValue secVals = eval(xpc, doc, "/fdml/body/section/@id/string()");
        List<String> sections = new ArrayList<>();
        if (secVals != null) for (XdmItem it : secVals) sections.add(it.getStringValue());

        sb.append("{\"file\":\"").append(esc(f.toString())).append("\"");
        if (!isEmpty(title)) sb.append(",\"title\":\"").append(esc(title)).append("\"");
        if (!isEmpty(email)) sb.append(",\"authorEmail\":\"").append(esc(email)).append("\"");
        sb.append(",\"sections\":[");
        for (int j = 0; j < sections.size(); j++) {
          sb.append("\"").append(esc(sections.get(j))).append("\"");
          if (j < sections.size() - 1) sb.append(",");
        }
        sb.append("]}");
        if (i < files.size() - 1) sb.append(",");
      }
      sb.append("]}");
      return sb.toString();
    } catch (Exception e) {
      throw new RuntimeException("Indexing failed: " + e.getMessage(), e);
    }
  }

  private static XdmValue eval(XPathCompiler xpc, XdmNode doc, String expr) {
    try { return xpc.evaluate(expr, doc); }
    catch (SaxonApiException e) { return null; }
  }

  private static String evalString(XPathCompiler xpc, XdmNode doc, String expr) {
    try {
      XdmItem item = xpc.evaluateSingle(expr, doc); // safe, no checked XPathException downstream
      return item == null ? "" : item.getStringValue();
    } catch (SaxonApiException e) {
      return "";
    }
  }

  private static List<Path> expandAll(List<Path> inputs) {
    List<Path> out = new ArrayList<>();
    for (Path p : inputs) {
      try {
        if (Files.isDirectory(p)) Files.walk(p).filter(Files::isRegularFile).forEach(out::add);
        else out.add(p);
      } catch (Exception e) { throw new RuntimeException(e); }
    }
    return out;
  }

  private static boolean isEmpty(String s) { return s == null || s.trim().isEmpty(); }
  private static String esc(String s) { return s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r",""); }
}
