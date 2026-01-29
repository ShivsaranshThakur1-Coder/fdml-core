<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
  <xsl:output method="xml" indent="yes"/>

  <xsl:template match="/"><svrl:schematron-output><xsl:apply-templates select="/*"/></svrl:schematron-output></xsl:template>

  <xsl:template match="fdml">
    <xsl:if test="not(meta)"><svrl:failed-assert><svrl:text>fdml must contain meta</svrl:text></svrl:failed-assert></xsl:if>
    <xsl:if test="not(body)"><svrl:failed-assert><svrl:text>fdml must contain body</svrl:text></svrl:failed-assert></xsl:if>
    <xsl:if test="not(normalize-space(meta/title))"><svrl:failed-assert><svrl:text>meta/title must be present and non-empty</svrl:text></svrl:failed-assert></xsl:if>
    <xsl:if test="string-length(normalize-space(meta/title)) &gt; 120"><svrl:failed-assert><svrl:text>meta/title must be ≤ 120 characters</svrl:text></svrl:failed-assert></xsl:if>
    <xsl:variable name="email" select="normalize-space(meta/author/@email)"/>
    <xsl:if test="meta/author/@email and not(matches($email, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'))"><svrl:failed-assert><svrl:text>meta/author/@email is not a valid email</svrl:text></svrl:failed-assert></xsl:if>
    <xsl:if test="body and not(body/section or body/figure or body/sequence)"><svrl:failed-assert><svrl:text>body must contain at least one &lt;section&gt; or &lt;figure&gt; or &lt;sequence&gt;</svrl:text></svrl:failed-assert></xsl:if>

    <!-- Ontology Batch 1 (FDML v1.2 only) -->
    <xsl:if test="@version = '1.2' and meta/geometry/formation/@kind = 'twoLinesFacing' and not(body/geometry/twoLines/facing)">
      <svrl:failed-assert><svrl:text>twoLinesFacing formation must declare body/geometry/twoLines/facing</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version = '1.2' and meta/geometry/formation/@kind = 'twoLinesFacing' and meta/geometry/roles/role and body/geometry/twoLines/facing and not(meta/geometry/roles/role[@id = body/geometry/twoLines/facing/@a])">
      <svrl:failed-assert><svrl:text>twoLines/facing/@a must reference a declared role id</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version = '1.2' and meta/geometry/formation/@kind = 'twoLinesFacing' and meta/geometry/roles/role and body/geometry/twoLines/facing and not(meta/geometry/roles/role[@id = body/geometry/twoLines/facing/@b])">
      <svrl:failed-assert><svrl:text>twoLines/facing/@b must reference a declared role id</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:if test="@version = '1.2' and meta/geometry/formation/@kind = 'couple' and meta/geometry/formation/@womanSide and not(meta/geometry/roles/role[@id='man'] and meta/geometry/roles/role[@id='woman'])">
      <svrl:failed-assert><svrl:text>couple formation with womanSide must declare roles 'man' and 'woman'</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version = '1.2' and meta/geometry/formation/@kind = 'couple' and meta/geometry/formation/@womanSide and not(body/geometry/couples/pair[(@a='man' and @b='woman') or (@a='woman' and @b='man')])">
      <svrl:failed-assert><svrl:text>couple formation with womanSide must include body/geometry/couples/pair linking man and woman</svrl:text></svrl:failed-assert>
    </xsl:if>

    <!-- Ontology Batch 4B: relpos evidence must exist and match womanSide. -->
    <xsl:variable name="ws" select="normalize-space(meta/geometry/formation/@womanSide)"/>
    <xsl:if test="@version = '1.2' and meta/geometry/formation/@kind = 'couple' and meta/geometry/formation/@womanSide and not((($ws='left') and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='leftOf') or (@a='man' and @b='woman' and @relation='rightOf')])) or (($ws='right') and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='rightOf') or (@a='man' and @b='woman' and @relation='leftOf')])))">
      <svrl:failed-assert><svrl:text>couple formation with womanSide must include at least one relpos primitive asserting the correct side between man and woman</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:if test="@version = '1.2' and contains(meta/meter/@value, '9/16') and not(meta/meter/@rhythmPattern = '2+2+2+3')">
      <svrl:failed-assert><svrl:text>v1.2 dances with meter 9/16 must specify meter/@rhythmPattern='2+2+2+3'</svrl:text></svrl:failed-assert>
    </xsl:if>

    <!-- Ontology Batch 2 (FDML v1.2 only) -->
    <xsl:if test="@version = '1.2' and meta/geometry/hold and not(meta/geometry/hold/@kind = 'vPosition' or meta/geometry/hold/@kind = 'beltHold' or meta/geometry/hold/@kind = 'armenianHold' or meta/geometry/hold/@kind = 'palmToPalm' or meta/geometry/hold/@kind = 'none')">
      <svrl:failed-assert><svrl:text>v1.2 meta/geometry/hold/@kind must be one of: vPosition|beltHold|armenianHold|palmToPalm|none</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version = '1.2' and meta/geometry/hold and not(meta/geometry/hold/@kind = 'none') and .//step/geo/primitive[@kind = 'releaseHold']">
      <svrl:failed-assert><svrl:text>v1.2 dances with hold/@kind != 'none' must not use primitive kind='releaseHold'</svrl:text></svrl:failed-assert>
    </xsl:if>

    <!-- Ontology Batch 4A (FDML v1.2 only): line progression requires explicit line order slots and delta. -->
    <xsl:if test="@version='1.2' and meta/geometry/formation/@kind='line' and .//step/geo/primitive[@kind='progress'] and count(body/geometry/line/order/slot) &lt; 2">
      <svrl:failed-assert><svrl:text>line formation with progress primitives must declare body/geometry/line/order with at least 2 slots</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version='1.2' and meta/geometry/formation/@kind='line' and .//step/geo/primitive[@kind='progress'] and count(body/geometry/line/order/slot/@who) != count(distinct-values(body/geometry/line/order/slot/@who))">
      <svrl:failed-assert><svrl:text>line order slot list must not contain duplicate who values</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version='1.2' and meta/geometry/formation/@kind='line' and .//step/geo/primitive[@kind='progress'] and count(.//step/geo/primitive[@kind='progress' and not(@delta)]) &gt; 0">
      <svrl:failed-assert><svrl:text>every progress primitive must have @delta</svrl:text></svrl:failed-assert>
    </xsl:if>
    <xsl:if test="@version='1.2' and meta/geometry/formation/@kind='line' and .//step/geo/primitive[@kind='progress'] and meta/geometry/roles/role and body/geometry/line/order/slot/@who and not(every $w in body/geometry/line/order/slot/@who satisfies meta/geometry/roles/role[@id = $w])">
      <svrl:failed-assert><svrl:text>line/order/slot/@who must reference a declared role id</svrl:text></svrl:failed-assert>
    </xsl:if>

    <xsl:apply-templates select="body"/>
  </xsl:template>

  <xsl:template match="body">
    <!-- Ontology Batch 4B: relpos + swapPlaces attribute requirements (FDML v1.2 only). -->
    <xsl:for-each select=".//step/geo/primitive[@kind='relpos']">
      <xsl:if test="not(@a) or not(@b)"><svrl:failed-assert><svrl:text>relpos primitive must declare @a and @b</svrl:text></svrl:failed-assert></xsl:if>
      <xsl:if test="not(@relation)"><svrl:failed-assert><svrl:text>relpos primitive must declare @relation</svrl:text></svrl:failed-assert></xsl:if>
    </xsl:for-each>
    <xsl:for-each select=".//step/geo/primitive[@kind='swapPlaces']">
      <xsl:if test="not(@a) or not(@b)"><svrl:failed-assert><svrl:text>swapPlaces primitive must declare @a and @b</svrl:text></svrl:failed-assert></xsl:if>
    </xsl:for-each>

    <xsl:for-each select="figure">
      <xsl:if test="not(@id)"><svrl:failed-assert><svrl:text>figure must have @id</svrl:text></svrl:failed-assert></xsl:if>
      <xsl:if test="@id and not(matches(@id, '^f-[a-z0-9-]+$'))"><svrl:failed-assert><svrl:text>figure/@id must match pattern 'f-[a-z0-9-]+'</svrl:text></svrl:failed-assert></xsl:if>
      <xsl:if test="@id and count(//figure[@id=current()/@id]) &gt; 1"><svrl:failed-assert><svrl:text>figure/@id values must be unique across the document</svrl:text></svrl:failed-assert></xsl:if>
      <xsl:if test="not(step)"><svrl:failed-assert><svrl:text>figure must contain at least one step</svrl:text></svrl:failed-assert></xsl:if>
      <xsl:for-each select="step">
        <xsl:if test="not(@beats) or number(@beats) &lt; 1"><svrl:failed-assert><svrl:text>step/@beats must be ≥ 1</svrl:text></svrl:failed-assert></xsl:if>
        <xsl:if test="not(@who)"><svrl:failed-assert><svrl:text>step/@who is required</svrl:text></svrl:failed-assert></xsl:if>
        <xsl:if test="not(@startFoot)"><svrl:failed-assert><svrl:text>step/@startFoot is required</svrl:text></svrl:failed-assert></xsl:if>
      </xsl:for-each>
    </xsl:for-each>

    <xsl:for-each select="sequence/use">
      <xsl:variable name="t" select="@figure"/>
      <xsl:if test="count(//figure[@id=$t]) = 0"><svrl:failed-assert><svrl:text>sequence/use/@figure must reference an existing figure id</svrl:text></svrl:failed-assert></xsl:if>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="@*|node()"><xsl:apply-templates select="@*|node()"/></xsl:template>
</xsl:stylesheet>
