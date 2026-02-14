package org.fdml.cli;

import net.sf.saxon.s9api.DocumentBuilder;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.SaxonApiException;
import net.sf.saxon.s9api.XPathCompiler;
import net.sf.saxon.s9api.XdmEmptySequence;
import net.sf.saxon.s9api.XdmItem;
import net.sf.saxon.s9api.XdmNode;
import net.sf.saxon.s9api.XdmValue;

import javax.xml.transform.stream.StreamSource;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

class ExportJson {

  static String export(Path target) {
    try {
      Processor proc = new Processor(false);
      DocumentBuilder db = proc.newDocumentBuilder();
      XPathCompiler xpc = proc.newXPathCompiler();

      if (Files.isDirectory(target)) {
        List<Path> files = expandDirectory(target);
        List<Object> payloads = new ArrayList<>();
        for (Path f : files) payloads.add(exportOne(f, db, xpc));
        return toJson(payloads);
      }
      return toJson(exportOne(target, db, xpc));
    } catch (Exception e) {
      throw new RuntimeException("export-json failed: " + e.getMessage(), e);
    }
  }

  private static Map<String, Object> exportOne(Path file, DocumentBuilder db, XPathCompiler xpc) throws Exception {
    XdmNode doc = db.build(new StreamSource(file.toFile()));

    LinkedHashMap<String, Object> out = new LinkedHashMap<>();
    out.put("file", file.toString());
    out.put("meta", buildMeta(doc, xpc));
    out.put("figures", buildFigures(doc, xpc));
    out.put("topology", buildTopology(doc, xpc));
    return out;
  }

  private static Map<String, Object> buildMeta(XdmNode doc, XPathCompiler xpc) {
    LinkedHashMap<String, Object> meta = new LinkedHashMap<>();
    meta.put("version", str(xpc, "normalize-space(/fdml/@version)", doc));
    meta.put("title", str(xpc, "normalize-space(/fdml/meta/title)", doc));
    meta.put("meter", str(xpc, "normalize-space(/fdml/meta/meter/@value)", doc));
    meta.put("tempoBpm", str(xpc, "normalize-space(/fdml/meta/tempo/@bpm)", doc));
    meta.put("originCountry", str(xpc, "normalize-space(/fdml/meta/origin/@country)", doc));
    meta.put("typeGenre", str(xpc, "normalize-space(/fdml/meta/type/@genre)", doc));
    meta.put("formationText", str(xpc, "normalize-space(/fdml/meta/formation/@text)", doc));
    meta.put("formationKind", str(xpc, "normalize-space(/fdml/meta/geometry/formation/@kind)", doc));
    return meta;
  }

  private static List<Object> buildFigures(XdmNode doc, XPathCompiler xpc) {
    List<Object> figures = new ArrayList<>();
    XdmValue nodes = eval(xpc, "/fdml/body//figure", doc);
    for (XdmItem it : nodes) {
      XdmNode fig = (XdmNode) it;
      LinkedHashMap<String, Object> f = new LinkedHashMap<>();
      f.put("id", str(xpc, "string(@id)", fig));
      f.put("name", str(xpc, "string(@name)", fig));
      f.put("steps", buildSteps(fig, xpc));
      figures.add(f);
    }
    return figures;
  }

  private static List<Object> buildSteps(XdmNode fig, XPathCompiler xpc) {
    List<Object> steps = new ArrayList<>();
    XdmValue nodes = eval(xpc, ".//step", fig);
    for (XdmItem it : nodes) {
      XdmNode step = (XdmNode) it;
      LinkedHashMap<String, Object> s = new LinkedHashMap<>();
      s.put("who", str(xpc, "string(@who)", step));
      s.put("action", str(xpc, "string(@action)", step));
      s.put("beats", str(xpc, "string(@beats)", step));
      s.put("count", str(xpc, "string(@count)", step));
      s.put("direction", str(xpc, "string(@direction)", step));
      s.put("facing", str(xpc, "string(@facing)", step));
      s.put("startFoot", str(xpc, "string(@startFoot)", step));
      s.put("endFoot", str(xpc, "string(@endFoot)", step));
      s.put("text", str(xpc, "normalize-space(string-join(text(), ' '))", step));
      s.put("primitives", buildPrimitives(step, xpc));
      steps.add(s);
    }
    return steps;
  }

  private static List<Object> buildPrimitives(XdmNode step, XPathCompiler xpc) {
    List<Object> primitives = new ArrayList<>();
    XdmValue nodes = eval(xpc, "geo/primitive", step);
    for (XdmItem it : nodes) {
      XdmNode prim = (XdmNode) it;
      LinkedHashMap<String, Object> p = new LinkedHashMap<>();
      p.put("kind", str(xpc, "string(@kind)", prim));
      p.put("who", str(xpc, "string(@who)", prim));
      p.put("frame", str(xpc, "string(@frame)", prim));
      p.put("dir", str(xpc, "string(@dir)", prim));
      p.put("a", str(xpc, "string(@a)", prim));
      p.put("b", str(xpc, "string(@b)", prim));
      p.put("delta", str(xpc, "string(@delta)", prim));
      String preserve = str(xpc, "string(@preserveOrder)", prim);
      if (!preserve.isBlank()) p.put("preserveOrder", preserve);
      primitives.add(p);
    }
    return primitives;
  }

  private static Map<String, Object> buildTopology(XdmNode doc, XPathCompiler xpc) {
    LinkedHashMap<String, Object> topology = new LinkedHashMap<>();
    topology.put("circle", buildCircleTopology(doc, xpc));
    topology.put("line", buildLineTopology(doc, xpc));
    topology.put("twoLines", buildTwoLinesTopology(doc, xpc));
    return topology;
  }

  private static Map<String, Object> buildCircleTopology(XdmNode doc, XPathCompiler xpc) {
    LinkedHashMap<String, Object> circle = new LinkedHashMap<>();
    List<Object> orders = new ArrayList<>();
    XdmValue nodes = eval(xpc, "/fdml/body/geometry/circle/order", doc);
    for (XdmItem it : nodes) {
      XdmNode order = (XdmNode) it;
      LinkedHashMap<String, Object> o = new LinkedHashMap<>();
      o.put("role", str(xpc, "string(@role)", order));
      o.put("slots", readSlots(order, xpc));
      orders.add(o);
    }
    circle.put("orders", orders);
    return circle;
  }

  private static Map<String, Object> buildLineTopology(XdmNode doc, XPathCompiler xpc) {
    LinkedHashMap<String, Object> line = new LinkedHashMap<>();
    List<Object> lines = new ArrayList<>();
    XdmValue nodes = eval(xpc, "/fdml/body/geometry/line[@id]", doc);
    for (XdmItem it : nodes) {
      XdmNode lineNode = (XdmNode) it;
      LinkedHashMap<String, Object> l = new LinkedHashMap<>();
      l.put("id", str(xpc, "string(@id)", lineNode));
      List<Object> orders = new ArrayList<>();
      XdmValue orderNodes = eval(xpc, "order", lineNode);
      for (XdmItem oit : orderNodes) {
        XdmNode order = (XdmNode) oit;
        LinkedHashMap<String, Object> o = new LinkedHashMap<>();
        o.put("phase", str(xpc, "string(@phase)", order));
        o.put("slots", readSlots(order, xpc));
        orders.add(o);
      }
      l.put("orders", orders);
      lines.add(l);
    }
    line.put("lines", lines);
    return line;
  }

  private static Map<String, Object> buildTwoLinesTopology(XdmNode doc, XPathCompiler xpc) {
    LinkedHashMap<String, Object> twoLines = new LinkedHashMap<>();
    List<Object> lines = new ArrayList<>();
    twoLines.put("lines", lines);

    LinkedHashMap<String, Object> facing = new LinkedHashMap<>();
    String facingA = str(xpc, "string(/fdml/body/geometry/twoLines/facing[1]/@a)", doc);
    String facingB = str(xpc, "string(/fdml/body/geometry/twoLines/facing[1]/@b)", doc);
    facing.put("a", facingA);
    facing.put("b", facingB);
    twoLines.put("facing", facing);

    List<Object> opposites = new ArrayList<>();
    List<Object> neighbors = new ArrayList<>();
    twoLines.put("opposites", opposites);
    twoLines.put("neighbors", neighbors);

    LinkedHashMap<String, List<String>> firstOrdersByLine = new LinkedHashMap<>();

    XdmValue lineNodes = eval(xpc, "/fdml/body/geometry/twoLines/line[@id]", doc);
    for (XdmItem it : lineNodes) {
      XdmNode lineNode = (XdmNode) it;
      String lineId = str(xpc, "string(@id)", lineNode);

      LinkedHashMap<String, Object> l = new LinkedHashMap<>();
      l.put("id", lineId);
      l.put("role", str(xpc, "string(@role)", lineNode));

      List<Object> orders = new ArrayList<>();
      XdmValue orderNodes = eval(xpc, "order", lineNode);
      for (XdmItem oit : orderNodes) {
        XdmNode order = (XdmNode) oit;
        LinkedHashMap<String, Object> o = new LinkedHashMap<>();
        o.put("slots", readSlots(order, xpc));
        orders.add(o);
      }
      l.put("orders", orders);
      lines.add(l);

      if (!orders.isEmpty()) {
        @SuppressWarnings("unchecked")
        List<String> firstSlots = (List<String>) ((Map<String, Object>) orders.get(0)).get("slots");
        firstOrdersByLine.put(lineId, firstSlots);
      }
    }

    inferOpposites(firstOrdersByLine, facingA, facingB, opposites);
    inferNeighbors(firstOrdersByLine, neighbors);
    return twoLines;
  }

  private static void inferOpposites(Map<String, List<String>> firstOrdersByLine,
                                     String facingA,
                                     String facingB,
                                     List<Object> opposites) {
    if (firstOrdersByLine.size() < 2) return;
    String lineA;
    String lineB;
    List<String> ids = new ArrayList<>(firstOrdersByLine.keySet());

    if (firstOrdersByLine.containsKey(facingA) && firstOrdersByLine.containsKey(facingB)) {
      lineA = facingA;
      lineB = facingB;
    } else {
      lineA = ids.get(0);
      lineB = ids.get(1);
    }

    List<String> aOrder = firstOrdersByLine.get(lineA);
    List<String> bOrder = firstOrdersByLine.get(lineB);
    if (aOrder == null || bOrder == null || aOrder.size() != bOrder.size()) return;

    for (int i = 0; i < aOrder.size(); i++) {
      String a = aOrder.get(i);
      String b = bOrder.get(i);
      if (a == null || a.isBlank() || b == null || b.isBlank()) continue;
      LinkedHashMap<String, Object> pair = new LinkedHashMap<>();
      pair.put("a", a);
      pair.put("b", b);
      opposites.add(pair);
    }
  }

  private static void inferNeighbors(Map<String, List<String>> firstOrdersByLine, List<Object> neighbors) {
    for (Map.Entry<String, List<String>> e : firstOrdersByLine.entrySet()) {
      String lineId = e.getKey();
      List<String> slots = e.getValue();
      if (slots == null) continue;
      for (int i = 0; i + 1 < slots.size(); i++) {
        String a = slots.get(i);
        String b = slots.get(i + 1);
        if (a == null || a.isBlank() || b == null || b.isBlank()) continue;
        LinkedHashMap<String, Object> pair = new LinkedHashMap<>();
        pair.put("line", lineId);
        pair.put("a", a);
        pair.put("b", b);
        neighbors.add(pair);
      }
    }
  }

  private static List<String> readSlots(XdmNode orderNode, XPathCompiler xpc) {
    List<String> out = new ArrayList<>();
    XdmValue slots = eval(xpc, "slot/@who", orderNode);
    for (XdmItem it : slots) {
      String who = it.getStringValue();
      if (who != null && !who.isBlank()) out.add(who);
    }
    return out;
  }

  private static List<Path> expandDirectory(Path root) {
    List<Path> out = new ArrayList<>();
    try {
      Files.walk(root).filter(Files::isRegularFile).forEach(out::add);
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
    out.removeIf(p -> !looksLikeXml(p));
    out.sort(Comparator.comparing(Path::toString));
    return out;
  }

  private static boolean looksLikeXml(Path p) {
    String n = p.getFileName().toString().toLowerCase(Locale.ROOT);
    return n.endsWith(".xml") || n.endsWith(".fdml") || n.endsWith(".fdml.xml");
  }

  private static String str(XPathCompiler xpc, String expr, XdmNode node) {
    try {
      XdmItem i = xpc.evaluateSingle(expr, node);
      return i == null ? "" : i.getStringValue();
    } catch (SaxonApiException e) {
      return "";
    }
  }

  private static XdmValue eval(XPathCompiler xpc, String expr, XdmNode node) {
    try {
      return xpc.evaluate(expr, node);
    } catch (SaxonApiException e) {
      return XdmEmptySequence.getInstance();
    }
  }

  private static String toJson(Object value) {
    StringBuilder sb = new StringBuilder();
    appendJson(sb, value);
    return sb.toString();
  }

  @SuppressWarnings("unchecked")
  private static void appendJson(StringBuilder sb, Object value) {
    if (value == null) {
      sb.append("null");
      return;
    }
    if (value instanceof String) {
      sb.append("\"").append(esc((String) value)).append("\"");
      return;
    }
    if (value instanceof Boolean || value instanceof Number) {
      sb.append(value.toString());
      return;
    }
    if (value instanceof List) {
      List<Object> xs = (List<Object>) value;
      sb.append("[");
      for (int i = 0; i < xs.size(); i++) {
        appendJson(sb, xs.get(i));
        if (i < xs.size() - 1) sb.append(",");
      }
      sb.append("]");
      return;
    }
    if (value instanceof Map) {
      Map<String, Object> m = (Map<String, Object>) value;
      sb.append("{");
      int i = 0;
      for (Map.Entry<String, Object> e : m.entrySet()) {
        sb.append("\"").append(esc(e.getKey())).append("\":");
        appendJson(sb, e.getValue());
        if (i < m.size() - 1) sb.append(",");
        i++;
      }
      sb.append("}");
      return;
    }
    sb.append("\"").append(esc(String.valueOf(value))).append("\"");
  }

  private static String esc(String s) {
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "");
  }
}
