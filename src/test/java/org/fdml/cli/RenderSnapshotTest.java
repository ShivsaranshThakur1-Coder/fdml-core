package org.fdml.cli;

import net.sf.saxon.s9api.*;
import org.junit.jupiter.api.Test;

import javax.xml.transform.stream.StreamSource;
import java.nio.file.*;
import java.io.*;
import static org.junit.jupiter.api.Assertions.*;

public class RenderSnapshotTest {

  private static String normalize(String s) throws Exception {
    // Normalize newlines
    String out = s.replace("\r\n", "\n").replace("\r", "\n");
    // Drop optional DOCTYPE emitted by some HTML serializers
    out = out.replaceAll("(?is)<!DOCTYPE\\s+HTML[^>]*>", "");
    // Drop serializer-inserted Content-Type meta tag (not part of semantics)
    out = out.replaceAll("(?is)<meta\\s+http-equiv=\"Content-Type\"[^>]*>", "");
    // Treat self-closing vs non-self-closing void tags as equal (e.g., <link/> vs <link>)
    out = out.replaceAll("/>", ">");
    // Collapse whitespace
    out = out.replaceAll("\\s+", " ").trim();
    return out;
  }

  @Test
  public void renderExampleMatchesSnapshot() throws Exception {
    Processor proc = new Processor(false);
    XsltCompiler comp = proc.newXsltCompiler();
    XsltExecutable exec = comp.compile(new StreamSource(Paths.get("xslt/fdml-to-card.xsl").toFile()));
    XsltTransformer t = exec.load();
    t.setSource(new StreamSource(Paths.get("corpus/valid/example-01.fdml.xml").toFile()));

    ByteArrayOutputStream baos = new ByteArrayOutputStream();
    Serializer s = proc.newSerializer(baos);
    s.setOutputProperty(Serializer.Property.METHOD, "html");
    s.setOutputProperty(Serializer.Property.INDENT, "yes");
    t.setDestination(s);
    t.transform();

    String actual = normalize(baos.toString("UTF-8"));
    String expected = normalize(Files.readString(Paths.get("src/test/resources/snapshots/example-01.html")));

    assertEquals(expected, actual, "Rendered HTML differs from snapshot");
  }
}
