package org.fdml.cli;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.util.*;

class SchematronValidator {
  static class Result {
    final Path file;
    final boolean ok;
    final int failures;
    final List<String> messages;
    Result(Path file, boolean ok, int failures, List<String> messages) {
      this.file = file; this.ok = ok; this.failures = failures; this.messages = messages;
    }
  }

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

  List<Result> validateCollect(List<Path> inputs) {
    List<Path> files = expandAll(inputs);
    List<Result> out = new ArrayList<>();
    for (Path f : files) out.add(validateFile(f));
    return out;
  }

  boolean validatePaths(List<Path> inputs) {
    List<Result> results = validateCollect(inputs);
    boolean allOk = true;
    for (Result r : results) {
      if (r.ok) System.out.println("SCH OK  : " + r.file);
      else {
        System.out.println("SCH FAIL: " + r.file + " (" + r.failures + " failure(s))");
        if (!r.messages.isEmpty()) System.out.println("  \u2192 " + String.join(" | ", r.messages));
      }
      allOk &= r.ok;
    }
    System.out.printf("Schematron checked %d file(s).%n", results.size());
    return allOk;
  }

  private Result validateFile(Path xml) {
    try {
      XsltTransformer t = compiledSchematron.load();
      XdmDestination dest = new XdmDestination();
      t.setSource(new StreamSource(xml.toFile()));
      t.setDestination(dest);
      t.transform();

      XPathCompiler xpc = proc.newXPathCompiler();
      xpc.declareNamespace("svrl","http://purl.oclc.org/dsdl/svrl");

      XdmNode svrl = dest.getXdmNode();
      XdmValue failed = xpc.evaluate("//svrl:failed-assert", svrl);
      int count = failed.size();

      List<String> msgs = new ArrayList<>();
      XdmValue texts = xpc.evaluate("//svrl:failed-assert/svrl:text/string()", svrl);
      for (XdmItem i : texts) msgs.add(i.getStringValue());

      return new Result(xml, count == 0, count, msgs);
    } catch (Exception e) {
      return new Result(xml, false, 1, List.of("Schematron error: " + e.getMessage()));
    }
  }

  private List<Path> expandAll(List<Path> inputs) {
    List<Path> out = new ArrayList<>();
    for (Path p : inputs) {
      try {
        if (Files.isDirectory(p)) Files.walk(p).filter(Files::isRegularFile).forEach(out::add);
        else out.add(p);
      } catch (Exception e) { throw new RuntimeException(e); }
    }
    return out;
  }
}
