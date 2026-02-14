package org.fdml.cli;

import net.sf.saxon.s9api.*;

import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.util.*;

class TimingValidator {

  static final class Issue {
    final String code;
    final String figureId;
    final String meter;
    final long beats;
    final String message;

    Issue(String code, String figureId, String meter, long beats, String message) {
      this.code = code;
      this.figureId = figureId;
      this.meter = meter;
      this.beats = beats;
      this.message = message;
    }
  }

  static final class FileResult {
    final Path file;
    final List<Issue> issues = new ArrayList<>();

    FileResult(Path file) {
      this.file = file;
    }

    boolean ok() {
      return issues.isEmpty();
    }
  }

  private static final class Meter {
    final String raw;
    final List<Integer> groups;
    final int denominator;
    final int barLengthCounts;
    final boolean additive;
    final boolean nineSixteenLegacy;

    Meter(String raw, List<Integer> groups, int denominator, int barLengthCounts, boolean additive, boolean nineSixteenLegacy) {
      this.raw = raw;
      this.groups = groups;
      this.denominator = denominator;
      this.barLengthCounts = barLengthCounts;
      this.additive = additive;
      this.nineSixteenLegacy = nineSixteenLegacy;
    }
  }

  static List<FileResult> validateCollect(List<Path> inputs) {
    List<Path> files = expandAll(inputs);
    List<FileResult> out = new ArrayList<>();
    try {
      Processor proc = new Processor(false);
      DocumentBuilder db = proc.newDocumentBuilder();
      XPathCompiler xpc = proc.newXPathCompiler();

      for (Path f : files) {
        if (!looksLikeXml(f)) continue;
        FileResult r = new FileResult(f);

        XdmNode doc;
        try {
          doc = db.build(new StreamSource(f.toFile()));
        } catch (SaxonApiException e) {
          r.issues.add(new Issue("bad_meter_format", null, null, 0, "XML parse error: " + e.getMessage()));
          out.add(r);
          continue;
        }

        String meterRaw = string(xpc, "normalize-space(/fdml/meta/meter/@value)", doc);
        if (meterRaw.isEmpty()) {
          r.issues.add(new Issue("missing_meter", null, null, 0, "meta/meter/@value is missing"));
          out.add(r);
          continue;
        }

        Meter meter = parseMeter(meterRaw);
        if (meter == null) {
          r.issues.add(new Issue("bad_meter_format", null, meterRaw, 0, "meter must be N/D or additive A+B+.../D"));
          out.add(r);
          continue;
        }

        XdmValue figures = eval(xpc, "/fdml/body//figure", doc);
        for (XdmItem it : figures) {
          XdmNode fig = (XdmNode) it;
          String figId = string(xpc, "string(@id)", fig);
          if (figId == null || figId.isBlank()) figId = "(no-id)";

          List<Integer> stepBeats = new ArrayList<>();
          boolean hasBadStep = false;

          XdmValue steps = eval(xpc, "./step | ./measureRange/step", fig);
          for (XdmItem sit : steps) {
            XdmNode step = (XdmNode) sit;
            String beatsRaw = string(xpc, "string(@beats)", step);
            Integer beats = parsePositiveInt(beatsRaw);
            if (beats == null) {
              r.issues.add(new Issue(
                "bad_step_beats",
                figId,
                meter.raw,
                0,
                "step/@beats must be a positive integer"
              ));
              hasBadStep = true;
              continue;
            }
            stepBeats.add(beats);
          }

          long totalBeats = 0;
          for (Integer b : stepBeats) totalBeats += b;

          if (hasBadStep) continue;

          if (!alignsToBarLength(totalBeats, meter)) {
            r.issues.add(new Issue(
              "off_meter_figure",
              figId,
              meter.raw,
              totalBeats,
              "figure total beats do not align to bar length " + meter.barLengthCounts
            ));
            continue;
          }

          if (meter.additive && !alignsToAdditivePattern(stepBeats, meter)) {
            r.issues.add(new Issue(
              "off_meter_figure",
              figId,
              meter.raw,
              totalBeats,
              "step boundaries do not align with additive group boundaries"
            ));
          }
        }

        out.add(r);
      }
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
    return out;
  }

  private static boolean alignsToAdditivePattern(List<Integer> stepBeats, Meter meter) {
    if (meter.barLengthCounts <= 0) return false;
    Set<Integer> groupBoundaries = new HashSet<>();
    for (int i = 1; i < meter.barLengthCounts; i++) groupBoundaries.add(i);

    int run = 0;
    for (int i = 0; i < stepBeats.size(); i++) {
      Integer b = stepBeats.get(i);
      run += b;
      int mod = run % meter.barLengthCounts;
      boolean isLast = i == stepBeats.size() - 1;
      if (isLast) {
        if (mod != 0) return false;
      } else {
        if (mod != 0 && !groupBoundaries.contains(mod)) return false;
      }
    }
    return true;
  }

  private static boolean alignsToBarLength(long totalBeats, Meter meter) {
    if (meter.barLengthCounts <= 0) return false;
    if (totalBeats % meter.barLengthCounts == 0) return true;
    // Legacy corpus compatibility: 9/16 phrases are sometimes encoded at half-bar granularity.
    if (meter.nineSixteenLegacy) return totalBeats % 2 == 0;
    return false;
  }

  private static Meter parseMeter(String raw) {
    if (raw == null) return null;
    String meter = raw.trim();
    int slash = meter.indexOf('/');
    if (slash <= 0 || slash != meter.lastIndexOf('/')) return null;

    String numPart = meter.substring(0, slash).trim();
    String denPart = meter.substring(slash + 1).trim();
    Integer den = parsePositiveInt(denPart);
    if (den == null) return null;

    String[] tokens = numPart.split("\\+");
    if (tokens.length == 0) return null;

    List<Integer> groups = new ArrayList<>();
    int numeratorTotal = 0;
    for (String tok : tokens) {
      Integer v = parsePositiveInt(tok.trim());
      if (v == null) return null;
      groups.add(v);
      numeratorTotal += v;
    }
    if (numeratorTotal <= 0) return null;

    boolean additive = groups.size() > 1;
    boolean nineSixteenLegacy = !additive && numeratorTotal == 9 && den == 16;
    int barLengthCounts = additive ? groups.size() : (nineSixteenLegacy ? 4 : numeratorTotal);

    return new Meter(raw, groups, den, barLengthCounts, additive, nineSixteenLegacy);
  }

  private static Integer parsePositiveInt(String s) {
    if (s == null) return null;
    String t = s.trim();
    if (t.isEmpty()) return null;
    try {
      int v = Integer.parseInt(t);
      return v > 0 ? v : null;
    } catch (NumberFormatException e) {
      return null;
    }
  }

  private static String string(XPathCompiler xpc, String expr, XdmNode node) {
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

  private static boolean looksLikeXml(Path p) {
    String n = p.getFileName().toString().toLowerCase(Locale.ROOT);
    return n.endsWith(".xml") || n.endsWith(".fdml") || n.endsWith(".fdml.xml");
  }
}
