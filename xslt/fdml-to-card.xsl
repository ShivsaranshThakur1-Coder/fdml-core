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
    <xsl:variable name="beats" select="sum(step/@beats)"/>
    <xsl:variable name="meterVal" select="/fdml/meta/meter/@value"/>
    <xsl:variable name="beatsPerBar" select="number(substring-before($meterVal, '/'))"/>
    <xsl:variable name="bars" select="if (number($beatsPerBar)=number($beatsPerBar) and $beatsPerBar &gt; 0) then ($beats div $beatsPerBar) else ()"/>
    <div class="figure-card">
      <h2>
        <xsl:text>Figure</xsl:text>
        <xsl:if test="@name"><xsl:text>: </xsl:text><xsl:value-of select="@name"/></xsl:if>
        <xsl:if test="@formation"><xsl:text> (</xsl:text><xsl:value-of select="@formation"/><xsl:text>)</xsl:text></xsl:if>
        <span class="beats">
          <xsl:text> — Total: </xsl:text><xsl:value-of select="$beats"/><xsl:text> beats</xsl:text>
          <xsl:if test="$bars">
            <xsl:text> (~</xsl:text><xsl:value-of select="format-number($bars,'0.##')"/><xsl:text> bars @ </xsl:text><xsl:value-of select="$meterVal"/><xsl:text>)</xsl:text>
          </xsl:if>
        </span>
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
              <td>
                <xsl:value-of select="@direction"/>
                <xsl:text> </xsl:text>
                <xsl:call-template name="dirIcon">
                  <xsl:with-param name="d" select="@direction"/>
                </xsl:call-template>
              </td>
              <td><xsl:value-of select="@facing"/></td>
              <td><xsl:value-of select="normalize-space(.)"/></td>
            </tr>
          </xsl:for-each>
        </tbody>
      </table>
    </div>
  </xsl:template>

  <xsl:template name="dirIcon">
    <xsl:param name="d"/>
    <xsl:variable name="D" select="normalize-space($d)"/>
    <xsl:choose>
      <xsl:when test="$D='Left'">
        <svg class="dir" width="18" height="18" viewBox="0 0 24 24">
          <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>
          <line x1="20" y1="12" x2="4" y2="12" marker-end="url(#arrow)"/>
        </svg>
      </xsl:when>
      <xsl:when test="$D='Right'">
        <svg class="dir" width="18" height="18" viewBox="0 0 24 24">
          <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>
          <line x1="4" y1="12" x2="20" y2="12" marker-end="url(#arrow)"/>
        </svg>
      </xsl:when>
      <xsl:when test="$D='Fwd'">
        <svg class="dir" width="18" height="18" viewBox="0 0 24 24">
          <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>
          <line x1="12" y1="20" x2="12" y2="4" marker-end="url(#arrow)"/>
        </svg>
      </xsl:when>
      <xsl:when test="$D='Back'">
        <svg class="dir" width="18" height="18" viewBox="0 0 24 24">
          <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>
          <line x1="12" y1="4" x2="12" y2="20" marker-end="url(#arrow)"/>
        </svg>
      </xsl:when>
      <xsl:when test="$D='DiagL'">
        <svg class="dir" width="18" height="18" viewBox="0 0 24 24">
          <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>
          <line x1="18" y1="18" x2="6" y2="6" marker-end="url(#arrow)"/>
        </svg>
      </xsl:when>
      <xsl:when test="$D='DiagR'">
        <svg class="dir" width="18" height="18" viewBox="0 0 24 24">
          <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>
          <line x1="6" y1="18" x2="18" y2="6" marker-end="url(#arrow)"/>
        </svg>
      </xsl:when>
      <xsl:when test="$D='CW'">
        <span class="dir-uni">↻</span>
      </xsl:when>
      <xsl:when test="$D='CCW'">
        <span class="dir-uni">↺</span>
      </xsl:when>
      <xsl:otherwise>
        <span class="dir-uni"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="section">
    <div class="section"><xsl:value-of select="normalize-space(.)"/></div>
  </xsl:template>

  <xsl:template match="@*|node()">
    <xsl:apply-templates select="@*|node()"/>
  </xsl:template>
</xsl:stylesheet>
