package org.fdml.cli;

import java.nio.file.*;
import java.util.*;

public class Main {
  private static final int EXIT_OK = 0;
  private static final int EXIT_VALIDATION_ERR = 2;
  private static final int EXIT_TRANSFORM_ERR = 3;
  private static final int EXIT_IO_ERR = 4;

  public static void main(String[] args) {
    if (args.length < 1) { usage(); System.exit(EXIT_IO_ERR); }
    String cmd = args[0];
    try {
      switch (cmd) {
        case "validate": {
          if (args.length < 2) { System.err.println("validate: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schemaPath = Paths.get("schema/fdml.xsd");
          FdmlValidator validator = new FdmlValidator(schemaPath);
          List<Path> targets = collectTargets(args, 1);
          boolean allOk = validator.validatePaths(targets);
          System.exit(allOk ? EXIT_OK : EXIT_VALIDATION_ERR);
        }

        case "validate-sch": {
          if (args.length < 2) { System.err.println("validate-sch: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schXsl = Paths.get("schematron/fdml-compiled.xsl");
          SchematronValidator sch = new SchematronValidator(schXsl);
          List<Path> targets = collectTargets(args, 1);
          boolean allOk = sch.validatePaths(targets);
          System.exit(allOk ? EXIT_OK : EXIT_VALIDATION_ERR);
        }

        case "validate-all": {
          if (args.length < 2) { System.err.println("validate-all: provide at least one file or directory"); System.exit(EXIT_IO_ERR); }
          Path schemaPath = Paths.get("schema/fdml.xsd");
          FdmlValidator validator = new FdmlValidator(schemaPath);
          Path schXsl = Paths.get("schematron/fdml-compiled.xsl");
          SchematronValidator sch = new SchematronValidator(schXsl);
          List<Path> targets = collectTargets(args, 1);
          boolean ok1 = validator.validatePaths(targets);
          boolean ok2 = sch.validatePaths(targets);
          System.exit(ok1 && ok2 ? EXIT_OK : EXIT_VALIDATION_ERR);
        }

        case "render": {
          if (args.length < 2) { System.err.println("render: provide <fdml-file> [--out path]"); System.exit(EXIT_IO_ERR); }
          Path in  = Paths.get(args[1]);
          Path out = Paths.get("out/render.html");
          for (int i = 2; i < args.length; i++) {
            if ("--out".equals(args[i]) && i + 1 < args.length) { out = Paths.get(args[++i]); }
          }
          Path xsl = Paths.get("xslt/fdml-to-card.xsl");
          Renderer.render(in, xsl, out);
          System.exit(EXIT_OK);
        }

        default: { usage(); System.exit(EXIT_IO_ERR); }
      }
    } catch (Exception e) {
      e.printStackTrace();
      System.exit(EXIT_IO_ERR);
    }
  }

  private static List<Path> collectTargets(String[] args, int from) {
    List<Path> t = new ArrayList<>();
    for (int i = from; i < args.length; i++) t.add(Paths.get(args[i]));
    return t;
  }

  private static void usage() {
    System.out.println("FDML CLI");
    System.out.println("Usage:");
    System.out.println("  validate <file-or-dir> [more paths...]     # XSD");
    System.out.println("  validate-sch <file-or-dir> [more paths...] # Schematron (compiled XSLT)");
    System.out.println("  validate-all <file-or-dir> [...]           # XSD + Schematron");
    System.out.println("  render <fdml-file> [--out out.html]        # XSLT → HTML");
  }
}
