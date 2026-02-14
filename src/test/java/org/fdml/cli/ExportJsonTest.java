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

public class ExportJsonTest {

  @Test
  public void keyPresenceForExample03AbdalaAndHaireOpposites() {
    String ex03 = ExportJson.export(Path.of("corpus/valid/example-03.fdml.xml"));
    assertContainsInOrder(ex03, "\"file\":", "\"meta\":", "\"figures\":", "\"topology\":");
    assertContainsInOrder(ex03,
      "\"version\":", "\"title\":", "\"meter\":", "\"tempoBpm\":",
      "\"originCountry\":", "\"typeGenre\":", "\"formationText\":", "\"formationKind\":");
    assertContainsInOrder(ex03,
      "\"who\":", "\"action\":", "\"beats\":", "\"count\":", "\"direction\":",
      "\"facing\":", "\"startFoot\":", "\"endFoot\":", "\"text\":", "\"primitives\":");
    assertTrue(ex03.contains("\"title\":\"Circle Waltz — Basic\""));
    assertTrue(ex03.contains("\"meter\":\"3/4\""));

    String abdala = ExportJson.export(Path.of("corpus/valid/abdala.fdml.xml"));
    assertTrue(abdala.contains("\"title\":\"Abdala\""));
    assertTrue(abdala.contains("\"meter\":\"9/16\""));
    assertTrue(abdala.contains("\"typeGenre\":\"line\""));
    assertTrue(abdala.contains("\"originCountry\":\"Bulgaria\""));
    assertTrue(abdala.contains("\"figures\":["));

    String haire = ExportJson.export(Path.of("corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml"));
    assertTrue(haire.contains("\"formationKind\":\"twoLinesFacing\""));
    assertTrue(haire.contains("\"twoLines\":{"));
    assertTrue(haire.contains("\"opposites\":[{\"a\":\"b1\",\"b\":\"g1\"},{\"a\":\"b2\",\"b\":\"g2\"}]"));
    assertTrue(haire.contains("\"neighbors\":[{\"line\":\"bride_line\",\"a\":\"b1\",\"b\":\"b2\"},{\"line\":\"groom_line\",\"a\":\"g1\",\"b\":\"g2\"}]"));
  }

  @Test
  public void directoryExportUsesDeterministicSortedFileOrder() throws Exception {
    Path tempDir = Files.createTempDirectory("fdml-export-json-order");
    Path a = tempDir.resolve("a.fdml.xml");
    Path b = tempDir.resolve("b.fdml.xml");
    Path c = tempDir.resolve("c.fdml.xml");

    Files.copy(Path.of("corpus/valid/abdala.fdml.xml"), c);
    Files.copy(Path.of("corpus/valid/example-03.fdml.xml"), a);
    Files.copy(Path.of("corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml"), b);

    String json = ExportJson.export(tempDir);
    int ia = json.indexOf("\"file\":\"" + jsonEsc(a.toString()) + "\"");
    int ib = json.indexOf("\"file\":\"" + jsonEsc(b.toString()) + "\"");
    int ic = json.indexOf("\"file\":\"" + jsonEsc(c.toString()) + "\"");

    assertTrue(ia >= 0 && ib >= 0 && ic >= 0, "Expected all copied files in directory export");
    assertTrue(ia < ib && ib < ic, "Expected deterministic lexicographic file ordering");
  }

  @Test
  public void goldenMatchesForHaireOpposites() throws Exception {
    String actual = ExportJson.export(Path.of("corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml")).trim();
    String expected = Files.readString(
      Path.of("src/test/resources/export-json/expected/haire-mamougeh.opposites.v12.json"),
      StandardCharsets.UTF_8
    ).trim();
    assertEquals(expected, actual, "export-json output drifted from golden payload");
  }

  @Test
  public void generatedPayloadConformsToSchema() throws Exception {
    String payload = ExportJson.export(Path.of("corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml"));
    Path out = Files.createTempFile("fdml-export-json-", ".json");
    Files.writeString(out, payload, StandardCharsets.UTF_8);

    ProcessResult r = runSchemaValidator(
      Path.of("schema/export-json.schema.json"),
      out
    );
    assertEquals(0, r.exitCode, "Expected schema validation to pass, output:\n" + r.output);
  }

  @Test
  public void invalidFixtureFailsSchemaValidation() throws Exception {
    ProcessResult r = runSchemaValidator(
      Path.of("schema/export-json.schema.json"),
      Path.of("src/test/resources/export-json/invalid/missing-meta.json")
    );
    assertTrue(r.exitCode != 0, "Expected invalid JSON fixture to fail schema validation");
    assertTrue(r.output.contains("required") || r.output.contains("missing"),
      "Expected missing-required-field signal in output:\n" + r.output);
  }

  private static void assertContainsInOrder(String text, String... snippets) {
    int idx = -1;
    for (String s : snippets) {
      int next = text.indexOf(s, idx + 1);
      assertTrue(next >= 0, "Missing snippet: " + s);
      assertTrue(next > idx, "Out-of-order snippet: " + s);
      idx = next;
    }
  }

  private static String jsonEsc(String s) {
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
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
