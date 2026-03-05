package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class IngestPromoteTest {

  @Test
  public void promoteAllPassingBatchItems() throws Exception {
    Path tmpDir = Files.createTempDirectory("fdml-ingest-promote-pass");
    Path batchOut = tmpDir.resolve("batch-out");
    Path indexOut = batchOut.resolve("index.json");
    int batchCode = Ingest.runBatch(new String[]{
      "ingest-batch",
      "--source-dir", "src/test/resources/ingest_batch/sources",
      "--out-dir", batchOut.toString(),
      "--title-prefix", "Batch Fixture",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic",
      "--enable-enrichment",
      "--env-file", "src/test/resources/enrichment/offline.env",
      "--index-out", indexOut.toString()
    });
    assertEquals(0, batchCode, "Expected ingest-batch to succeed before promotion");

    Path promotedDir = tmpDir.resolve("promoted");
    Path quarantineDir = tmpDir.resolve("quarantine");
    Path quarantineOut = quarantineDir.resolve("quarantine.json");
    int promoteCode = IngestPromote.run(new String[]{
      "ingest-promote",
      "--index", indexOut.toString(),
      "--dest", promotedDir.toString(),
      "--quarantine-dir", quarantineDir.toString(),
      "--quarantine-out", quarantineOut.toString()
    });
    assertEquals(0, promoteCode, "Expected ingest-promote to succeed");

    List<Path> promotedXml = listSorted(promotedDir, ".fdml.xml");
    List<Path> promotedProv = listSorted(promotedDir, ".provenance.json");
    List<Path> promotedEnrich = listSorted(promotedDir, ".enrichment-report.json");
    assertEquals(2, promotedXml.size(), "Expected both valid batch items to be promoted");
    assertEquals(2, promotedProv.size(), "Expected provenance sidecars to be promoted");
    assertEquals(2, promotedEnrich.size(), "Expected enrichment sidecars to be promoted");

    String quarantine = Files.readString(quarantineOut, StandardCharsets.UTF_8);
    assertTrue(quarantine.contains("\"quarantined\":0"), "Expected no quarantined items:\n" + quarantine);
  }

  @Test
  public void quarantineItemsThatFailPromotionCriteria() throws Exception {
    Path tmpDir = Files.createTempDirectory("fdml-ingest-promote-fail");
    Path batchOut = tmpDir.resolve("batch-out");
    Path indexOut = batchOut.resolve("index.json");
    int batchCode = Ingest.runBatch(new String[]{
      "ingest-batch",
      "--source-dir", "src/test/resources/ingest_batch/sources",
      "--out-dir", batchOut.toString(),
      "--title-prefix", "Batch Fixture",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic",
      "--enable-enrichment",
      "--env-file", "src/test/resources/enrichment/offline.env",
      "--index-out", indexOut.toString()
    });
    assertEquals(0, batchCode, "Expected ingest-batch to succeed before promotion");

    String index = Files.readString(indexOut, StandardCharsets.UTF_8);
    String modified = index.replaceFirst("\"strictOk\":true", "\"strictOk\":false");
    Path badIndex = tmpDir.resolve("index-bad.json");
    Files.writeString(badIndex, modified, StandardCharsets.UTF_8);

    Path promotedDir = tmpDir.resolve("promoted");
    Path quarantineDir = tmpDir.resolve("quarantine");
    Path quarantineOut = quarantineDir.resolve("quarantine.json");
    int promoteCode = IngestPromote.run(new String[]{
      "ingest-promote",
      "--index", badIndex.toString(),
      "--dest", promotedDir.toString(),
      "--quarantine-dir", quarantineDir.toString(),
      "--quarantine-out", quarantineOut.toString()
    });
    assertEquals(0, promoteCode, "Expected ingest-promote to complete even with quarantined items");

    List<Path> promotedXml = listSorted(promotedDir, ".fdml.xml");
    assertEquals(1, promotedXml.size(), "Expected exactly one promoted item after forcing one strict failure");

    String quarantine = Files.readString(quarantineOut, StandardCharsets.UTF_8);
    assertTrue(quarantine.contains("\"quarantined\":1"), "Expected one quarantined item:\n" + quarantine);
    assertTrue(quarantine.contains("doctor_strict_failed"), "Expected strict failure reason in quarantine report:\n" + quarantine);
  }

  private static List<Path> listSorted(Path dir, String suffix) throws Exception {
    if (!Files.exists(dir)) return List.of();
    try (var stream = Files.list(dir)) {
      return stream
        .filter(Files::isRegularFile)
        .filter(p -> p.getFileName().toString().endsWith(suffix))
        .sorted(Comparator.comparing(p -> p.getFileName().toString()))
        .toList();
    }
  }
}
