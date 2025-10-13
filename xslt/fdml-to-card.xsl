<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" indent="yes"/>

  <xsl:template match="/">
    <html>
      <head>
        <title>FDML Render</title>
        <link rel="stylesheet" href="../css/print.css"/>
      </head>
      <body>
        <h1>FDML Render (placeholder)</h1>
        <xsl:apply-templates select="fdml"/>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="fdml">
    <div class="fdml">
      <div class="meta">
        <xsl:if test="meta/title"><div class="title"><xsl:value-of select="normalize-space(meta/title)"/></div></xsl:if>
        <xsl:if test="meta/dance/@name"><div class="dance">Dance: <xsl:value-of select="meta/dance/@name"/></div></xsl:if>
        <xsl:if test="meta/meter/@value"><div class="meter">Meter: <xsl:value-of select="meta/meter/@value"/></div></xsl:if>
        <xsl:if test="meta/tempo/@bpm"><div class="tempo">Tempo: <xsl:value-of select="meta/tempo/@bpm"/> bpm</div></xsl:if>
        <xsl:if test="meta/author"><div class="author"><xsl:value-of select="normalize-space(meta/author)"/></div></xsl:if>
      </div>

      <xsl:choose>
        <xsl:when test="body/figure">
          <xsl:for-each select="body/figure">
            <xsl:call-template name="figureCard"/>
          </xsl:for-each>
        </xsl:when>
        <xsl:otherwise>
          <div class="body"><xsl:apply-templates select="body/*"/></div>
        </xsl:otherwise>
      </xsl:choose>
    </div>
  </xsl:template>

  <xsl:template name="figureCard">
    <div class="figure-card">
      <h2>
        <xsl:text>Figure</xsl:text>
        <xsl:if test="@name"><xsl:text>: </xsl:text><xsl:value-of select="@name"/></xsl:if>
        <xsl:if test="@formation"><xsl:text> (</xsl:text><xsl:value-of select="@formation"/><xsl:text>)</xsl:text></xsl:if>
      </h2>
      <table class="steps">
        <thead>
          <tr>
            <th>#</th><th>Who</th><th>Action</th><th>Beats</th><th>Count</th><th>Foot</th><th>Direction</th><th>Facing</th><th>Notes</th>
          </tr>
        </thead>
        <tbody>
          <xsl:for-each select="step">
            <tr>
              <td><xsl:value-of select="position()"/></td>
              <td><xsl:value-of select="@who"/></td>
              <td><xsl:value-of select="@action"/></td>
              <td><xsl:value-of select="@beats"/></td>
              <td><xsl:value-of select="@count"/></td>
              <td>
                <xsl:value-of select="@startFoot"/>
                <xsl:if test="@endFoot"><xsl:text>→</xsl:text><xsl:value-of select="@endFoot"/></xsl:if>
              </td>
              <td><xsl:value-of select="@direction"/></td>
              <td><xsl:value-of select="@facing"/></td>
              <td><xsl:value-of select="normalize-space(.)"/></td>
            </tr>
          </xsl:for-each>
        </tbody>
      </table>
    </div>
  </xsl:template>

  <xsl:template match="section">
    <div class="section"><xsl:value-of select="normalize-space(.)"/></div>
  </xsl:template>

  <xsl:template match="@*|node()">
    <xsl:apply-templates select="@*|node()"/>
  </xsl:template>
</xsl:stylesheet>
