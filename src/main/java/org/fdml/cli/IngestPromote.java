package org.fdml.cli;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Comparator;

final class IngestPromote {

  private IngestPromote() {}

  private static final class BatchItem {
    String source;
    String fdml;
    String provenance;
    String enrichmentReport;
    int ingestExitCode;
    boolean doctorStrictOk;
    boolean provenanceSchemaOk;
    boolean enrichmentSchemaOk;
    List<String> errors = new ArrayList<>();
  }

  private static final class QuarantineItem {
    String source;
    String fdml;
    String provenance;
    String enrichmentReport;
    List<String> reasons;
  }

  static int run(String[] args) {
    Map<String, String> kv = parseFlags(args, 1);
    String indexArg = kv.getOrDefault("--index", "").trim();
    String destArg = kv.getOrDefault("--dest", "").trim();
    if (indexArg.isBlank() || destArg.isBlank()) {
      System.err.println("ingest-promote: provide --index <ingest-batch-index.json> --dest <dir> [--quarantine-dir <dir>] [--quarantine-out quarantine.json]");
      return 4;
    }

    Path index = Paths.get(indexArg);
    if (!Files.exists(index)) {
      System.err.println("ingest-promote: index file missing: " + index);
      return 4;
    }
    Path dest = Paths.get(destArg);
    Path quarantineDir = Paths.get(kv.getOrDefault("--quarantine-dir", dest.resolve("quarantine").toString()).trim());
    Path quarantineOut = Paths.get(kv.getOrDefault("--quarantine-out", quarantineDir.resolve("quarantine.json").toString()).trim());

    List<BatchItem> items;
    try {
      String json = Files.readString(index, StandardCharsets.UTF_8);
      items = parseBatchItems(json);
    } catch (Exception e) {
      System.err.println("ingest-promote: failed to parse index file: " + index + " (" + e.getMessage() + ")");
      return 4;
    }
    items.sort(Comparator.comparing(i -> i.source));

    int promoted = 0;
    List<QuarantineItem> quarantined = new ArrayList<>();
    for (BatchItem item : items) {
      LinkedHashSet<String> reasonSet = new LinkedHashSet<>();
      if (item.ingestExitCode != 0) reasonSet.add("ingest_exit_nonzero");
      if (!item.doctorStrictOk) reasonSet.add("doctor_strict_failed");
      if (!item.provenanceSchemaOk) reasonSet.add("provenance_schema_failed");
      if (!item.enrichmentSchemaOk) reasonSet.add("enrichment_schema_failed");
      for (String e : item.errors) if (e != null && !e.isBlank()) reasonSet.add(e);
      List<String> reasons = new ArrayList<>(reasonSet);

      if (reasons.isEmpty()) {
        try {
          copyIfExists(Paths.get(item.fdml), dest.resolve(Paths.get(item.fdml).getFileName().toString()));
          copyIfExists(Paths.get(item.provenance), dest.resolve(Paths.get(item.provenance).getFileName().toString()));
          copyIfExists(Paths.get(item.enrichmentReport), dest.resolve(Paths.get(item.enrichmentReport).getFileName().toString()));
          promoted++;
        } catch (Exception e) {
          reasons.add("copy_failed");
        }
      }

      if (!reasons.isEmpty()) {
        QuarantineItem q = new QuarantineItem();
        q.source = item.source;
        q.fdml = item.fdml;
        q.provenance = item.provenance;
        q.enrichmentReport = item.enrichmentReport;
        q.reasons = reasons;
        quarantined.add(q);

        try {
          copyIfExists(Paths.get(item.fdml), quarantineDir.resolve(Paths.get(item.fdml).getFileName().toString()));
          copyIfExists(Paths.get(item.provenance), quarantineDir.resolve(Paths.get(item.provenance).getFileName().toString()));
          copyIfExists(Paths.get(item.enrichmentReport), quarantineDir.resolve(Paths.get(item.enrichmentReport).getFileName().toString()));
        } catch (Exception ignored) {
          // report still captures reasons
        }
      }
    }

    try {
      Files.createDirectories(quarantineOut.getParent());
      Files.writeString(
        quarantineOut,
        buildQuarantineJson(index.toString(), dest.toString(), quarantineDir.toString(), items.size(), promoted, quarantined) + "\n",
        StandardCharsets.UTF_8,
        StandardOpenOption.CREATE,
        StandardOpenOption.TRUNCATE_EXISTING
      );
      System.out.println("Created: " + quarantineOut);
      System.out.println("INGEST-PROMOTE SUMMARY");
      System.out.println("  total      : " + items.size());
      System.out.println("  promoted   : " + promoted);
      System.out.println("  quarantined: " + quarantined.size());
      return 0;
    } catch (Exception e) {
      System.err.println("ingest-promote: failed to write quarantine output: " + quarantineOut + " (" + e.getMessage() + ")");
      return 4;
    }
  }

  private static void copyIfExists(Path src, Path dst) throws Exception {
    if (!Files.exists(src)) return;
    Path parent = dst.getParent();
    if (parent != null) Files.createDirectories(parent);
    Files.copy(src, dst, StandardCopyOption.REPLACE_EXISTING);
  }

  private static List<BatchItem> parseBatchItems(String json) {
    Object root = JsonMini.parse(json);
    if (!(root instanceof Map<?, ?> rootMap)) throw new IllegalArgumentException("index root must be object");
    Object rawItems = rootMap.get("items");
    if (!(rawItems instanceof List<?> arr)) throw new IllegalArgumentException("index missing items[]");
    List<BatchItem> out = new ArrayList<>();
    for (Object obj : arr) {
      if (!(obj instanceof Map<?, ?> m)) throw new IllegalArgumentException("item must be object");
      BatchItem item = new BatchItem();
      item.source = asString(m.get("source"));
      Map<?, ?> outputs = asMap(m.get("outputs"), "outputs");
      item.fdml = asString(outputs.get("fdml"));
      item.provenance = asString(outputs.get("provenance"));
      item.enrichmentReport = asString(outputs.get("enrichmentReport"));
      item.ingestExitCode = asInt(m.get("ingestExitCode"));
      Map<?, ?> doctor = asMap(m.get("doctor"), "doctor");
      item.doctorStrictOk = asBoolean(doctor.get("strictOk"));
      Map<?, ?> schema = asMap(m.get("schema"), "schema");
      item.provenanceSchemaOk = asBoolean(schema.get("provenance"));
      item.enrichmentSchemaOk = asBoolean(schema.get("enrichmentReport"));
      Object rawErrs = m.get("errors");
      if (rawErrs instanceof List<?> errs) {
        for (Object e : errs) item.errors.add(asString(e));
      }
      out.add(item);
    }
    return out;
  }

  private static Map<?, ?> asMap(Object o, String label) {
    if (!(o instanceof Map<?, ?> m)) throw new IllegalArgumentException(label + " must be object");
    return m;
  }

  private static String asString(Object o) {
    return o == null ? "" : String.valueOf(o);
  }

  private static int asInt(Object o) {
    if (o instanceof Number n) return n.intValue();
    try {
      return Integer.parseInt(asString(o));
    } catch (NumberFormatException e) {
      return 0;
    }
  }

  private static boolean asBoolean(Object o) {
    if (o instanceof Boolean b) return b;
    return "true".equalsIgnoreCase(asString(o));
  }

  private static Map<String, String> parseFlags(String[] args, int from) {
    Map<String, String> m = new java.util.HashMap<>();
    for (int i = from; i < args.length; i++) {
      String a = args[i];
      if (!a.startsWith("--")) continue;
      String val = "";
      if (i + 1 < args.length && !args[i + 1].startsWith("--")) val = args[++i];
      m.put(a, val);
    }
    return m;
  }

  private static String buildQuarantineJson(String indexPath,
                                            String dest,
                                            String quarantineDir,
                                            int total,
                                            int promoted,
                                            List<QuarantineItem> quarantined) {
    StringBuilder sb = new StringBuilder();
    sb.append("{");
    sb.append("\"indexPath\":\"").append(jsonEscape(indexPath)).append("\",");
    sb.append("\"dest\":\"").append(jsonEscape(dest)).append("\",");
    sb.append("\"quarantineDir\":\"").append(jsonEscape(quarantineDir)).append("\",");
    sb.append("\"total\":").append(total).append(",");
    sb.append("\"promoted\":").append(promoted).append(",");
    sb.append("\"quarantined\":").append(quarantined.size()).append(",");
    sb.append("\"items\":[");
    for (int i = 0; i < quarantined.size(); i++) {
      QuarantineItem q = quarantined.get(i);
      if (i > 0) sb.append(",");
      sb.append("{");
      sb.append("\"source\":\"").append(jsonEscape(q.source)).append("\",");
      sb.append("\"outputs\":{");
      sb.append("\"fdml\":\"").append(jsonEscape(q.fdml)).append("\",");
      sb.append("\"provenance\":\"").append(jsonEscape(q.provenance)).append("\",");
      sb.append("\"enrichmentReport\":\"").append(jsonEscape(q.enrichmentReport)).append("\"");
      sb.append("},");
      sb.append("\"reasons\":[");
      for (int j = 0; j < q.reasons.size(); j++) {
        if (j > 0) sb.append(",");
        sb.append("\"").append(jsonEscape(q.reasons.get(j))).append("\"");
      }
      sb.append("]");
      sb.append("}");
    }
    sb.append("]}");
    return sb.toString();
  }

  private static String jsonEscape(String s) {
    if (s == null) return "";
    return s.replace("\\", "\\\\")
      .replace("\"", "\\\"")
      .replace("\n", "\\n")
      .replace("\r", "\\r")
      .replace("\t", "\\t");
  }
}
