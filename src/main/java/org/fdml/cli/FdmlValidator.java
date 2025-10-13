package org.fdml.cli;

import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.*;
import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;

class FdmlValidator {

  static class Result {
    final Path file;
    final boolean ok;
    final String message;
    final Integer line;
    final Integer column;
    Result(Path file, boolean ok, String message, Integer line, Integer column) {
      this.file = file;
      this.ok = ok;
      this.message = message;
      this.line = line;
      this.column = column;
    }
  }

  private final Schema schema;

  FdmlValidator(Path xsdPath) {
    try {
      SchemaFactory sf = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
      this.schema = sf.newSchema(xsdPath.toFile());
    } catch (SAXException e) {
      throw new RuntimeException("Failed to load schema: " + xsdPath, e);
    }
  }

  List<Result> validateCollect(List<Path> inputs) {
    List<Path> files = expandAll(inputs);
    List<Result> out = new ArrayList<>();
    for (Path f : files) out.add(validateOne(f));
    return out;
  }

  boolean validatePaths(List<Path> inputs) {
    List<Result> results = validateCollect(inputs);
    boolean allOk = true;
    for (Result r : results) {
      if (r.ok) System.out.println("OK  : " + r.file);
      else System.out.println("FAIL: " + r.file + (r.message != null ? " : " + r.message : ""));
      allOk &= r.ok;
    }
    System.out.printf("Validated %d file(s).%n", results.size());
    return allOk;
  }

  private Result validateOne(Path f) {
    try {
      Validator v = schema.newValidator();
      v.validate(new StreamSource(f.toFile()));
      return new Result(f, true, null, null, null);
    } catch (SAXParseException e) {
      String msg = String.format("(line %d, col %d): %s", e.getLineNumber(), e.getColumnNumber(), e.getMessage());
      return new Result(f, false, msg, e.getLineNumber(), e.getColumnNumber());
    } catch (SAXException | IOException e) {
      return new Result(f, false, e.getMessage(), null, null);
    }
  }

  private List<Path> expandAll(List<Path> inputs) {
    List<Path> files = new ArrayList<>();
    for (Path p : inputs) {
      if (Files.isDirectory(p)) {
        try {
          Files.walk(p).filter(Files::isRegularFile).filter(this::looksLikeXml).forEach(files::add);
        } catch (IOException e) { throw new RuntimeException(e); }
      } else {
        files.add(p);
      }
    }
    return files;
  }

  private boolean looksLikeXml(Path p) {
    String n = p.getFileName().toString().toLowerCase();
    return n.endsWith(".xml") || n.endsWith(".fdml") || n.endsWith(".fdml.xml");
  }
}
