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
  public void coupleWomanSideMissingPartnerPairingFails() throws Exception {
    String xml = """
      <?xml version=\"1.0\" encoding=\"UTF-8\"?>
      <fdml version=\"1.2\">
        <meta>
          <title>Bad couple pairing</title>
          <type genre=\"couple\"/>
          <meter value=\"4/4\"/>
          <tempo bpm=\"120\"/>
          <formation text=\"couple\"/>
          <geometry>
            <formation kind=\"couple\" womanSide=\"left\"/>
            <roles>
              <role id=\"man\"/>
              <role id=\"woman\"/>
            </roles>
          </geometry>
        </meta>
        <body>
          <geometry>
            <couples>
              <!-- missing man/woman pair -->
            </couples>
          </geometry>
          <figure id=\"f\" name=\"x\">
            <step who=\"man\" action=\"hold\" beats=\"1\"><geo><primitive kind=\"hold\"/></geo></step>
          </figure>
        </body>
      </fdml>
      """;

    Path tmp = Files.createTempFile("fdml-bad-couple", ".fdml.xml");
    Files.writeString(tmp, xml);

    var r = GeometryValidator.validateOne(tmp);
    assertFalse(r.ok, "Expected geometry validation to fail");
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("missing_partner_pairing")),
      "Expected missing_partner_pairing");
  }

  @Test
  public void twoLinesFacingMissingFacingFails() throws Exception {
    String xml = """
      <?xml version=\"1.0\" encoding=\"UTF-8\"?>
      <fdml version=\"1.2\">
        <meta>
          <title>Bad twoLinesFacing missing facing</title>
          <type genre=\"line\"/>
          <meter value=\"4/4\"/>
          <tempo bpm=\"120\"/>
          <formation text=\"two lines\"/>
          <geometry>
            <formation kind=\"twoLinesFacing\"/>
            <roles>
              <role id=\"a\"/>
              <role id=\"b\"/>
            </roles>
          </geometry>
        </meta>
        <body>
          <geometry>
            <twoLines>
              <line id=\"L1\" role=\"a\"/>
              <line id=\"L2\" role=\"b\"/>
              <!-- facing missing -->
            </twoLines>
          </geometry>
          <figure id=\"f\" name=\"x\">
            <step who=\"a\" action=\"approach\" beats=\"2\"><geo><primitive kind=\"approach\"/></geo></step>
          </figure>
        </body>
      </fdml>
      """;

    Path tmp = Files.createTempFile("fdml-bad-twolines", ".fdml.xml");
    Files.writeString(tmp, xml);

    var r = GeometryValidator.validateOne(tmp);
    assertFalse(r.ok, "Expected geometry validation to fail");
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("missing_two_lines_facing")),
      "Expected missing_two_lines_facing");
  }

  @Test
  public void aalistullaaTwirlMissingHalfFails() {
    var p = Paths.get("corpus/invalid_v12/aalistullaa.twirl-missing-half.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertFalse(r.ok, "Expected geometry validation to fail for " + p);
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("twirl_missing_half")),
      "Expected twirl_missing_half");
  }

  @Test
  public void aalistullaaHoldBrokenFails() {
    var p = Paths.get("corpus/invalid_v12/aalistullaa.hold-broken.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertFalse(r.ok, "Expected geometry validation to fail for " + p);
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("hold_broken")),
      "Expected hold_broken");
  }

  @Test
  public void progressMissingOrderTriggersMissingLineOrderSlots() {
    var p = Paths.get("corpus/invalid_v12/example-05-contra.progress-missing-order.v12.fdml.xml");
    var r = GeometryValidator.validateOne(p);
    assertFalse(r.ok, "Expected geometry validation to fail for " + p);
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("missing_line_order_slots")),
      "Expected missing_line_order_slots");
  }

  @Test
  public void progressMissingDeltaTriggersProgressMissingDelta() throws Exception {
    String xml = """
      <?xml version=\"1.0\" encoding=\"UTF-8\"?>
      <fdml version=\"1.2\">
        <meta>
          <title>Bad progress delta</title>
          <type genre=\"line\"/>
          <meter value=\"4/4\"/>
          <tempo bpm=\"120\"/>
          <formation text=\"line\"/>
          <geometry>
            <formation kind=\"line\"/>
            <roles>
              <role id=\"all\"/>
              <role id=\"d1\"/>
              <role id=\"d2\"/>
            </roles>
          </geometry>
        </meta>
        <body>
          <geometry>
            <line id=\"line1\">
              <order>
                <slot who=\"d1\"/>
                <slot who=\"d2\"/>
              </order>
            </line>
          </geometry>
          <figure id=\"f-x\" name=\"x\">
            <step who=\"all\" action=\"progress\" beats=\"4\" startFoot=\"R\">
              <geo>
                <primitive kind=\"progress\" who=\"all\" />
              </geo>
            </step>
          </figure>
        </body>
      </fdml>
      """;

    Path tmp = Files.createTempFile("fdml-bad-progress", ".fdml.xml");
    Files.writeString(tmp, xml);

    var r = GeometryValidator.validateOne(tmp);
    assertFalse(r.ok, "Expected geometry validation to fail");
    assertTrue(r.issues.stream().anyMatch(i -> i.code.equals("progress_missing_delta")),
      "Expected progress_missing_delta");
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
