<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" omit-xml-declaration="yes"/>

  <xsl:template match="/">
    <html>
      <head>
        <meta charset="utf-8"/>
        <title>FDML: <xsl:value-of select="/fdml/meta/title"/></title>
        <link rel="stylesheet" href="style.css?v=nocache" />
      </head>
      <body>
        <div class="card">
          <h1><xsl:value-of select="/fdml/meta/title"/></h1>
          <p class="sub">
            Meter: <code><xsl:value-of select="/fdml/meta/meter"/></code>
            &#160;&#8226;&#160;
            Tempo: <code><xsl:value-of select="/fdml/meta/tempo"/></code>
          </p>

          <xsl:if test="/fdml/body/figure">
            <table>
              <thead>
                <tr><th>Figure ID</th><th>Name</th></tr>
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

          <p class="meta">Generated from FDML via XSLT.</p>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
