<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" omit-xml-declaration="yes"/>
  <xsl:param name="cssVersion" select="'nocache'"/>

  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta name="color-scheme" content="dark light"/>
        <title>FDML: <xsl:value-of select="/fdml/meta/title"/></title>
        <link rel="stylesheet" href="{concat('style.css?', $thisVersion)}"/>
        <xsl:variable name="thisVersion" select="$cssVersion"/>
      </head>
      <body>
        <header class="site-head">
          <div class="container">
            <a class="brand" href="index.html">FDML</a>
            <nav class="nav">
              <a href="index.html">Examples</a>
              <a href="https://github.com/ShivsaranshThakur1-Coder/fdml-core" target="_blank" rel="noopener">GitHub</a>
            </nav>
          </div>
        </header>

        <main class="container">
          <div class="card">
            <h1><xsl:value-of select="/fdml/meta/title"/></h1>
            <p class="sub">
              <span>Meter <code><xsl:value-of select="/fdml/meta/meter"/></code></span>
              &#160;•&#160;
              <span>Tempo <xsl:text> </xsl:text><code><xsl:value-of select="/fdml/meta/tempo"/></code></span>
            </p>

            <xsl:if test="/fdml/body/figure">
              <table class="table">
                <thead>
                  <tr><th>Figure</th><th>Name</th></tr>
                </thead>
                <tbody>
                  <xsl:for-each select="/fdml/body/figure">
                    <tr>
                      <td>
                        <button class="chip copy-btn" data-copy="{@id}" title="Copy ID">
                          <code><xsl:value-of select="@id"/></code>
                          <span class="copy-icon">⧉</span>
                        </button>
                      </td>
                      <td><xsl:value-of select="@name"/></td>
                    </tr>
                  </tr>
                  </xsl:for-each>
                </tbody>
              </table>
            </xsl:if>

            <p class="sub">Generated from FDML</p>
            <p class="sub"><a class="muted" href="index.html">← Back to all examples</a></p>
          </div>
        </main>

        <footer><div class="container">© <xsl:value-of select="substring-before(/fdml/meta/date,'-')"/> FDML</div></footer>

        <script>
        document.addEventListener('click', function(e){
          var btn = e.target.closest('[data-copy]');
          if(!btn) return;
          var txt = btn.getAttribute('data-copy') || '';
          if (navigator.clipboard) { navigator.clipboard.writeText(txt); }
          btn.classList.add('copied');
          setTimeout(function(){ btn.classList.remove('copied'); }, 1200);
        });
        </script>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
