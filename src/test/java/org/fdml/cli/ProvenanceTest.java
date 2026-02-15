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

public class ProvenanceTest {

  @Test
  public void ingestProvenanceMatchesSchemaAndGoldFixture() throws Exception {
    Path tmpDir = Files.createTempDirectory("fdml-provenance-test");
    Path outXml = tmpDir.resolve("ingest.fdml.xml");
    Path outProv = tmpDir.resolve("provenance.json");

    int code = Ingest.run(new String[]{
      "ingest",
      "--source", "analysis/gold/ingest/source_minimal.txt",
      "--out", outXml.toString(),
      "--title", "Ingest Minimal",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic",
      "--provenance-out", outProv.toString()
    });
    assertEquals(0, code, "Expected ingest with provenance-out to succeed");
    assertTrue(Files.exists(outProv), "Expected provenance output file to exist");

    ProcessResult schemaCheck = runSchemaValidator(
      Path.of("schema/provenance.schema.json"),
      outProv
    );
    assertEquals(0, schemaCheck.exitCode, "Expected provenance schema validation to pass:\n" + schemaCheck.output);

    String actual = Files.readString(outProv, StandardCharsets.UTF_8).trim();
    String expected = Files.readString(Path.of("analysis/gold/ingest/provenance_minimal.json"), StandardCharsets.UTF_8).trim();
    assertEquals(expected, actual, "Generated provenance drifted from deterministic gold fixture");
  }

  @Test
  public void invalidProvenanceFixtureFailsSchemaValidation() throws Exception {
    ProcessResult r = runSchemaValidator(
      Path.of("schema/provenance.schema.json"),
      Path.of("src/test/resources/provenance/invalid/missing_sha.json")
    );
    assertTrue(r.exitCode != 0, "Expected invalid provenance fixture to fail schema validation");
    assertTrue(r.output.contains("sourceSha256") || r.output.contains("required"),
      "Expected sourceSha256 required-field signal in output:\n" + r.output);
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
