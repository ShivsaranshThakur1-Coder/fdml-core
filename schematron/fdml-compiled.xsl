<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:svrl="http://purl.oclc.org/dsdl/svrl">

  <xsl:output method="xml" indent="yes"/>

  <xsl:template match="/">
    <svrl:schematron-output>
      <xsl:apply-templates select="/*"/>
    </svrl:schematron-output>
  </xsl:template>

  <xsl:template match="fdml">
    <xsl:if test="not(meta)">
      <svrl:failed-assert><svrl:text>fdml must contain meta</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="not(body)">
      <svrl:failed-assert><svrl:text>fdml must contain body</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:if test="not(normalize-space(meta/title))">
      <svrl:failed-assert><svrl:text>meta/title must be present and non-empty</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="string-length(normalize-space(meta/title)) &gt; 120">
      <svrl:failed-assert><svrl:text>meta/title must be ≤ 120 characters</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:variable name="email" select="normalize-space(meta/author/@email)"/>
    <xsl:if test="meta/author/@email and not(matches($email, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'))">
      <svrl:failed-assert><svrl:text>meta/author/@email is not a valid email</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:if test="body and not(body/section or body/figure)">
      <svrl:failed-assert><svrl:text>body must contain at least one &lt;section&gt; or &lt;figure&gt;</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:apply-templates select="body"/>
  </xsl:template>

  <xsl:template match="body">
    <xsl:for-each select="figure">
      <xsl:if test="not(@id)">
        <svrl:failed-assert><svrl:text>figure must have @id</svrl:text></svrl:failed-assert>
      </xsl:if>
      <xsl:if test="@id and not(matches(@id, '^f-[a-z0-9-]+$'))">
        <svrl:failed-assert><svrl:text>figure/@id must match pattern 'f-[a-z0-9-]+'</svrl:text></svrl:failed-assert>
      </xsl:if>
      <xsl:if test="@id and count(//figure[@id=current()/@id]) &gt; 1">
        <svrl:failed-assert><svrl:text>figure/@id values must be unique across the document</svrl:text></svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(step)">
        <svrl:failed-assert><svrl:text>figure must contain at least one step</svrl:text></svrl:failed-assert>
      </xsl:if>
      <xsl:for-each select="step">
        <xsl:if test="not(@beats) or number(@beats) &lt; 1">
          <svrl:failed-assert><svrl:text>step/@beats must be ≥ 1</svrl:text></svrl:failed-assert>
        </xsl:if>
        <xsl:if test="not(@who)">
          <svrl:failed-assert><svrl:text>step/@who is required</svrl:text></svrl:failed-assert>
        </xsl:if>
        <xsl:if test="not(@startFoot)">
          <svrl:failed-assert><svrl:text>step/@startFoot is required</svrl:text></svrl:failed-assert>
        </xsl:if>
      </xsl:for-each>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="@*|node()">
    <xsl:apply-templates select="@*|node()"/>
  </xsl:template>
</xsl:stylesheet>
