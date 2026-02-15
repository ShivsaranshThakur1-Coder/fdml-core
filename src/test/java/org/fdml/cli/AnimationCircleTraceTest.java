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

public class AnimationCircleTraceTest {

  @Test
  public void traceHashMatchesExpectedForMayimV12() throws Exception {
    Path source = Path.of("corpus/valid_v12/mayim-mayim.v12.fdml.xml");
    String payload = ExportJson.export(source);

    Path tmp = Files.createTempFile("fdml-anim-circle-payload-", ".json");
    Files.writeString(tmp, payload, StandardCharsets.UTF_8);

    ProcessResult r = runTraceScript(tmp, source.toString());
    assertEquals(0, r.exitCode, "animation_trace_circle.py should exit 0");

    String expected = Files.readString(
      Path.of("src/test/resources/animation_circle/trace_expected.json"),
      StandardCharsets.UTF_8
    ).trim();
    assertEquals(expected, r.output.trim(), "AnimationCircle trace output drifted from expected");
  }

  private static ProcessResult runTraceScript(Path payloadPath, String source) throws Exception {
    List<String> cmd = new ArrayList<>();
    cmd.add("python3");
    cmd.add("scripts/animation_trace_circle.py");
    cmd.add("--json");
    cmd.add(payloadPath.toString());
    cmd.add("--source");
    cmd.add(source);

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
