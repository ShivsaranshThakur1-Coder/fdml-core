
package org.fdml.cli;

import org.junit.jupiter.api.Test;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

public class IndexJsonTest {
  @Test
  public void indexIncludesAllValidFiles() throws Exception {
    // Count *.xml under corpus/valid
    long expected = Files.list(Paths.get("corpus/valid"))
        .filter(f -> f.getFileName().toString().toLowerCase().endsWith(".xml"))
        .count();

    // Build JSON in-memory (no file I/O dependency)
    String json = Indexer.buildIndex(List.of(Paths.get("corpus/valid")));

    // Naive count of items by counting  occurrences
    long actual = json.split("\\\"file\\\"\s*:").length - 1;

    assertEquals(expected, actual, "index.json item count should match corpus/valid XML count");
    assertTrue(actual >= 12, "index.json must include at least 12 items");
  }

  @Test
  public void indexIncludesExtendedFacetFields() {
    String json = Indexer.buildIndex(List.of(
      Paths.get("corpus/valid/example-03.fdml.xml"),
      Paths.get("corpus/valid/abdala.fdml.xml"),
      Paths.get("corpus/valid_v12/mayim-mayim.v12.fdml.xml")
    ));

    String ex03 = extractItemObject(json, "corpus/valid/example-03.fdml.xml");
    assertNotNull(ex03, "Expected item for example-03");
    assertTrue(ex03.contains("\"version\":\"1.0\""));
    assertTrue(ex03.contains("\"meter\":\"3/4\""));
    assertTrue(ex03.contains("\"tempoBpm\":\"90\""));
    assertTrue(ex03.contains("\"authorEmail\":\"alice@example.com\""));
    assertTrue(ex03.contains("\"hasGeometry\":false"));

    String abdala = extractItemObject(json, "corpus/valid/abdala.fdml.xml");
    assertNotNull(abdala, "Expected item for abdala");
    assertTrue(abdala.contains("\"meter\":\"9/16\""));
    assertTrue(abdala.contains("\"genre\":\"line\""));
    assertTrue(abdala.contains("\"originCountry\":\"Bulgaria\""));

    String v12 = extractItemObject(json, "corpus/valid_v12/mayim-mayim.v12.fdml.xml");
    assertNotNull(v12, "Expected item for v1.2 sample");
    assertTrue(v12.contains("\"version\":\"1.2\""));
    assertTrue(v12.contains("\"formationKind\":\"circle\""));
    assertTrue(v12.contains("\"hasGeometry\":true"));
  }

  private static String extractItemObject(String json, String file) {
    String marker = "\"file\":\"" + file + "\"";
    int markerPos = json.indexOf(marker);
    if (markerPos < 0) return null;
    int start = json.lastIndexOf('{', markerPos);
    int end = json.indexOf('}', markerPos);
    if (start < 0 || end < 0 || end <= start) return null;
    return json.substring(start, end + 1);
  }
}
