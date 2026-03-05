package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class IngestBatchTest {

  @Test
  public void ingestBatchProducesDeterministicOutputsAndPassingSummary() throws Exception {
    Path tmpDir = Files.createTempDirectory("fdml-ingest-batch-test");
    Path outDir = tmpDir.resolve("out");
    Path indexOut = outDir.resolve("index.json");

    int code = Ingest.runBatch(new String[]{
      "ingest-batch",
      "--source-dir", "src/test/resources/ingest_batch/sources",
      "--out-dir", outDir.toString(),
      "--title-prefix", "Batch Fixture",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic",
      "--enable-enrichment",
      "--env-file", "src/test/resources/enrichment/offline.env",
      "--index-out", indexOut.toString()
    });
    assertEquals(0, code, "Expected ingest-batch to succeed");
    assertTrue(Files.exists(indexOut), "Expected ingest-batch summary index.json");

    String summary = Files.readString(indexOut, StandardCharsets.UTF_8);
    assertTrue(summary.contains("\"failed\":0"), "Expected zero failed items in batch summary:\n" + summary);
    assertTrue(summary.contains("sample-a.txt"), "Expected sample-a in summary:\n" + summary);
    assertTrue(summary.contains("sample-b.txt"), "Expected sample-b in summary:\n" + summary);
    assertTrue(summary.contains("\"provenance\":true"), "Expected provenance schema success in summary:\n" + summary);
    assertTrue(summary.contains("\"enrichmentReport\":true"), "Expected enrichment schema success in summary:\n" + summary);

    List<Path> xmlFiles = listSorted(outDir, ".fdml.xml");
    List<Path> provFiles = listSorted(outDir, ".provenance.json");
    List<Path> enrichFiles = listSorted(outDir, ".enrichment-report.json");

    assertEquals(2, xmlFiles.size(), "Expected one fdml output per source file");
    assertEquals(2, provFiles.size(), "Expected one provenance output per source file");
    assertEquals(2, enrichFiles.size(), "Expected one enrichment report per source file");

    for (Path xml : xmlFiles) {
      int doctorCode = Doctor.run(new String[]{"doctor", xml.toString(), "--strict"});
      assertEquals(0, doctorCode, "Expected strict doctor pass for " + xml);
    }
    for (Path prov : provFiles) {
      ProcessResult r = runSchemaValidator(Path.of("schema/provenance.schema.json"), prov);
      assertEquals(0, r.exitCode, "Expected provenance schema pass for " + prov + ":\n" + r.output);
    }
    for (Path enrich : enrichFiles) {
      ProcessResult r = runSchemaValidator(Path.of("schema/enrichment-report.schema.json"), enrich);
      assertEquals(0, r.exitCode, "Expected enrichment-report schema pass for " + enrich + ":\n" + r.output);
    }
  }

  private static List<Path> listSorted(Path dir, String suffix) throws Exception {
    try (var stream = Files.list(dir)) {
      return stream
        .filter(Files::isRegularFile)
        .filter(p -> p.getFileName().toString().endsWith(suffix))
        .sorted(Comparator.comparing(p -> p.getFileName().toString()))
        .toList();
    }
  }

  private static ProcessResult runSchemaValidator(Path schema, Path instance) throws Exception {
    List<String> cmd = new ArrayList<>();
    cmd.add("python3");
    cmd.add("scripts/validate_json_schema.py");
    cmd.add(schema.toString());
    cmd.add(instance.toString());

    Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
    String output;
    try (InputStream in = p.getInputStream()) {
      output = readAll(in);
    }
    int exit = p.waitFor();
    return new ProcessResult(exit, output);
  }

  private static String readAll(InputStream in) throws Exception {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    in.transferTo(out);
    return out.toString(StandardCharsets.UTF_8);
  }

  private static final class ProcessResult {
    final int exitCode;
    final String output;

    ProcessResult(int exitCode, String output) {
      this.exitCode = exitCode;
      this.output = output;
    }
  }
}
