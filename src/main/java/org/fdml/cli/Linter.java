package org.fdml.cli;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.util.*;

class Linter {

  static final class Warning {
    final String code;
    final String figureId;
    final String meter;
    final long beats;
    final String bars;
    final String message;
    Warning(String code, String figureId, String meter, long beats, String bars, String message) {
      this.code = code; this.figureId = figureId; this.meter = meter; this.beats = beats; this.bars = bars; this.message = message;
    }
  }

  static final class FileResult {
    final Path file;
    final List<Warning> warnings = new ArrayList<>();
    FileResult(Path f) { this.file = f; }
    boolean ok() { return warnings.isEmpty(); }
  }

  static List<FileResult> lintCollect(List<Path> inputs) {
    List<Path> files = expandAll(inputs);
    List<FileResult> out = new ArrayList<>();
    try {
      Processor proc = new Processor(false);
      DocumentBuilder db = proc.newDocumentBuilder();
      XPathCompiler xpc = proc.newXPathCompiler();

      for (Path f : files) {
        FileResult r = new FileResult(f);
        XdmNode doc;
        try {
          doc = db.build(new StreamSource(f.toFile()));
        } catch (SaxonApiException e) {
          r.warnings.add(new Warning("parse_error", null, null, 0, null, e.getMessage()));
          out.add(r);
          continue;
        }

        String meter = string(xpc, "normalize-space(/fdml/meta/meter/@value)", doc);
        Integer num = parseMeterNumerator(meter);

        XdmValue figures = eval(xpc, "/fdml/body/figure", doc);
        for (XdmItem it : figures) {
          XdmNode fig = (XdmNode) it;
          String figId = string(xpc, "string(@id)", fig);
          long beats = roundToLong(evalNumber(xpc, "number(sum(./step/@beats))", fig));
          if (num != null && num > 0) {
            long rem = beats % num;
            if (rem != 0) {
              double bars = (num == 0) ? 0.0 : (beats * 1.0 / num);
              r.warnings.add(new Warning(
                "off_meter",
                figId == null || figId.isEmpty() ? "(no-id)" : figId,
                meter,
                beats,
                String.format(java.util.Locale.ROOT, "%.2f", bars),
                "total beats not divisible by meter numerator"
              ));
            }
          }
        }

        if (meter == null || meter.isEmpty()) {
          r.warnings.add(new Warning("missing_meter", null, null, 0, null, "meta/meter/@value is missing"));
        }

        out.add(r);
      }
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
    return out;
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

  private static String string(XPathCompiler xpc, String expr, XdmNode node) {
    try { XdmItem i = xpc.evaluateSingle(expr, node); return i == null ? "" : i.getStringValue(); }
    catch (SaxonApiException e) { return ""; }
  }

  private static double evalNumber(XPathCompiler xpc, String expr, XdmNode node) {
    try { XdmItem i = xpc.evaluateSingle(expr, node); return i == null ? Double.NaN : Double.parseDouble(i.getStringValue()); }
    catch (Exception e) { return Double.NaN; }
  }

  private static long roundToLong(double d) {
    if (Double.isNaN(d) || Double.isInfinite(d)) return 0L;
    return Math.round(d);
  }

  private static Integer parseMeterNumerator(String meter) {
    if (meter == null) return null;
    int idx = meter.indexOf('/');
    if (idx <= 0) return null;
    try { return Integer.parseInt(meter.substring(0, idx).trim()); }
    catch (NumberFormatException e) { return null; }
  }

  private static XdmValue eval(XPathCompiler xpc, String expr, XdmNode node) {
    try { return xpc.evaluate(expr, node); }
    catch (SaxonApiException e) { return XdmEmptySequence.getInstance(); }
  }

  private static XdmValue eval(XPathCompiler xpc, XdmNode node, String expr) {
    try { return xpc.evaluate(expr, node); }
    catch (SaxonApiException e) { return XdmEmptySequence.getInstance(); }
  }
}
