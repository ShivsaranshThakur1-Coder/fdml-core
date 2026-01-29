package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.nio.file.*;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class FdmlSchemaV12Test {

  @Test
  public void invalidV12PrimitiveKindIsRejectedByXsd() {
    var validator = new FdmlValidator(Paths.get("schema/fdml.xsd"));
    var results = validator.validateCollect(List.of(Paths.get(
      "corpus/invalid_v12/mayim-mayim.bad-primitive-kind.v12.fdml.xml"
    )));

    assertTrue(results.stream().anyMatch(r -> !r.ok), "Expected at least one XSD validation failure");
  }
}
