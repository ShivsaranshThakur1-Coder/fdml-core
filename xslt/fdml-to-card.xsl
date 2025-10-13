<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="html" indent="yes" />

  <xsl:template match="/">
    <html>
      <head>
        <title>FDML Render</title>
        <link rel="stylesheet" href="../css/print.css"/>
      </head>
      <body>
        <h1>FDML Render (placeholder)</h1>
        <xsl:apply-templates/>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="fdml">
    <div class="fdml">
      <div class="meta"><xsl:apply-templates select="meta/*"/></div>
      <div class="body"><xsl:apply-templates select="body/*"/></div>
    </div>
  </xsl:template>

  <xsl:template match="*">
    <div class="{name()}">
      <xsl:value-of select="normalize-space(.)"/>
    </div>
  </xsl:template>
</xsl:stylesheet>
