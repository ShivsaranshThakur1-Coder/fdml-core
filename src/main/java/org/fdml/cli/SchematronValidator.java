package org.fdml.cli;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.util.*;

class SchematronValidator {
  private final Processor proc;
  private final XsltExecutable compiledSchematron;

  SchematronValidator(Path compiledSchematronXsl) {
    try {
      proc = new Processor(false);
      XsltCompiler comp = proc.newXsltCompiler();
      compiledSchematron = comp.compile(new StreamSource(compiledSchematronXsl.toFile()));
    } catch (SaxonApiException e) {
      throw new RuntimeException("Failed to load compiled Schematron: " + compiledSchematronXsl, e);
    }
  }

  boolean validatePaths(List<Path> paths) {
    List<Path> files = new ArrayList<>();
    for (Path p : paths) files.addAll(expand(p));
    boolean allOk = true;
    for (Path f : files) {
      boolean ok = validateFile(f);
      allOk = allOk && ok;
    }
    System.out.printf("Schematron checked %d file(s).%n", files.size());
    return allOk;
  }

  private List<Path> expand(Path p) {
    List<Path> out = new ArrayList<>();
    try {
      if (Files.isDirectory(p)) {
        Files.walk(p).filter(Files::isRegularFile).forEach(out::add);
      } else out.add(p);
    } catch (Exception e) { throw new RuntimeException(e); }
    return out;
  }

  private boolean validateFile(Path xml) {
    try {
      XsltTransformer t = compiledSchematron.load();
      XdmDestination dest = new XdmDestination();
      t.setSource(new StreamSource(xml.toFile()));
      t.setDestination(dest);
      t.transform();

      XPathCompiler xpc = proc.newXPathCompiler();
      xpc.declareNamespace("svrl","http://purl.oclc.org/dsdl/svrl");

      XdmNode svrl = dest.getXdmNode();
      XdmValue failures = xpc.evaluate("//svrl:failed-assert", svrl);

      if (failures.size() == 0) {
        System.out.println("SCH OK  : " + xml);
        return true;
      } else {
        System.out.println("SCH FAIL: " + xml + " (" + failures.size() + " failure(s))");
        XdmValue msgs = xpc.evaluate("string-join(//svrl:failed-assert/svrl:text, ' | ')", svrl);
        System.out.println("  → " + msgs.toString());
        return false;
      }
    } catch (Exception e) {
      System.out.println("SCH ERR : " + xml + " : " + e.getMessage());
      return false;
    }
  }
}
