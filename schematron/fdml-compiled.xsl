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

  <!-- Pattern: basic-rules (compiled) -->
  <xsl:template match="fdml">
    <!-- assert: must have meta -->
    <xsl:if test="not(meta)">
      <svrl:failed-assert test="meta">
        <svrl:text>fdml must contain meta</svrl:text>
      </svrl:failed-assert>
    </xsl:if>
    <!-- assert: must have body -->
    <xsl:if test="not(body)">
      <svrl:failed-assert test="body">
        <svrl:text>fdml must contain body</svrl:text>
      </svrl:failed-assert>
    </xsl:if>
  </xsl:template>

  <xsl:template match="@*|node()">
    <xsl:apply-templates select="@*|node()"/>
  </xsl:template>
</xsl:stylesheet>
