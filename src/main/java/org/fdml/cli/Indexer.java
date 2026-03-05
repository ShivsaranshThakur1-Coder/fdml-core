package org.fdml.cli;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class Indexer {
  private static final Pattern SOURCE_ID_PATTERN =
      Pattern.compile("(?i)(?:^|#)\\s*source_id\\s*:\\s*([^#\\s]+)");
  private static final Pattern SOURCE_TITLE_PATTERN =
      Pattern.compile("(?i)(?:^|#)\\s*title\\s*:\\s*([^#]+)");
  private static final Pattern DANCE_TERMS = Pattern.compile(
      "\\b(dance|dances|dancer|dancers|dancing|step|steps|jump|jumps|hop|hops|turn|turns|line|circle|formation|rhythm|beat|beats|partner|partners|hold|holds|stomp|stomps|sway|clap|spin|spins|procession|figure|figures|chain|couple|couples|waltz|polka|dabke|folk)\\b",
      Pattern.CASE_INSENSITIVE
  );
  private static final List<Pattern> PLACEHOLDER_PATTERNS = List.of(
      Pattern.compile("^#\\s*source_id\\s*:", Pattern.CASE_INSENSITIVE),
      Pattern.compile("^Ingest filler step", Pattern.CASE_INSENSITIVE),
      Pattern.compile("^M2 Conversion", Pattern.CASE_INSENSITIVE)
  );
  private static final int STRICT_MIN_STEPS = 8;
  private static final double STRICT_MIN_NON_PLACEHOLDER_RATIO = 0.80d;
  private static final int STRICT_MIN_DANCE_LEXEME_STEPS = 4;
  private static final int STRICT_MIN_UNIQUE_NON_PLACEHOLDER_STEPS = 6;
  private static final int RELAXED_MIN_STEPS = 4;
  private static final double RELAXED_MIN_NON_PLACEHOLDER_RATIO = 0.80d;
  private static final int RELAXED_MIN_UNIQUE_NON_PLACEHOLDER_STEPS = 4;

  private static final List<Path> SOURCE_MANIFEST_PATHS = List.of(
      Paths.get("analysis/sources/web_seed_manifest.json"),
      Paths.get("analysis/sources/m5_expansion_seed_manifest.json"),
      Paths.get("analysis/sources/non_wikipedia_public_domain_manifest.json"),
      Paths.get("out/acquired_sources/merged_manifest.json")
  );
  private static final Map<String, SourceMeta> SOURCE_META_BY_ID = loadSourceMetaById();

  private static final class SourceMeta {
    final String id;
    final String title;
    final String category;

    SourceMeta(String id, String title, String category) {
      this.id = id;
      this.title = title;
      this.category = category;
    }
  }

  private static final class DescriptionProfile {
    final int steps;
    final int nonPlaceholderSteps;
    final int danceLexemeSteps;
    final int uniqueNonPlaceholderSteps;
    final boolean strict;
    final boolean relaxed;
    final String tier;

    DescriptionProfile(int steps,
                       int nonPlaceholderSteps,
                       int danceLexemeSteps,
                       int uniqueNonPlaceholderSteps,
                       boolean strict,
                       boolean relaxed,
                       String tier) {
      this.steps = steps;
      this.nonPlaceholderSteps = nonPlaceholderSteps;
      this.danceLexemeSteps = danceLexemeSteps;
      this.uniqueNonPlaceholderSteps = uniqueNonPlaceholderSteps;
      this.strict = strict;
      this.relaxed = relaxed;
      this.tier = tier;
    }
  }

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
        String version = evalString(xpc, doc, "normalize-space(/fdml/@version)");
        String meter = evalString(xpc, doc, "normalize-space(/fdml/meta/meter/@value)");
        String tempoBpm = evalString(xpc, doc, "normalize-space(/fdml/meta/tempo/@bpm)");
        String genre = evalString(xpc, doc, "normalize-space(/fdml/meta/type/@genre)");
        String formationText = evalString(xpc, doc, "normalize-space(/fdml/meta/formation/@text)");
        String formationKind = evalString(xpc, doc, "normalize-space(/fdml/meta/geometry/formation/@kind)");
        String originCountry = evalString(xpc, doc, "normalize-space(/fdml/meta/origin/@country)");
        boolean hasGeometry = evalBoolean(xpc, doc, "boolean(/fdml/meta/geometry)");
        String notesMeta = evalString(xpc, doc, "normalize-space(/fdml/body/section[@type='notes'][1]/p[1])");
        String sourceId = firstNonEmpty(extractToken(notesMeta, SOURCE_ID_PATTERN), inferSourceIdFromPath(f));
        SourceMeta sourceMeta = isEmpty(sourceId) ? null : SOURCE_META_BY_ID.get(sourceId);
        String sourceTitle = firstNonEmpty(
            extractToken(notesMeta, SOURCE_TITLE_PATTERN),
            sourceMeta == null ? "" : sourceMeta.title
        );
        String sourceCategory = sourceMeta == null ? "" : sourceMeta.category;
        List<String> stepActions = evalStringList(xpc, doc, "/fdml/body/figure/step/@action/string()");
        DescriptionProfile fullDescription = computeDescriptionProfile(stepActions);

        XdmValue secVals = eval(xpc, doc, "/fdml/body/section/@id/string()");
        List<String> sections = new ArrayList<>();
        if (secVals != null) for (XdmItem it : secVals) sections.add(it.getStringValue());

        sb.append("{\"file\":\"").append(esc(f.toString())).append("\"");
        if (!isEmpty(title)) sb.append(",\"title\":\"").append(esc(title)).append("\"");
        if (!isEmpty(email)) sb.append(",\"authorEmail\":\"").append(esc(email)).append("\"");
        sb.append(",\"version\":\"").append(esc(version)).append("\"");
        sb.append(",\"meter\":\"").append(esc(meter)).append("\"");
        sb.append(",\"tempoBpm\":\"").append(esc(tempoBpm)).append("\"");
        sb.append(",\"genre\":\"").append(esc(genre)).append("\"");
        sb.append(",\"formationText\":\"").append(esc(formationText)).append("\"");
        sb.append(",\"formationKind\":\"").append(esc(formationKind)).append("\"");
        sb.append(",\"originCountry\":\"").append(esc(originCountry)).append("\"");
        if (!isEmpty(sourceId)) sb.append(",\"sourceId\":\"").append(esc(sourceId)).append("\"");
        if (!isEmpty(sourceTitle)) sb.append(",\"sourceTitle\":\"").append(esc(sourceTitle)).append("\"");
        if (!isEmpty(sourceCategory)) sb.append(",\"sourceCategory\":\"").append(esc(sourceCategory)).append("\"");
        sb.append(",\"fullDescriptionTier\":\"").append(esc(fullDescription.tier)).append("\"");
        sb.append(",\"fullDescriptionStrict\":").append(fullDescription.strict);
        sb.append(",\"fullDescriptionRelaxed\":").append(fullDescription.relaxed);
        sb.append(",\"fullDescriptionSteps\":").append(fullDescription.steps);
        sb.append(",\"fullDescriptionNonPlaceholderSteps\":").append(fullDescription.nonPlaceholderSteps);
        sb.append(",\"fullDescriptionDanceLexemeSteps\":").append(fullDescription.danceLexemeSteps);
        sb.append(",\"fullDescriptionUniqueNonPlaceholderSteps\":").append(fullDescription.uniqueNonPlaceholderSteps);
        sb.append(",\"hasGeometry\":").append(hasGeometry);
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

  private static Map<String, SourceMeta> loadSourceMetaById() {
    Map<String, SourceMeta> out = new HashMap<>();
    for (Path manifestPath : SOURCE_MANIFEST_PATHS) {
      if (!Files.exists(manifestPath)) continue;
      try {
        String raw = Files.readString(manifestPath, StandardCharsets.UTF_8);
        Object parsed = JsonMini.parse(raw);
        if (!(parsed instanceof Map<?, ?> root)) continue;
        Object sourcesRaw = root.get("sources");
        if (!(sourcesRaw instanceof List<?> sources)) continue;
        String fallbackCategory = inferFallbackCategory(manifestPath);
        for (Object item : sources) {
          if (!(item instanceof Map<?, ?> source)) continue;
          String id = trim(asString(source.get("id")));
          if (id.isEmpty()) continue;
          String title = trim(asString(source.get("title")));
          String category = trim(asString(source.get("category")));
          if (category.isEmpty()) category = fallbackCategory;
          SourceMeta existing = out.get(id);
          if (existing == null) {
            out.put(id, new SourceMeta(id, title, category));
          } else {
            String mergedTitle = isEmpty(existing.title) ? title : existing.title;
            String mergedCategory = isEmpty(existing.category) ? category : existing.category;
            out.put(id, new SourceMeta(id, mergedTitle, mergedCategory));
          }
        }
      } catch (Exception ignored) {
        // Ignore malformed local manifests; index generation remains best-effort.
      }
    }
    return out;
  }

  private static String inferFallbackCategory(Path manifestPath) {
    String name = manifestPath.getFileName().toString();
    if ("non_wikipedia_public_domain_manifest.json".equals(name)) return "nonwiki-public-domain";
    if ("m5_expansion_seed_manifest.json".equals(name)) return "m5-expansion";
    if ("web_seed_manifest.json".equals(name)) return "seed";
    return "";
  }

  private static String inferSourceIdFromPath(Path file) {
    String name = file.getFileName().toString();
    String lower = name.toLowerCase(Locale.ROOT);
    if (lower.endsWith(".fdml.xml")) name = name.substring(0, name.length() - ".fdml.xml".length());
    else if (lower.endsWith(".xml")) name = name.substring(0, name.length() - ".xml".length());
    String prefixA = "acquired_sources__";
    String prefixB = "acquired_sources_nonwiki__";
    if (name.startsWith(prefixA)) return name.substring(prefixA.length());
    if (name.startsWith(prefixB)) return name.substring(prefixB.length());
    return "";
  }

  private static String extractToken(String notes, Pattern pattern) {
    if (isEmpty(notes)) return "";
    Matcher m = pattern.matcher(notes);
    if (!m.find()) return "";
    return trim(m.group(1));
  }

  private static String firstNonEmpty(String... values) {
    for (String v : values) {
      if (!isEmpty(v)) return trim(v);
    }
    return "";
  }

  private static String asString(Object o) {
    return o == null ? "" : String.valueOf(o);
  }

  private static DescriptionProfile computeDescriptionProfile(List<String> stepActions) {
    if (stepActions == null || stepActions.isEmpty()) {
      return new DescriptionProfile(0, 0, 0, 0, false, false, "basic");
    }
    int steps = stepActions.size();
    int nonPlaceholderSteps = 0;
    int danceLexemeSteps = 0;
    Set<String> unique = new HashSet<>();
    for (String raw : stepActions) {
      String normalized = trim(raw);
      if (normalized.isEmpty()) continue;
      if (looksLikePlaceholderStep(normalized)) continue;
      nonPlaceholderSteps++;
      unique.add(normalized.toLowerCase(Locale.ROOT));
      if (DANCE_TERMS.matcher(normalized).find()) danceLexemeSteps++;
    }
    int uniqueNonPlaceholderSteps = unique.size();
    double nonPlaceholderRatio = steps == 0 ? 0.0d : (double) nonPlaceholderSteps / (double) steps;
    boolean strict = steps >= STRICT_MIN_STEPS
        && nonPlaceholderRatio >= STRICT_MIN_NON_PLACEHOLDER_RATIO
        && danceLexemeSteps >= STRICT_MIN_DANCE_LEXEME_STEPS
        && uniqueNonPlaceholderSteps >= STRICT_MIN_UNIQUE_NON_PLACEHOLDER_STEPS;
    boolean relaxed = steps >= RELAXED_MIN_STEPS
        && nonPlaceholderRatio >= RELAXED_MIN_NON_PLACEHOLDER_RATIO
        && uniqueNonPlaceholderSteps >= RELAXED_MIN_UNIQUE_NON_PLACEHOLDER_STEPS;
    String tier = strict ? "strict" : (relaxed ? "relaxed" : "basic");
    return new DescriptionProfile(
        steps,
        nonPlaceholderSteps,
        danceLexemeSteps,
        uniqueNonPlaceholderSteps,
        strict,
        relaxed,
        tier
    );
  }

  private static boolean looksLikePlaceholderStep(String value) {
    if (isEmpty(value)) return true;
    for (Pattern p : PLACEHOLDER_PATTERNS) {
      if (p.matcher(value).find()) return true;
    }
    return false;
  }

  private static String trim(String s) {
    return s == null ? "" : s.trim();
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

  private static List<String> evalStringList(XPathCompiler xpc, XdmNode doc, String expr) {
    List<String> out = new ArrayList<>();
    XdmValue val = eval(xpc, doc, expr);
    if (val == null) return out;
    for (XdmItem item : val) {
      if (item == null) continue;
      String s = trim(item.getStringValue());
      if (!s.isEmpty()) out.add(s);
    }
    return out;
  }

  private static boolean evalBoolean(XPathCompiler xpc, XdmNode doc, String expr) {
    try {
      XdmItem item = xpc.evaluateSingle(expr, doc);
      if (item == null) return false;
      return "true".equalsIgnoreCase(item.getStringValue()) || "1".equals(item.getStringValue());
    } catch (SaxonApiException e) {
      return false;
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
