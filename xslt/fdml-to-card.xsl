<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" indent="yes"/>
  <xsl:key name="figById" match="figure" use="@id"/>

  <xsl:template match="/">
    <html>
      <head><title>FDML Render</title><link rel="stylesheet" href="../css/print.css"/></head>
      <body><h1>FDML Render (placeholder)</h1><xsl:apply-templates select="fdml"/></body>
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

      <xsl:if test="body/sequence">
        <xsl:for-each select="body/sequence">
          <xsl:call-template name="sequenceCard"/>
        </xsl:for-each>
      </xsl:if>

      <xsl:choose>
        <xsl:when test="body/figure">
          <xsl:for-each select="body/figure"><xsl:call-template name="figureCard"/></xsl:for-each>
        </xsl:when>
        <xsl:otherwise><div class="body"><xsl:apply-templates select="body/*"/></div></xsl:otherwise>
      </xsl:choose>
    </div>
  </xsl:template>

  <xsl:template name="sequenceCard">
    <xsl:variable name="meterVal" select="/fdml/meta/meter/@value"/>
    <xsl:variable name="beatsPerBar" select="number(substring-before($meterVal, '/'))"/>
    <xsl:variable name="grand" select="sum(for $u in use return (sum(key('figById', $u/@figure)/step/@beats) * (if ($u/@repeat) then number($u/@repeat) else 1)))"/>
    <xsl:variable name="bars" select="if ($beatsPerBar gt 0) then ($grand div $beatsPerBar) else ()"/>
    <div class="figure-card">
      <h2>
        <xsl:text>Sequence</xsl:text>
        <xsl:if test="@name"><xsl:text>: </xsl:text><xsl:value-of select="@name"/></xsl:if>
        <span class="beats">
          <xsl:text> — Total: </xsl:text><xsl:value-of select="$grand"/><xsl:text> beats</xsl:text>
          <xsl:if test="$bars"><xsl:text> (~</xsl:text><xsl:value-of select="format-number($bars,'0.##')"/><xsl:text> bars @ </xsl:text><xsl:value-of select="$meterVal"/><xsl:text>)</xsl:text></xsl:if>
        </span>
      </h2>
      <table class="steps">
        <thead><tr><th>#</th><th>Figure</th><th>Name</th><th>Repeat</th><th>Beats each</th><th>Subtotal</th></tr></thead>
        <tbody>
          <xsl:for-each select="use">
            <xsl:variable name="fig" select="key('figById', @figure)[1]"/>
            <xsl:variable name="rep" select="if (@repeat) then number(@repeat) else 1"/>
            <xsl:variable name="each" select="sum($fig/step/@beats)"/>
            <xsl:variable name="sub" select="$each * $rep"/>
            <tr>
              <td><xsl:value-of select="position()"/></td>
              <td><code><xsl:value-of select="@figure"/></code></td>
              <td><xsl:value-of select="$fig/@name"/></td>
              <td><xsl:value-of select="$rep"/></td>
              <td><xsl:value-of select="$each"/></td>
              <td><xsl:value-of select="$sub"/></td>
            </tr>
          </xsl:for-each>
        </tbody>
      </table>
    </div>
  </xsl:template>

  <xsl:template name="figureCard">
    <xsl:variable name="beats" select="sum(step/@beats)"/>
    <xsl:variable name="meterVal" select="/fdml/meta/meter/@value"/>
    <xsl:variable name="beatsPerBar" select="number(substring-before($meterVal, '/'))"/>
    <xsl:variable name="bars" select="if ($beatsPerBar gt 0) then ($beats div $beatsPerBar) else ()"/>
    <div class="figure-card">
      <h2>
        <xsl:text>Figure</xsl:text>
        <xsl:if test="@name"><xsl:text>: </xsl:text><xsl:value-of select="@name"/></xsl:if>
        <xsl:if test="@formation"><xsl:text> (</xsl:text><xsl:value-of select="@formation"/><xsl:text>)</xsl:text></xsl:if>
        <span class="beats"> — Total: <xsl:value-of select="$beats"/> beats<xsl:if test="$bars"> (~<xsl:value-of select="format-number($bars,'0.##')"/> bars @ <xsl:value-of select="$meterVal"/>)</xsl:if></span>
      </h2>
      <table class="steps">
        <thead><tr><th>#</th><th>Who</th><th>Action</th><th>Beats</th><th>Count</th><th>Foot</th><th>Direction</th><th>Facing</th><th>Notes</th></tr></thead>
        <tbody>
          <xsl:for-each select="step">
            <tr>
              <td><xsl:value-of select="position()"/></td>
              <td><xsl:value-of select="@who"/></td>
              <td><xsl:value-of select="@action"/></td>
              <td><xsl:value-of select="@beats"/></td>
              <td><xsl:value-of select="@count"/></td>
              <td><xsl:value-of select="@startFoot"/><xsl:if test="@endFoot"><xsl:text>→</xsl:text><xsl:value-of select="@endFoot"/></xsl:if></td>
              <td><xsl:value-of select="@direction"/></td>
              <td><xsl:value-of select="@facing"/></td>
              <td><xsl:value-of select="normalize-space(.)"/></td>
            </tr>
          </xsl:for-each>
        </tbody>
      </table>
    </div>
  </xsl:template>

  <xsl:template match="section"><div class="section"><xsl:value-of select="normalize-space(.)"/></div></xsl:template>
  <xsl:template match="@*|node()"><xsl:apply-templates select="@*|node()"/></xsl:template>
</xsl:stylesheet>
