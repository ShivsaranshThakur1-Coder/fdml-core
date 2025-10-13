package org.fdml.cli;

import com.openhtmltopdf.pdfboxout.PdfRendererBuilder;
import java.io.*;
import java.nio.file.*;

class PdfExporter {

  static void export(Path fdmlFile, Path xslFile, Path examplesDir, Path outPdf) {
    try {
      Files.createDirectories(outPdf.getParent());
      Files.createDirectories(examplesDir);

      Path tempHtml = examplesDir.resolve(".export-temp.html");
      Renderer.render(fdmlFile, xslFile, tempHtml);

      String html = Files.readString(tempHtml);
      String base = examplesDir.toUri().toString();

      try (OutputStream os = Files.newOutputStream(outPdf, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
        PdfRendererBuilder b = new PdfRendererBuilder();
        b.useFastMode();
        b.withHtmlContent(html, base);
        b.toStream(os);
        b.run();
      }

      Files.deleteIfExists(tempHtml);
      System.out.println("PDF: " + outPdf);
    } catch (Exception e) {
      throw new RuntimeException("PDF export failed for " + fdmlFile + " → " + outPdf, e);
    }
  }
}
