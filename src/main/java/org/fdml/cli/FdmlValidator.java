package org.fdml.cli;

import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import javax.xml.validation.Validator;
import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

import java.io.IOException;
import java.nio.file.*;
import java.util.*;

class FdmlValidator {
  private final Schema schema;

  FdmlValidator(Path xsdPath) {
    try {
      SchemaFactory sf = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
      this.schema = sf.newSchema(xsdPath.toFile());
    } catch (SAXException e) {
      throw new RuntimeException("Failed to load schema: " + xsdPath, e);
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
    System.out.printf("Validated %d file(s).%n", files.size());
    return allOk;
  }

  private List<Path> expand(Path p) {
    List<Path> out = new ArrayList<>();
    if (Files.isDirectory(p)) {
      try {
        Files.walk(p)
          .filter(Files::isRegularFile)
          .filter(this::looksLikeXml)
          .forEach(out::add);
      } catch (IOException e) {
        throw new RuntimeException(e);
      }
    } else {
      out.add(p);
    }
    return out;
  }

  private boolean looksLikeXml(Path p) {
    String n = p.getFileName().toString().toLowerCase();
    return n.endsWith(".xml") || n.endsWith(".fdml") || n.endsWith(".fdml.xml");
  }

  private boolean validateFile(Path f) {
    try {
      Validator v = schema.newValidator();
      v.validate(new StreamSource(f.toFile()));
      System.out.println("OK  : " + f);
      return true;
    } catch (SAXParseException e) {
      System.out.printf("FAIL: %s (line %d, col %d): %s%n",
          f, e.getLineNumber(), e.getColumnNumber(), e.getMessage());
      return false;
    } catch (SAXException | IOException e) {
      System.out.printf("FAIL: %s : %s%n", f, e.getMessage());
      return false;
    }
  }
}
