package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class DoctorExplainTest {

  @Test
  public void doctorExplainIncludesIssueCodeAndGuidance() throws Exception {
    RunResult r = runDoctor("doctor", "corpus/invalid_timing/example-off-meter.fdml.xml", "--explain");
    assertEquals(0, r.code, "Non-strict doctor should exit 0");
    assertTrue(r.stdout.contains("DOCTOR SUMMARY"), "Expected normal summary");
    assertTrue(r.stdout.contains("EXPLAIN"), "Expected explain section");
    assertTrue(r.stdout.contains("off_meter_figure"), "Expected timing issue code in explain section");
    assertTrue(r.stdout.toLowerCase().contains("align"), "Expected remediation guidance text");
  }

  @Test
  public void doctorJsonExplainIncludesExplainObject() throws Exception {
    RunResult r = runDoctor("doctor", "corpus/invalid_timing/example-off-meter.fdml.xml", "--json", "--explain");
    assertEquals(0, r.code, "Non-strict doctor should exit 0");
    assertTrue(r.stdout.contains("\"explain\":{"), "Expected explain object in JSON output");
    assertTrue(r.stdout.contains("\"off_meter_figure\""), "Expected issue code key in explain object");
  }

  @Test
  public void doctorExplainNoIssuesPrintsNoIssues() throws Exception {
    RunResult r = runDoctor("doctor", "corpus/valid/example-03.fdml.xml", "--explain");
    assertEquals(0, r.code, "Expected valid input to pass");
    assertTrue(r.stdout.contains("EXPLAIN"), "Expected explain section");
    assertTrue(r.stdout.contains("no issues"), "Expected no-issues marker");
  }

  private static RunResult runDoctor(String... args) throws Exception {
    PrintStream origOut = System.out;
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    int code;
    try (PrintStream ps = new PrintStream(out, true, StandardCharsets.UTF_8)) {
      System.setOut(ps);
      code = Doctor.run(args);
    } finally {
      System.setOut(origOut);
    }
    return new RunResult(code, out.toString(StandardCharsets.UTF_8));
  }

  private static final class RunResult {
    final int code;
    final String stdout;

    RunResult(int code, String stdout) {
      this.code = code;
      this.stdout = stdout;
    }
  }
}
