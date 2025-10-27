
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
}
