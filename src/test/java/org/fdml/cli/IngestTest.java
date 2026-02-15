package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class IngestTest {

  @Test
  public void ingestGoldSourceIsDeterministicAndStrictValid() throws Exception {
    Path tmpDir = Files.createTempDirectory("fdml-ingest-test");
    Path out1 = tmpDir.resolve("ingest-1.fdml.xml");
    Path out2 = tmpDir.resolve("ingest-2.fdml.xml");

    int code1 = Ingest.run(new String[]{
      "ingest",
      "--source", "analysis/gold/ingest/source_minimal.txt",
      "--out", out1.toString(),
      "--title", "Ingest Minimal",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic"
    });
    assertEquals(0, code1, "Expected ingest success for gold source");

    int code2 = Ingest.run(new String[]{
      "ingest",
      "--source", "analysis/gold/ingest/source_minimal.txt",
      "--out", out2.toString(),
      "--title", "Ingest Minimal",
      "--meter", "4/4",
      "--tempo", "112",
      "--profile", "v1-basic"
    });
    assertEquals(0, code2, "Expected ingest success on repeated run");

    String expected = Files.readString(Path.of("corpus/valid_ingest/ingest-minimal.fdml.xml"), StandardCharsets.UTF_8);
    String actual1 = Files.readString(out1, StandardCharsets.UTF_8);
    String actual2 = Files.readString(out2, StandardCharsets.UTF_8);
    assertEquals(expected, actual1, "Expected output must match committed deterministic fixture");
    assertEquals(actual1, actual2, "Repeated ingest output must be byte-identical");

    int doctorCode = Doctor.run(new String[]{"doctor", out1.toString(), "--strict"});
    assertEquals(0, doctorCode, "Expected strict doctor to pass for ingest gold output");
  }

  @Test
  public void ingestFailsOnEmptySource() throws Exception {
    Path tmp = Files.createTempFile("fdml-ingest-empty", ".fdml.xml");
    ByteArrayOutputStream errBuf = new ByteArrayOutputStream();
    PrintStream origErr = System.err;
    int code;
    try (PrintStream ps = new PrintStream(errBuf, true, StandardCharsets.UTF_8)) {
      System.setErr(ps);
      code = Ingest.run(new String[]{
        "ingest",
        "--source", "analysis/gold/ingest/source_empty.txt",
        "--out", tmp.toString()
      });
    } finally {
      System.setErr(origErr);
    }
    assertEquals(4, code, "Expected empty ingest source to fail with IO/usage exit code");
    String err = errBuf.toString(StandardCharsets.UTF_8);
    assertTrue(err.contains("source file is empty"), "Expected clear empty source error message");
  }
}
