<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="html" encoding="UTF-8" indent="no"/>

  <xsl:template match="/fdml">
    <html>
      <head>
        <meta charset="utf-8"/>
        <title>FDML: <xsl:value-of select="normalize-space(meta/title)"/></title>
        <style type="text/css">
          body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:2rem;max-width:900px}
          .card{border:1px solid #e5e7eb;border-radius:14px;padding:1.25rem;box-shadow:0 1px 2px rgba(0,0,0,0.04)}
          h1{margin:0 0 .25rem 0;font-size:1.6rem}
          .sub{color:#6b7280;margin:0 0 1rem 0}
          table{width:100%;border-collapse:collapse;margin-top:.5rem}
          th,td{padding:.5rem;border-bottom:1px solid #f1f5f9;text-align:left}
          th{color:#334155;font-weight:600;background:#f8fafc}
          .meta{margin:.5rem 0 0 0;color:#475569}
          code{background:#f1f5f9;padding:.1rem .4rem;border-radius:6px}
        </style>
      </head>
      <body>
        <div class="card">
          <h1><xsl:value-of select="normalize-space(meta/title)"/></h1>
          <p class="sub">
            Meter: <code><xsl:value-of select="normalize-space(meta/meter)"/></code>
            &#160;•&#160;
            Tempo: <code><xsl:value-of select="normalize-space(meta/tempo)"/></code>
          </p>

          <xsl:if test="body/figure">
            <table>
              <thead>
                <tr><th>Figure ID</th><th>Name</th></tr>
              </thead>
              <tbody>
                <xsl:for-each select="body/figure">
                  <tr>
                    <td><code><xsl:value-of select="@id"/></code></td>
                    <td><xsl:value-of select="@name"/></td>
                  </tr>
                </xsl:for-each>
              </tbody>
            </table>
          </xsl:if>

          <p class="meta">Generated from FDML via XSLT.</p>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
