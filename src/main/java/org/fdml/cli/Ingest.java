package org.fdml.cli;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class Ingest {
  private static final int NOTES_PREVIEW_CHARS = 200;
  private static final int MAX_PROSE_STEPS = 24;
  private static final int MIN_PROSE_STEP_CHARS = 20;
  private static final int MAX_PROSE_STEP_CHARS = 220;
  private static final Pattern STEP_LINE = Pattern.compile("^\\s*(?:\\d+\\.\\s+|-\\s+)(.+?)\\s*$", Pattern.MULTILINE);
  private static final Pattern FIRST_NON_EMPTY_LINE = Pattern.compile("^\\s*\\S.*$", Pattern.MULTILINE);
  private static final Pattern NON_HEADER_NON_EMPTY_LINE = Pattern.compile("(?m)^(?!\\s*#)\\s*\\S.*$");
  private static final Pattern SENTENCE_PATTERN = Pattern.compile("(?s)([^.!?\\n][^.!?]{10,320}[.!?])");
  private static final Pattern DANCE_TERMS = Pattern.compile(
    "\\b(dance|dances|dancer|dancers|dancing|step|steps|jump|jumps|hop|hops|turn|turns|line|circle|formation|rhythm|beat|beats|partner|partners|hold|holds|stomp|stomps|sway|clap|spin|spins|procession|figure|figures|chain|couple|couples|waltz|polka|dabke|folk)\\b",
    Pattern.CASE_INSENSITIVE
  );
  private static final Pattern BOILERPLATE_TERMS = Pattern.compile(
    "\\b(project gutenberg|ebook|release date|credits|copyright|license|isbn|references|bibliography|external links|all rights reserved|transcriber|proofreading team)\\b",
    Pattern.CASE_INSENSITIVE
  );
  private static final List<String> SUPPORTED_PROFILES = List.of(
    "v1-basic",
    "v12-circle",
    "v12-line",
    "v12-twoLinesFacing",
    "v12-couple"
  );

  private static final class ExtractedStep {
    final String normalizedText;
    final String sourceSnippet;
    final int sourceStart;
    final int sourceEnd;

    ExtractedStep(String normalizedText, String sourceSnippet, int sourceStart, int sourceEnd) {
      this.normalizedText = normalizedText;
      this.sourceSnippet = sourceSnippet;
      this.sourceStart = sourceStart;
      this.sourceEnd = sourceEnd;
    }
  }

  private static final class SentenceCandidate {
    final String normalizedText;
    final String sourceSnippet;
    final int sourceStart;
    final int sourceEnd;
    final int score;

    SentenceCandidate(String normalizedText, String sourceSnippet, int sourceStart, int sourceEnd, int score) {
      this.normalizedText = normalizedText;
      this.sourceSnippet = sourceSnippet;
      this.sourceStart = sourceStart;
      this.sourceEnd = sourceEnd;
      this.score = score;
    }
  }

  private static final class DoctorStatus {
    boolean xsdOk;
    boolean schematronOk;
    boolean lintOk;
    boolean timingOk;
    boolean geometryOk;
    boolean strictOk;
  }

  private static final class SchemaStatus {
    boolean ok;
    int exitCode;
  }

  private static final class BatchItem {
    String sourcePath;
    String fdmlPath;
    String provenancePath;
    String enrichmentReportPath;
    int ingestExitCode;
    DoctorStatus doctor = emptyDoctorStatus();
    SchemaStatus provenanceSchema = emptySchemaStatus();
    SchemaStatus enrichmentSchema = emptySchemaStatus();
    final List<String> errors = new ArrayList<>();
  }

  static int run(String[] args) {
    Map<String, String> kv = parseFlags(args, 1);
    String sourceArg = kv.getOrDefault("--source", "").trim();
    String outArg = kv.getOrDefault("--out", "").trim();
    if (sourceArg.isEmpty() || outArg.isEmpty()) {
      System.err.println("ingest: provide --source <path.txt> --out <out.fdml.xml> [--title T] [--meter M] [--tempo BPM] [--profile " + String.join("|", SUPPORTED_PROFILES) + "] [--provenance-out file.json] [--enable-enrichment] [--env-file .env] [--enrichment-report file.json]");
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
    String provenanceOutArg = kv.getOrDefault("--provenance-out", "").trim();
    String enrichmentReportArg = kv.getOrDefault("--enrichment-report", "").trim();
    boolean enableEnrichment = kv.containsKey("--enable-enrichment");
    String envFile = kv.getOrDefault("--env-file", ".env").trim();

    List<ExtractedStep> extractedSteps = deriveExtractedSteps(sourceText);
    Enrichment.Result enrichment = Enrichment.apply(sourceText, envFile, enableEnrichment);

    List<String> stepTexts = new ArrayList<>();
    List<ExtractedStep> extractionSeed = extractedSteps;
    if (!enrichment.effectiveText.equals(sourceText)) extractionSeed = deriveExtractedSteps(enrichment.effectiveText);
    for (ExtractedStep s : extractionSeed) stepTexts.add(s.normalizedText);
    if (!enrichment.suggestedSteps.isEmpty()) {
      stepTexts.clear();
      stepTexts.addAll(enrichment.suggestedSteps);
    }
    int minSteps = "v12-twoLinesFacing".equals(profile) ? 6 : 1;
    ensureMinSteps(stepTexts, minSteps);
    int barLengthCounts = parseBarLengthCounts(meter);
    if (barLengthCounts > 0) padToBarLength(stepTexts, barLengthCounts);

    String xml = buildXml(title, meter, tempo, profile, sourceText, stepTexts, enrichment.notes);

    try {
      Path parent = out.getParent();
      if (parent != null) Files.createDirectories(parent);
      Files.writeString(out, xml, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
      System.out.println("Created: " + out);
    } catch (Exception e) {
      System.err.println("ingest: failed to write output file: " + out + " (" + e.getMessage() + ")");
      return 4;
    }

    if (!enrichmentReportArg.isBlank()) {
      Path enrichmentReportOut = Paths.get(enrichmentReportArg);
      String enrichmentJson = enrichment.toReportJson(source.toString()) + "\n";
      try {
        Path parent = enrichmentReportOut.getParent();
        if (parent != null) Files.createDirectories(parent);
        Files.writeString(enrichmentReportOut, enrichmentJson, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
        System.out.println("Created: " + enrichmentReportOut);
      } catch (Exception e) {
        System.err.println("ingest: failed to write enrichment report file: " + enrichmentReportOut + " (" + e.getMessage() + ")");
        return 4;
      }
    }

    if (!provenanceOutArg.isBlank()) {
      Path provenanceOut = Paths.get(provenanceOutArg);
      String provenanceJson = buildProvenanceJson(source.toString(), sourceText, extractedSteps);
      try {
        Path parent = provenanceOut.getParent();
        if (parent != null) Files.createDirectories(parent);
        Files.writeString(provenanceOut, provenanceJson, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
        System.out.println("Created: " + provenanceOut);
      } catch (Exception e) {
        System.err.println("ingest: failed to write provenance file: " + provenanceOut + " (" + e.getMessage() + ")");
        return 4;
      }
    }
    return 0;
  }

  static int runBatch(String[] args) {
    Map<String, String> kv = parseFlags(args, 1);
    String sourceDirArg = kv.getOrDefault("--source-dir", "").trim();
    String outDirArg = kv.getOrDefault("--out-dir", "").trim();
    if (sourceDirArg.isEmpty() || outDirArg.isEmpty()) {
      System.err.println("ingest-batch: provide --source-dir <dir> --out-dir <dir> [--title-prefix T] [--meter M] [--tempo BPM] [--profile " + String.join("|", SUPPORTED_PROFILES) + "] [--enable-enrichment] [--env-file .env] [--index-out out.json]");
      return 4;
    }

    String profile = kv.getOrDefault("--profile", "v1-basic").trim();
    if (!SUPPORTED_PROFILES.contains(profile)) {
      System.err.println("ingest-batch: unsupported --profile '" + profile + "'. Supported: " + String.join(", ", SUPPORTED_PROFILES));
      return 4;
    }

    Path sourceDir = Paths.get(sourceDirArg);
    Path outDir = Paths.get(outDirArg);
    if (!Files.isDirectory(sourceDir)) {
      System.err.println("ingest-batch: --source-dir is not a directory: " + sourceDir);
      return 4;
    }
    String titlePrefix = kv.getOrDefault("--title-prefix", "Ingest Batch");
    String meter = kv.getOrDefault("--meter", "4/4");
    String tempo = kv.getOrDefault("--tempo", "112");
    boolean enableEnrichment = kv.containsKey("--enable-enrichment");
    String envFile = kv.getOrDefault("--env-file", ".env").trim();
    Path indexOut = Paths.get(kv.getOrDefault("--index-out", outDir.resolve("index.json").toString()).trim());

    List<Path> sourceFiles;
    try (var stream = Files.list(sourceDir)) {
      sourceFiles = stream
        .filter(Files::isRegularFile)
        .filter(p -> p.getFileName().toString().toLowerCase(java.util.Locale.ROOT).endsWith(".txt"))
        .sorted(Comparator.comparing(p -> p.getFileName().toString()))
        .toList();
    } catch (Exception e) {
      System.err.println("ingest-batch: failed to list source dir: " + sourceDir + " (" + e.getMessage() + ")");
      return 4;
    }
    if (sourceFiles.isEmpty()) {
      System.err.println("ingest-batch: no .txt files found in: " + sourceDir);
      return 4;
    }

    List<BatchItem> items = new ArrayList<>();
    int failed = 0;
    for (Path sourceFile : sourceFiles) {
      String fileName = sourceFile.getFileName().toString();
      String stem = fileName.toLowerCase(java.util.Locale.ROOT).endsWith(".txt")
        ? fileName.substring(0, fileName.length() - 4)
        : fileName;
      Path outXml = outDir.resolve(stem + ".fdml.xml");
      Path outProv = outDir.resolve(stem + ".provenance.json");
      Path outEnrich = outDir.resolve(stem + ".enrichment-report.json");

      String title = titlePrefix == null || titlePrefix.isBlank() ? stem : titlePrefix + " - " + stem;
      List<String> one = new ArrayList<>();
      one.add("ingest");
      one.add("--source");
      one.add(sourceFile.toString());
      one.add("--out");
      one.add(outXml.toString());
      one.add("--title");
      one.add(title);
      one.add("--meter");
      one.add(meter);
      one.add("--tempo");
      one.add(tempo);
      one.add("--profile");
      one.add(profile);
      one.add("--provenance-out");
      one.add(outProv.toString());
      one.add("--enrichment-report");
      one.add(outEnrich.toString());
      if (enableEnrichment) one.add("--enable-enrichment");
      one.add("--env-file");
      one.add(envFile);

      BatchItem item = new BatchItem();
      item.sourcePath = sourceFile.toString();
      item.fdmlPath = outXml.toString();
      item.provenancePath = outProv.toString();
      item.enrichmentReportPath = outEnrich.toString();

      int ingestCode = run(one.toArray(new String[0]));
      item.ingestExitCode = ingestCode;
      if (ingestCode != 0) {
        item.errors.add("ingest_failed");
        failed++;
        items.add(item);
        continue;
      }

      DoctorStatus doctor = doctorStrictStatus(outXml);
      item.doctor = doctor;
      if (!doctor.strictOk) item.errors.add("doctor_strict_failed");

      SchemaStatus provSchema = runSchemaValidation(Paths.get("schema/provenance.schema.json"), outProv);
      item.provenanceSchema = provSchema;
      if (!provSchema.ok) item.errors.add("provenance_schema_failed");

      SchemaStatus enrichSchema = runSchemaValidation(Paths.get("schema/enrichment-report.schema.json"), outEnrich);
      item.enrichmentSchema = enrichSchema;
      if (!enrichSchema.ok) item.errors.add("enrichment_schema_failed");

      if (!item.errors.isEmpty()) failed++;
      items.add(item);
    }

    String summary = buildBatchIndexJson(sourceDir, outDir, items);
    try {
      Path parent = indexOut.getParent();
      if (parent != null) Files.createDirectories(parent);
      Files.writeString(indexOut, summary, StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
      System.out.println("Created: " + indexOut);
      int ok = items.size() - failed;
      System.out.println("INGEST-BATCH SUMMARY");
      System.out.println("  total : " + items.size());
      System.out.println("  ok    : " + ok);
      System.out.println("  failed: " + failed);
    } catch (Exception e) {
      System.err.println("ingest-batch: failed to write index output: " + indexOut + " (" + e.getMessage() + ")");
      return 4;
    }

    return failed == 0 ? 0 : 2;
  }

  private static List<ExtractedStep> deriveExtractedSteps(String sourceText) {
    List<ExtractedStep> out = new ArrayList<>();
    int bodyStart = firstBodyContentOffset(sourceText);
    String bodyText = sourceText.substring(bodyStart);

    Matcher m = STEP_LINE.matcher(bodyText);
    while (m.find()) {
      int start = bodyStart + m.start(1);
      int end = bodyStart + m.end(1);
      if (start < 0 || end < start || end > sourceText.length()) continue;
      String snippet = sourceText.substring(start, end);
      String normalized = collapseWhitespace(snippet);
      if (!normalized.isEmpty() && !looksLikePlaceholderStep(normalized)) {
        out.add(new ExtractedStep(normalized, snippet, start, end));
      }
    }
    if (!out.isEmpty()) return out;

    List<SentenceCandidate> sentenceCandidates = extractSentenceCandidates(sourceText, bodyStart);
    if (!sentenceCandidates.isEmpty()) {
      // Prefer dance-relevant prose first.
      for (SentenceCandidate c : sentenceCandidates) {
        if (c.score <= 0) continue;
        out.add(new ExtractedStep(c.normalizedText, c.sourceSnippet, c.sourceStart, c.sourceEnd));
        if (out.size() >= MAX_PROSE_STEPS) return out;
      }
      // Backfill with informative non-boilerplate prose if relevance matches are scarce.
      for (SentenceCandidate c : sentenceCandidates) {
        if (c.score > 0) continue;
        out.add(new ExtractedStep(c.normalizedText, c.sourceSnippet, c.sourceStart, c.sourceEnd));
        if (out.size() >= MAX_PROSE_STEPS) return out;
      }
      if (!out.isEmpty()) return out;
    }

    Matcher first = FIRST_NON_EMPTY_LINE.matcher(bodyText);
    if (first.find()) {
      int start = bodyStart + first.start();
      int end = bodyStart + first.end();
      String snippet = sourceText.substring(start, end);
      String normalized = collapseWhitespace(snippet);
      if (!normalized.isEmpty()) out.add(new ExtractedStep(normalized, snippet, start, end));
    }

    if (out.isEmpty()) out.add(new ExtractedStep("Ingested step", "Ingested step", 0, 13));
    return out;
  }

  private static List<SentenceCandidate> extractSentenceCandidates(String sourceText, int bodyStart) {
    List<SentenceCandidate> out = new ArrayList<>();
    String bodyText = sourceText.substring(bodyStart);
    Matcher m = SENTENCE_PATTERN.matcher(bodyText);
    java.util.LinkedHashSet<String> seen = new java.util.LinkedHashSet<>();
    while (m.find()) {
      int start = bodyStart + m.start(1);
      int end = bodyStart + m.end(1);
      if (start < 0 || end <= start || end > sourceText.length()) continue;
      String snippet = sourceText.substring(start, end);
      String normalized = collapseWhitespace(snippet.replace('\uFEFF', ' ').trim());
      if (normalized.length() < MIN_PROSE_STEP_CHARS || normalized.length() > MAX_PROSE_STEP_CHARS) continue;
      if (!looksLikeInformativeSentence(normalized)) continue;
      String key = normalized.toLowerCase(java.util.Locale.ROOT);
      if (!seen.add(key)) continue;
      out.add(new SentenceCandidate(normalized, snippet, start, end, scoreDanceRelevance(normalized)));
      if (out.size() >= MAX_PROSE_STEPS * 3) break;
    }
    return out;
  }

  private static int firstBodyContentOffset(String sourceText) {
    Matcher m = NON_HEADER_NON_EMPTY_LINE.matcher(sourceText);
    if (m.find()) return m.start();
    return 0;
  }

  private static boolean looksLikeInformativeSentence(String sentence) {
    if (sentence == null || sentence.isBlank()) return false;
    String s = sentence.trim();
    if (s.startsWith("==") || s.startsWith("=")) return false;
    String lower = s.toLowerCase(java.util.Locale.ROOT);
    if (lower.contains("http://") || lower.contains("https://") || lower.contains("www.")) return false;
    if (BOILERPLATE_TERMS.matcher(lower).find()) return false;
    if (!containsLetter(s)) return false;
    return !looksLikePlaceholderStep(s);
  }

  private static int scoreDanceRelevance(String sentence) {
    int score = 0;
    Matcher m = DANCE_TERMS.matcher(sentence);
    while (m.find()) score++;
    String lower = sentence.toLowerCase(java.util.Locale.ROOT);
    if (lower.contains("traditional")) score++;
    if (lower.contains("performed")) score++;
    if (lower.contains("rhythm")) score++;
    if (lower.contains("formation")) score++;
    return score;
  }

  private static boolean containsLetter(String s) {
    for (int i = 0; i < s.length(); i++) {
      if (Character.isLetter(s.charAt(i))) return true;
    }
    return false;
  }

  private static boolean looksLikePlaceholderStep(String normalized) {
    String lower = normalized.toLowerCase(java.util.Locale.ROOT);
    return lower.startsWith("# source_id:")
      || lower.startsWith("ingest filler step")
      || lower.startsWith("m2 conversion");
  }

  private static String buildProvenanceJson(String sourcePath, String sourceText, List<ExtractedStep> steps) {
    String sha = sha256Hex(sourceText);
    StringBuilder sb = new StringBuilder();
    sb.append("{");
    sb.append("\"sourcePath\":\"").append(jsonEscape(sourcePath)).append("\",");
    sb.append("\"sourceSha256\":\"").append(sha).append("\",");
    sb.append("\"steps\":[");
    for (int i = 0; i < steps.size(); i++) {
      ExtractedStep s = steps.get(i);
      if (i > 0) sb.append(",");
      sb.append("{");
      sb.append("\"figureId\":\"f-ingest\",");
      sb.append("\"stepIndex\":").append(i + 1).append(",");
      sb.append("\"action\":\"").append(jsonEscape(s.normalizedText)).append("\",");
      sb.append("\"beats\":1,");
      sb.append("\"sourceSpan\":{");
      sb.append("\"start\":").append(s.sourceStart).append(",");
      sb.append("\"end\":").append(s.sourceEnd);
      sb.append("},");
      sb.append("\"sourceSnippet\":\"").append(jsonEscape(s.sourceSnippet)).append("\"");
      sb.append("}");
    }
    sb.append("]}");
    return sb.toString();
  }

  private static DoctorStatus doctorStrictStatus(Path fdmlPath) {
    DoctorStatus s = emptyDoctorStatus();
    List<Path> targets = List.of(fdmlPath);

    FdmlValidator v = new FdmlValidator(Paths.get("schema/fdml.xsd"));
    SchematronValidator sch = new SchematronValidator(Paths.get("schematron/fdml-compiled.xsl"));
    var rX = v.validateCollect(targets);
    var rS = sch.validateCollect(targets);
    var rL = Linter.lintCollect(targets);
    var rT = TimingValidator.validateCollect(targets);
    var rG = GeometryValidator.validateCollect(targets);

    s.xsdOk = true;
    for (var r : rX) if (!r.ok) { s.xsdOk = false; break; }
    s.schematronOk = true;
    for (var r : rS) if (!r.ok) { s.schematronOk = false; break; }
    s.lintOk = true;
    for (var r : rL) if (!r.ok()) { s.lintOk = false; break; }
    s.timingOk = true;
    for (var r : rT) if (!r.ok()) { s.timingOk = false; break; }
    s.geometryOk = true;
    for (var r : rG) if (!r.ok) { s.geometryOk = false; break; }
    s.strictOk = s.xsdOk && s.schematronOk && s.lintOk && s.timingOk && s.geometryOk;
    return s;
  }

  private static SchemaStatus runSchemaValidation(Path schemaPath, Path instancePath) {
    SchemaStatus s = emptySchemaStatus();
    if (!Files.exists(instancePath)) {
      s.ok = false;
      s.exitCode = 2;
      return s;
    }
    try {
      Process p = new ProcessBuilder(
        List.of("python3", "scripts/validate_json_schema.py", schemaPath.toString(), instancePath.toString())
      ).redirectErrorStream(true).start();
      try (var in = p.getInputStream()) {
        while (in.read() != -1) {
          // consume output to avoid blocking
        }
      }
      s.exitCode = p.waitFor();
      s.ok = s.exitCode == 0;
      return s;
    } catch (Exception e) {
      s.ok = false;
      s.exitCode = 2;
      return s;
    }
  }

  private static String buildBatchIndexJson(Path sourceDir, Path outDir, List<BatchItem> items) {
    int failed = 0;
    for (BatchItem item : items) if (!item.errors.isEmpty()) failed++;
    int ok = items.size() - failed;

    StringBuilder sb = new StringBuilder();
    sb.append("{");
    sb.append("\"sourceDir\":\"").append(jsonEscape(sourceDir.toString())).append("\",");
    sb.append("\"outDir\":\"").append(jsonEscape(outDir.toString())).append("\",");
    sb.append("\"total\":").append(items.size()).append(",");
    sb.append("\"ok\":").append(ok).append(",");
    sb.append("\"failed\":").append(failed).append(",");
    sb.append("\"items\":[");
    for (int i = 0; i < items.size(); i++) {
      BatchItem item = items.get(i);
      if (i > 0) sb.append(",");
      sb.append("{");
      sb.append("\"source\":\"").append(jsonEscape(item.sourcePath)).append("\",");
      sb.append("\"outputs\":{");
      sb.append("\"fdml\":\"").append(jsonEscape(item.fdmlPath)).append("\",");
      sb.append("\"provenance\":\"").append(jsonEscape(item.provenancePath)).append("\",");
      sb.append("\"enrichmentReport\":\"").append(jsonEscape(item.enrichmentReportPath)).append("\"");
      sb.append("},");
      sb.append("\"ingestExitCode\":").append(item.ingestExitCode).append(",");
      sb.append("\"doctor\":{");
      sb.append("\"strictOk\":").append(item.doctor.strictOk).append(",");
      sb.append("\"xsd\":").append(item.doctor.xsdOk).append(",");
      sb.append("\"schematron\":").append(item.doctor.schematronOk).append(",");
      sb.append("\"lint\":").append(item.doctor.lintOk).append(",");
      sb.append("\"timing\":").append(item.doctor.timingOk).append(",");
      sb.append("\"geometry\":").append(item.doctor.geometryOk);
      sb.append("},");
      sb.append("\"schema\":{");
      sb.append("\"provenance\":").append(item.provenanceSchema.ok).append(",");
      sb.append("\"enrichmentReport\":").append(item.enrichmentSchema.ok);
      sb.append("},");
      sb.append("\"errors\":[");
      for (int j = 0; j < item.errors.size(); j++) {
        if (j > 0) sb.append(",");
        sb.append("\"").append(jsonEscape(item.errors.get(j))).append("\"");
      }
      sb.append("]");
      sb.append("}");
    }
    sb.append("]}");
    return sb.toString() + "\n";
  }

  private static DoctorStatus emptyDoctorStatus() {
    DoctorStatus s = new DoctorStatus();
    s.xsdOk = false;
    s.schematronOk = false;
    s.lintOk = false;
    s.timingOk = false;
    s.geometryOk = false;
    s.strictOk = false;
    return s;
  }

  private static SchemaStatus emptySchemaStatus() {
    SchemaStatus s = new SchemaStatus();
    s.ok = false;
    s.exitCode = 2;
    return s;
  }

  private static String sha256Hex(String sourceText) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] digest = md.digest(sourceText.getBytes(StandardCharsets.UTF_8));
      StringBuilder sb = new StringBuilder();
      for (byte b : digest) sb.append(String.format(java.util.Locale.ROOT, "%02x", b));
      return sb.toString();
    } catch (Exception e) {
      throw new RuntimeException("Failed to compute SHA-256", e);
    }
  }

  private static String jsonEscape(String s) {
    return s.replace("\\", "\\\\")
      .replace("\"", "\\\"")
      .replace("\n", "\\n")
      .replace("\r", "\\r")
      .replace("\t", "\\t");
  }

  private static void ensureMinSteps(List<String> stepTexts, int minSteps) {
    while (stepTexts.size() < minSteps) stepTexts.add("Ingest filler step " + (stepTexts.size() + 1));
  }

  private static void padToBarLength(List<String> stepTexts, int barLengthCounts) {
    while (stepTexts.size() % barLengthCounts != 0) stepTexts.add("Ingest filler step " + (stepTexts.size() + 1));
  }

  private static String buildXml(String title,
                                 String meter,
                                 String tempo,
                                 String profile,
                                 String sourceText,
                                 List<String> stepTexts,
                                 List<String> enrichmentNotes) {
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
    for (String note : enrichmentNotes) {
      String safe = truncate(collapseWhitespace(note), 180);
      if (safe.isBlank()) continue;
      sb.append("      <p>").append(escape("Enrichment: " + safe)).append("</p>\n");
    }
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
