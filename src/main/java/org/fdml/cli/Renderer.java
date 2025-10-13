package org.fdml.cli;

import net.sf.saxon.s9api.*;
import javax.xml.transform.stream.StreamSource;
import java.io.File;
import java.nio.file.Path;

class Renderer {
  static void render(Path xmlPath, Path xslPath, Path outPath) {
    try {
      Processor proc = new Processor(false);
      XsltCompiler comp = proc.newXsltCompiler();
      XsltExecutable exec = comp.compile(new StreamSource(xslPath.toFile()));
      XsltTransformer t = exec.load();
      t.setSource(new StreamSource(xmlPath.toFile()));
      Serializer s = proc.newSerializer(new File(outPath.toString()));
      s.setOutputProperty(Serializer.Property.INDENT, "yes");
      t.setDestination(s);
      t.transform();
      System.out.println("Rendered: " + outPath);
    } catch (Exception e) {
      throw new RuntimeException("Render failed for " + xmlPath + " with " + xslPath, e);
    }
  }
}
