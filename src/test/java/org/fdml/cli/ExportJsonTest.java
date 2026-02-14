package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
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
}
