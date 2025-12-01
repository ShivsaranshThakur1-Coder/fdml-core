<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:param name="cssVersion" select="'0'"/>

  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta name="color-scheme" content="dark light"/>
        <title>FDML: <xsl:value-of select="/fdml/meta/title"/></title>
        <link rel="stylesheet">
          <xsl:attribute name="href">./style.css?<xsl:value-of select="$cssVersion"/></xsl:attribute>
        </link>
      </head>
      <body>
        <header class="site-head">
          <div class="container">
            <a class="brand" href="../index.html">FDML</a>
            <nav class="nav">
              <a href="../index.html">Examples</a>
              <a href="../search.html">Search</a>
              <a href="https://github.com/ShivsaranshThakur1-Coder/fdml-core" target="_blank" rel="noopener">GitHub</a>
            </nav>
          </div>
        </header>

        <main class="container">
          <div class="card">
            <!-- Title -->
            <h1><xsl:value-of select="/fdml/meta/title"/></h1>

            <!-- High-level meta chips -->
            <p class="sub">
              <xsl:if test="/fdml/meta/origin/@country">
                <span>
                  Origin
                  <code><xsl:value-of select="/fdml/meta/origin/@country"/></code>
                </span>
              </xsl:if>
              <xsl:if test="/fdml/meta/type/@genre">
                &#160;•&#160;
                <span>
                  Type
                  <code><xsl:value-of select="/fdml/meta/type/@genre"/></code>
                </span>
              </xsl:if>
              <xsl:if test="/fdml/meta/type/@style">
                &#160;•&#160;
                <span>
                  Style
                  <code><xsl:value-of select="/fdml/meta/type/@style"/></code>
                </span>
              </xsl:if>
            </p>

            <!-- Meter / Tempo -->
            <p class="sub">
              <span>
                Meter
                <code><xsl:value-of select="/fdml/meta/meter/@value"/></code>
              </span>
              &#160;•&#160;
              <span>
                Tempo
                <code>
                  <xsl:value-of select="/fdml/meta/tempo/@bpm"/>
                  <xsl:if test="/fdml/meta/tempo/@bpm"> bpm</xsl:if>
                </code>
              </span>
            </p>

            <!-- Parts / Figures table for v1.1 (body/part/figure) -->
            <xsl:if test="/fdml/body/part">
              <h2>Structure</h2>
              <table>
                <thead>
                  <tr>
                    <th>Part</th>
                    <th>Figure</th>
                    <th>Name</th>
                  </tr>
                </thead>
                <tbody>
                  <xsl:for-each select="/fdml/body/part">
                    <xsl:variable name="partLabel">
                      <xsl:choose>
                        <xsl:when test="@label"><xsl:value-of select="@label"/></xsl:when>
                        <xsl:otherwise><xsl:value-of select="@id"/></xsl:otherwise>
                      </xsl:choose>
                    </xsl:variable>
                    <xsl:for-each select="figure">
                      <tr>
                        <td><code><xsl:value-of select="$partLabel"/></code></td>
                        <td><code><xsl:value-of select="@id"/></code></td>
                        <td><xsl:value-of select="@name"/></td>
                      </tr>
                    </xsl:for-each>
                  </xsl:for-each>
                </tbody>
              </table>
            </xsl:if>

            <!-- Fallback: v1.0 style, top-level figures under body -->
            <xsl:if test="not(/fdml/body/part) and /fdml/body/figure">
              <h2>Figures</h2>
              <table>
                <thead>
                  <tr>
                    <th>Figure</th>
                    <th>Name</th>
                  </tr>
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

            <!-- Notes / sections -->
            <xsl:if test="/fdml/body/section">
              <h2>Notes</h2>
              <xsl:for-each select="/fdml/body/section">
                <p class="sub">
                  <xsl:if test="@type">
                    <strong><xsl:value-of select="@type"/>:</strong>
                    &#160;
                  </xsl:if>
                  <xsl:value-of select="normalize-space(.)"/>
                </p>
              </xsl:for-each>
            </xsl:if>

            <p class="sub">Generated from FDML</p>
            <p class="sub">
              <a class="muted" href="../index.html">← Back to all examples</a>
            </p>
          </div>
        </main>

        <footer>
          <div class="container">© FDML</div>
        </footer>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>

