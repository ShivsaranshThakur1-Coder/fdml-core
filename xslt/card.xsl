<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" indent="no" omit-xml-declaration="yes"/>
  <xsl:param name="cssVersion" select="'0'"/>
  <xsl:template match="/">
    <html>
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title>FDML: <xsl:value-of select="/fdml/meta/title"/></title>
        <link rel="stylesheet" href="style.css?{$cssVersion}"/>
      </head>
      <body>
        <header class="site-head">
          <div class="container">
            <a class="brand" href="../index.html">FDML</a>
            <nav class="nav">
              <a href="../index.html">Examples</a>
              <a href="https://github.com/ShivsaranshThakur1-Coder/fdml-core" target="_blank" rel="noopener">GitHub</a>
            </nav>
          </div>
        </header>
        <main class="container">
          <div class="card">
            <h1><xsl:value-of select="/fdml/meta/title"/></h1>
            <p class="sub">
              Meter <code><xsl:value-of select="/fdml/meta/meter"/></code>
              &#160;•&#160;
              Tempo <code><xsl:value-of select="/fdml/meta/tempo"/></code>
            </p>
            <xsl:if test="/fdml/body/figure">
              <table class="spec">
                <thead>
                  <tr><th>Figure</th><th>Name</th></tr>
                </thead>
                <tbody>
                  <xsl:for-each select="/fdml/body/figure">
                    <tr>
                      <td><code><xsl:value-of select="@id"/></code></td>
                      <td><xsl:value-of select="@name"/></td>
                    </tr>
                  </xsl:for-each>
                </tbody>
              </table>
            </xsl:if>
            <p class="meta">Generated from FDML</p>
            <p class="meta"><a class="muted" href="../index.html">← Back to all examples</a></p>
          </div>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
