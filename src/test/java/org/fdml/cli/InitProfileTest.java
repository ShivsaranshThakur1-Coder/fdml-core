package org.fdml.cli;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class InitProfileTest {

  @Test
  public void initProfilesProduceDoctorStrictPassingFixtures() throws Exception {
    List<String> profiles = List.of(
      "v1-basic",
      "v12-circle",
      "v12-line",
      "v12-twoLinesFacing",
      "v12-couple"
    );

    Path tmpDir = Files.createTempDirectory("fdml-init-profiles");
    for (String profile : profiles) {
      Path out = tmpDir.resolve(profile + ".fdml.xml");

      Init.run(new String[]{
        "init",
        out.toString(),
        "--title", "Init Profile " + profile,
        "--profile", profile
      });

      assertTrue(Files.exists(out), "Expected init output file for profile " + profile);

      int code = Doctor.run(new String[]{
        "doctor",
        out.toString(),
        "--strict"
      });
      assertEquals(0, code, "Expected strict doctor pass for profile " + profile);
    }
  }
}
