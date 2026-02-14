package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class TimingValidatorTest {

  @Test
  public void invalidFixtureFailsOffMeter() {
    var rs = TimingValidator.validateCollect(List.of(
      Path.of("corpus/invalid_timing/example-off-meter.fdml.xml")
    ));

    assertFalse(rs.isEmpty(), "Expected one timing result");
    var r = rs.get(0);
    assertFalse(r.ok(), "Expected timing issues");
    assertTrue(r.issues.stream().anyMatch(i -> "off_meter_figure".equals(i.code)),
      "Expected off_meter_figure issue");
  }

  @Test
  public void missingMeterIsReported() throws Exception {
    String xml = """
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.1">
        <meta><title>t</title></meta>
        <body><figure id="f"><step who="all" action="x" beats="3"/></figure></body>
      </fdml>
      """;
    Path p = Files.createTempFile("fdml-missing-meter", ".xml");
    Files.writeString(p, xml);

    var rs = TimingValidator.validateCollect(List.of(p));
    assertTrue(rs.get(0).issues.stream().anyMatch(i -> "missing_meter".equals(i.code)),
      "Expected missing_meter");
  }

  @Test
  public void badMeterFormatIsReported() throws Exception {
    String xml = """
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.1">
        <meta><title>t</title><meter value="3-4"/></meta>
        <body><figure id="f"><step who="all" action="x" beats="3"/></figure></body>
      </fdml>
      """;
    Path p = Files.createTempFile("fdml-bad-meter", ".xml");
    Files.writeString(p, xml);

    var rs = TimingValidator.validateCollect(List.of(p));
    assertTrue(rs.get(0).issues.stream().anyMatch(i -> "bad_meter_format".equals(i.code)),
      "Expected bad_meter_format");
  }

  @Test
  public void badStepBeatsIsReported() throws Exception {
    String xml = """
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.1">
        <meta><title>t</title><meter value="3/4"/></meta>
        <body><figure id="f"><step who="all" action="x" beats="0"/></figure></body>
      </fdml>
      """;
    Path p = Files.createTempFile("fdml-bad-step-beats", ".xml");
    Files.writeString(p, xml);

    var rs = TimingValidator.validateCollect(List.of(p));
    assertTrue(rs.get(0).issues.stream().anyMatch(i -> "bad_step_beats".equals(i.code)),
      "Expected bad_step_beats");
  }

  @Test
  public void additiveMeterRequiresPatternAlignment() throws Exception {
    String xml = """
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.1">
        <meta><title>t</title><meter value="2+2+2+3/16"/></meta>
        <body>
          <figure id="f">
            <step who="all" action="x1" beats="3"/>
            <step who="all" action="x2" beats="6"/>
          </figure>
        </body>
      </fdml>
      """;
    Path p = Files.createTempFile("fdml-additive-pattern", ".xml");
    Files.writeString(p, xml);

    var rs = TimingValidator.validateCollect(List.of(p));
    assertTrue(rs.get(0).issues.stream().anyMatch(i -> "off_meter_figure".equals(i.code)),
      "Expected off_meter_figure for additive boundary mismatch");
  }

  @Test
  public void measureRangeStepsAreIncludedInFigureTotals() throws Exception {
    String xml = """
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.1">
        <meta><title>t</title><meter value="4/4"/></meta>
        <body>
          <figure id="f">
            <measureRange from="1" to="2">
              <step who="all" action="x1" beats="2"/>
            </measureRange>
            <measureRange from="3" to="4">
              <step who="all" action="x2" beats="2"/>
            </measureRange>
          </figure>
        </body>
      </fdml>
      """;
    Path p = Files.createTempFile("fdml-measure-range", ".xml");
    Files.writeString(p, xml);

    var rs = TimingValidator.validateCollect(List.of(p));
    assertTrue(rs.get(0).ok(), "Expected 2+2 in measureRange to satisfy 4/4 timing");
  }

  @Test
  public void nineSixteenLegacyHalfBarCompatibilityPasses() throws Exception {
    String xml = """
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.1">
        <meta><title>t</title><meter value="9/16"/></meta>
        <body>
          <figure id="f">
            <step who="all" action="x1" beats="3"/>
            <step who="all" action="x2" beats="3"/>
          </figure>
        </body>
      </fdml>
      """;
    Path p = Files.createTempFile("fdml-nine-sixteen", ".xml");
    Files.writeString(p, xml);

    var rs = TimingValidator.validateCollect(List.of(p));
    assertTrue(rs.get(0).ok(), "Expected 9/16 legacy half-bar phrase to pass timing");
  }
}
