package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class MainHelpTest {

  @Test
  public void longHelpFlagPrintsUsageAndExitsZero() throws Exception {
    ProcessResult r = runMain("--help");
    assertEquals(0, r.exitCode, "Expected --help to exit 0");
    assertTrue(r.output.contains("Usage:"), "Expected usage output for --help");
  }

  @Test
  public void shortHelpFlagPrintsUsageAndExitsZero() throws Exception {
    ProcessResult r = runMain("-h");
    assertEquals(0, r.exitCode, "Expected -h to exit 0");
    assertTrue(r.output.contains("Usage:"), "Expected usage output for -h");
  }

  private static ProcessResult runMain(String arg) throws Exception {
    Path mainClasses = Path.of(Main.class.getProtectionDomain().getCodeSource().getLocation().toURI());
    Process p = new ProcessBuilder(
      List.of("java", "-cp", mainClasses.toString(), "org.fdml.cli.Main", arg)
    ).redirectErrorStream(true).start();

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
