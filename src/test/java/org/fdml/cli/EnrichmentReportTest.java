package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class EnrichmentReportTest {

  @Test
  public void ingestOfflineEnrichmentReportMatchesSchemaAndFixture() throws Exception {
    Path tmpDir = Files.createTempDirectory("fdml-enrichment-report-test");
    Path outXml = tmpDir.resolve("ingest.fdml.xml");
    Path outReport = tmpDir.resolve("enrichment-report.json");

    int code = Ingest.run(new String[]{
      "ingest",
      "--source", "analysis/gold/ingest/source_minimal.txt",
      "--out", outXml.toString(),
      "--title", "Ingest Minimal",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic",
      "--enable-enrichment",
      "--env-file", "src/test/resources/enrichment/offline.env",
      "--enrichment-report", outReport.toString()
    });
    assertEquals(0, code, "Expected ingest with enrichment report to succeed");
    assertTrue(Files.exists(outReport), "Expected enrichment report file to be created");

    ProcessResult schemaCheck = runSchemaValidator(
      Path.of("schema/enrichment-report.schema.json"),
      outReport
    );
    assertEquals(0, schemaCheck.exitCode, "Expected enrichment report schema validation to pass:\n" + schemaCheck.output);

    String actual = Files.readString(outReport, StandardCharsets.UTF_8).trim();
    String expected = Files.readString(Path.of("src/test/resources/enrichment/expected/offline-report.json"), StandardCharsets.UTF_8).trim();
    assertEquals(expected, actual, "Generated enrichment report drifted from deterministic offline fixture");
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
