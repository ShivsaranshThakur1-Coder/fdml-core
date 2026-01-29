package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.nio.file.*;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class GeometryValidatorTest {

  @Test
  public void validV12ExamplePassesGeometryValidation() {
    var p = Paths.get("corpus/valid_v12/mayim-mayim.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertTrue(r.ok, "Expected geometry validation to pass for " + p + ": " + r.issues);
  }

  @Test
  public void circleOrderPreservationRejectsCrossingPrimitiveWhenPreserveOrderTrue() throws Exception {
    String xml = """
      <?xml version=\"1.0\" encoding=\"UTF-8\"?>
      <fdml version=\"1.2\">
        <meta>
          <title>Bad circle order</title>
          <type genre=\"circle\"/>
          <meter value=\"4/4\"/>
          <tempo bpm=\"120\"/>
          <formation text=\"circle\"/>
          <geometry>
            <formation kind=\"circle\"/>
            <roles><role id=\"all\"/></roles>
          </geometry>
        </meta>
        <body>
          <geometry><circle><order role=\"all\"/></circle></geometry>
          <figure id=\"f\" name=\"x\">
            <step who=\"all\" action=\"run\" beats=\"1\">
              <geo>
                <primitive kind=\"move\" frame=\"formation\" axis=\"tangent\" dir=\"counterclockwise\" preserveOrder=\"true\"/>
                <primitive kind=\"pass\" frame=\"formation\"/>
              </geo>
            </step>
          </figure>
        </body>
      </fdml>
      """;

    Path tmp = Files.createTempFile("fdml-bad-circle", ".fdml.xml");
    Files.writeString(tmp, xml);

    var r = GeometryValidator.validateOne(tmp);
    assertFalse(r.ok, "Expected geometry validation to fail");
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("circle_order_violation")), "Expected circle_order_violation");
  }

  @Test
  public void haireBadFormationFailsGeometryValidation() {
    var p = Paths.get("corpus/invalid_v12/haire-mamougeh.bad-formation.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertFalse(r.ok, "Expected geometry validation to fail for " + p);
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("bad_formation_for_approach_retreat")),
      "Expected bad_formation_for_approach_retreat");
  }

  @Test
  public void ambiguousCircleDirFailsGeometryValidation() {
    var p = Paths.get("corpus/invalid_v12/mayim-mayim.ambiguous-dir.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertFalse(r.ok, "Expected geometry validation to fail for " + p);
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("circle_travel_ambiguous")),
      "Expected circle_travel_ambiguous");
  }

  @Test
  public void circleOrderBrokenFailsWithCircleOrderChanged() {
    var p = Paths.get("corpus/invalid_v12/mayim-mayim.order-broken.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertFalse(r.ok, "Expected geometry validation to fail for " + p);
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("circle_order_changed")),
      "Expected circle_order_changed");
  }

  @Test
  public void validateGeoCollectSkipsNonXmlFiles() throws Exception {
    Path dir = Files.createTempDirectory("fdml-geo-dir");
    Files.writeString(dir.resolve("note.txt"), "hi");

    var rs = GeometryValidator.validateCollect(List.of(dir));
    // No *.xml-like inputs -> empty results
    assertEquals(0, rs.size());
  }
}
