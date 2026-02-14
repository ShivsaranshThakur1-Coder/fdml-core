package org.fdml.cli;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

public class DoctorTimingTest {

  @Test
  public void strictDoctorPassesOnValidAbdala() {
    int code = Doctor.run(new String[]{
      "doctor",
      "corpus/valid/abdala.fdml.xml",
      "--strict"
    });
    assertEquals(0, code, "Expected strict doctor to pass for valid abdala");
  }

  @Test
  public void strictDoctorFailsWhenTimingHasIssues() {
    int code = Doctor.run(new String[]{
      "doctor",
      "corpus/invalid_timing/example-off-meter.fdml.xml",
      "--strict"
    });
    assertEquals(2, code, "Expected strict doctor to fail on timing issues");
  }
}
