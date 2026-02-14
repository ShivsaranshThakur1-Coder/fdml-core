<?xml version="1.0" encoding="UTF-8"?>
<xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
               xmlns:sch="http://purl.oclc.org/dsdl/schematron"
               xmlns:schxslt="https://doi.org/10.5281/zenodo.1495494"
               xmlns:schxslt-api="https://doi.org/10.5281/zenodo.1495494#api"
               version="1.0">
   <rdf:Description xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                    xmlns:dc="http://purl.org/dc/elements/1.1/"
                    xmlns:dct="http://purl.org/dc/terms/"
                    xmlns:skos="http://www.w3.org/2004/02/skos/core#">
      <dct:creator>
         <dct:Agent>
            <skos:prefLabel>SchXslt/1.10.1 (XSLT 1.0)</skos:prefLabel>
         </dct:Agent>
      </dct:creator>
   </rdf:Description>
   <xsl:output indent="yes"/>
   <xsl:param name="schxslt.validate.initial-document-uri"/>
   <xsl:template name="schxslt.validate.main">
      <xsl:apply-templates select="document($schxslt.validate.initial-document-uri)"/>
   </xsl:template>
   <xsl:template match="/">
      <xsl:param name="schxslt.validate.recursive-call" select="false()"/>
      <xsl:choose>
         <xsl:when test="not($schxslt.validate.recursive-call) and (normalize-space($schxslt.validate.initial-document-uri) != '')">
            <xsl:apply-templates select="document($schxslt.validate.initial-document-uri)">
               <xsl:with-param name="schxslt.validate.recursive-call" select="true()"/>
            </xsl:apply-templates>
         </xsl:when>
         <xsl:otherwise>
            <xsl:variable name="schxslt:report">
               <svrl:metadata xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                              xmlns:dct="http://purl.org/dc/terms/">
                  <dct:source>
                     <rdf:Description xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                                      xmlns:dc="http://purl.org/dc/elements/1.1/"
                                      xmlns:skos="http://www.w3.org/2004/02/skos/core#">
                        <dct:creator>
                           <dct:Agent>
                              <skos:prefLabel>SchXslt/1.10.1 (XSLT 1.0)</skos:prefLabel>
                           </dct:Agent>
                        </dct:creator>
                     </rdf:Description>
                  </dct:source>
               </svrl:metadata>
               <xsl:call-template name="w96aab3"/>
               <xsl:call-template name="w96aab7"/>
               <xsl:call-template name="w96aac11"/>
               <xsl:call-template name="w96aac15"/>
               <xsl:call-template name="w96aac17"/>
               <xsl:call-template name="w96aac21"/>
               <xsl:call-template name="w96aac25"/>
               <xsl:call-template name="w96aac29"/>
               <xsl:call-template name="w96aac33"/>
               <xsl:call-template name="w96aac37"/>
               <xsl:call-template name="w96aac41"/>
            </xsl:variable>
            <svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
               <xsl:copy-of select="$schxslt:report"/>
            </svrl:schematron-output>
         </xsl:otherwise>
      </xsl:choose>
   </xsl:template>
   <xsl:template name="w96aab3">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="basic-rules"
                           name="basic-rules"/>
      <xsl:apply-templates mode="w96aab3" select="/"/>
   </xsl:template>
   <xsl:template match="fdml" mode="w96aab3" priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(meta)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">meta</xsl:attribute>
            <svrl:text>fdml must contain meta</svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(body)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">body</xsl:attribute>
            <svrl:text>fdml must contain body</svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aab3" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aab3" priority="-10">
      <xsl:apply-templates mode="w96aab3" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aab3" priority="-10"/>
   <xsl:template name="w96aab7">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="v11-meta-rules"
                           name="v11-meta-rules"/>
      <xsl:apply-templates mode="w96aab7" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.1']" mode="w96aab7" priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.1']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(meta/origin/@country)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">meta/origin/@country</xsl:attribute>
            <svrl:text>
        v1.1 dances must specify an origin country
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(meta/type/@genre)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">meta/type/@genre</xsl:attribute>
            <svrl:text>
        v1.1 dances must specify a type/genre
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(meta/meter/@value)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">meta/meter/@value</xsl:attribute>
            <svrl:text>
        v1.1 dances must specify a meter value
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aab7" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aab7" priority="-10">
      <xsl:apply-templates mode="w96aab7" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aab7" priority="-10"/>
   <xsl:template name="w96aac11">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="v11-sections"
                           name="v11-sections"/>
      <xsl:apply-templates mode="w96aac11" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.1']" mode="w96aac11" priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.1']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(body/section[@type = 'notes'])">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">body/section[@type = 'notes']</xsl:attribute>
            <svrl:text>
        v1.1 dances should include a section with type="notes"
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(body/section[@type = 'setup'])">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">body/section[@type = 'setup']</xsl:attribute>
            <svrl:text>
        v1.1 dances should include a section with type="setup"
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac11" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac11" priority="-10">
      <xsl:apply-templates mode="w96aac11" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac11" priority="-10"/>
   <xsl:template name="w96aac15">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="v12-geometry-meta"
                           name="v12-geometry-meta"/>
      <xsl:apply-templates mode="w96aac15" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']" mode="w96aac15" priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(meta/geometry/formation/@kind)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">meta/geometry/formation/@kind</xsl:attribute>
            <svrl:text>
        v1.2 dances must include meta/geometry/formation/@kind
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not(.//step/geo) or meta/geometry/roles/role)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(.//step/geo) or meta/geometry/roles/role</xsl:attribute>
            <svrl:text>
        v1.2 dances that use step/geo should declare meta/geometry/roles/role
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not(contains(meta/meter/@value, '9/16')) or meta/meter/@rhythmPattern = '2+2+2+3')">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(contains(meta/meter/@value, '9/16')) or meta/meter/@rhythmPattern = '2+2+2+3'</xsl:attribute>
            <svrl:text>
        v1.2 dances with meter 9/16 must specify meter/@rhythmPattern='2+2+2+3'
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not(meta/geometry/hold) or meta/geometry/hold/@kind = 'vPosition' or meta/geometry/hold/@kind = 'beltHold' or meta/geometry/hold/@kind = 'armenianHold' or meta/geometry/hold/@kind = 'palmToPalm' or meta/geometry/hold/@kind = 'none')">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(meta/geometry/hold) or meta/geometry/hold/@kind = 'vPosition' or meta/geometry/hold/@kind = 'beltHold' or meta/geometry/hold/@kind = 'armenianHold' or meta/geometry/hold/@kind = 'palmToPalm' or meta/geometry/hold/@kind = 'none'</xsl:attribute>
            <svrl:text>
        v1.2 meta/geometry/hold/@kind must be one of: vPosition|beltHold|armenianHold|palmToPalm|none
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not(meta/geometry/hold) or meta/geometry/hold/@kind = 'none' or count(.//step/geo/primitive[@kind = 'releaseHold']) = 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(meta/geometry/hold) or meta/geometry/hold/@kind = 'none' or count(.//step/geo/primitive[@kind = 'releaseHold']) = 0</xsl:attribute>
            <svrl:text>
        v1.2 dances with hold/@kind != 'none' must not use primitive kind='releaseHold'
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac15" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac15" priority="-10">
      <xsl:apply-templates mode="w96aac15" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac15" priority="-10"/>
   <xsl:template name="w96aac17">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="v12-geometry-step-primitives"
                           name="v12-geometry-step-primitives"/>
      <xsl:apply-templates mode="w96aac17" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']//step[geo]"
                 mode="w96aac17"
                 priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']//step[geo]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(geo/primitive)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">geo/primitive</xsl:attribute>
            <svrl:text>
        step/geo must contain at least one primitive
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(count(geo/primitive[not(@kind)]) = 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(geo/primitive[not(@kind)]) = 0</xsl:attribute>
            <svrl:text>
        each geo/primitive must have @kind
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac17" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac17" priority="-10">
      <xsl:apply-templates mode="w96aac17" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac17" priority="-10"/>
   <xsl:template name="w96aac21">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="v12-geometry-role-refs"
                           name="v12-geometry-role-refs"/>
      <xsl:apply-templates mode="w96aac21" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/roles/role]//step"
                 mode="w96aac21"
                 priority="1">
      <xsl:variable name="who" select="normalize-space(@who)"/>
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/roles/role]//step</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not($who = '' or count(/fdml/meta/geometry/roles/role[@id = $who]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">$who = '' or count(/fdml/meta/geometry/roles/role[@id = $who]) &gt; 0</xsl:attribute>
            <svrl:text>
        step/@who should reference a declared meta/geometry/roles/role/@id (for v1.2)
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac21" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/roles/role]//geo/primitive[@who]"
                 mode="w96aac21"
                 priority="0">
      <xsl:variable name="pwho" select="normalize-space(@who)"/>
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/roles/role]//geo/primitive[@who]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/meta/geometry/roles/role[@id = $pwho]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/meta/geometry/roles/role[@id = $pwho]) &gt; 0</xsl:attribute>
            <svrl:text>
        geo/primitive/@who must reference a declared meta/geometry/roles/role/@id (for v1.2)
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac21" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac21" priority="-10">
      <xsl:apply-templates mode="w96aac21" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac21" priority="-10"/>
   <xsl:template name="w96aac25">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="v12-body-geometry"
                           name="v12-body-geometry"/>
      <xsl:apply-templates mode="w96aac25" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']//step/geo/primitive[@kind='relpos']"
                 mode="w96aac25"
                 priority="13">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']//step/geo/primitive[@kind='relpos']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(@a and @b)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">@a and @b</xsl:attribute>
            <svrl:text>
        relpos primitive must declare @a and @b
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(@relation)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">@relation</xsl:attribute>
            <svrl:text>
        relpos primitive must declare @relation
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']//step/geo/primitive[@kind='swapPlaces']"
                 mode="w96aac25"
                 priority="12">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']//step/geo/primitive[@kind='swapPlaces']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(@a and @b)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">@a and @b</xsl:attribute>
            <svrl:text>
        swapPlaces primitive must declare @a and @b
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']//step/geo/primitive[@dir]"
                 mode="w96aac25"
                 priority="11">
      <xsl:variable name="d" select="normalize-space(@dir)"/>
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']//step/geo/primitive[@dir]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(@frame)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">@frame</xsl:attribute>
            <svrl:text>
        geo/primitive with @dir must declare @frame
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not($d = 'clockwise' or $d = 'counterclockwise' or $d = 'inward' or $d = 'outward' or $d = 'center') or @frame = 'formation')">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not($d = 'clockwise' or $d = 'counterclockwise' or $d = 'inward' or $d = 'outward' or $d = 'center') or @frame = 'formation'</xsl:attribute>
            <svrl:text>
        geo/primitive with formation-frame dir must use frame='formation'
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not($d = 'forward' or $d = 'backward' or $d = 'left' or $d = 'right') or @frame = 'dancer')">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not($d = 'forward' or $d = 'backward' or $d = 'left' or $d = 'right') or @frame = 'dancer'</xsl:attribute>
            <svrl:text>
        geo/primitive with dancer-frame dir must use frame='dancer'
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'line'][.//step/geo/primitive[@kind='progress']]"
                 mode="w96aac25"
                 priority="10">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/formation/@kind = 'line'][.//step/geo/primitive[@kind='progress']]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(body/geometry/line/order/slot) &gt;= 2)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(body/geometry/line/order/slot) &gt;= 2</xsl:attribute>
            <svrl:text>
        line formation with progress primitives must declare body/geometry/line/order with at least 2 slots
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(count(body/geometry/line/order/slot/@who) = count(distinct-values(body/geometry/line/order/slot/@who)))">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(body/geometry/line/order/slot/@who) = count(distinct-values(body/geometry/line/order/slot/@who))</xsl:attribute>
            <svrl:text>
        line order slot list must not contain duplicate who values
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(count(.//step/geo/primitive[@kind='progress' and not(@delta)]) = 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(.//step/geo/primitive[@kind='progress' and not(@delta)]) = 0</xsl:attribute>
            <svrl:text>
        every progress primitive must have @delta
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'line'][.//step/geo/primitive[@kind='progress']][meta/geometry/roles/role]//body/geometry/line/order/slot[@who]"
                 mode="w96aac25"
                 priority="9">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/formation/@kind = 'line'][.//step/geo/primitive[@kind='progress']][meta/geometry/roles/role]//body/geometry/line/order/slot[@who]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/meta/geometry/roles/role[@id = current()/@who]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/meta/geometry/roles/role[@id = current()/@who]) &gt; 0</xsl:attribute>
            <svrl:text>
        line/order/slot/@who must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'twoLinesFacing']"
                 mode="w96aac25"
                 priority="8">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/formation/@kind = 'twoLinesFacing']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(body/geometry/twoLines/facing)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">body/geometry/twoLines/facing</xsl:attribute>
            <svrl:text>
        twoLinesFacing formation must declare body/geometry/twoLines/facing
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'twoLinesFacing'][meta/geometry/roles/role]//body/geometry/twoLines/facing"
                 mode="w96aac25"
                 priority="7">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/formation/@kind = 'twoLinesFacing'][meta/geometry/roles/role]//body/geometry/twoLines/facing</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@a)]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@a)]) &gt; 0</xsl:attribute>
            <svrl:text>
        twoLines/facing/@a must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@b)]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@b)]) &gt; 0</xsl:attribute>
            <svrl:text>
        twoLines/facing/@b must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'couple'][meta/geometry/formation/@womanSide]"
                 mode="w96aac25"
                 priority="6">
      <xsl:variable name="ws" select="normalize-space(meta/geometry/formation/@womanSide)"/>
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][meta/geometry/formation/@kind = 'couple'][meta/geometry/formation/@womanSide]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(meta/geometry/roles/role[@id = 'man'] and meta/geometry/roles/role[@id = 'woman'])">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">meta/geometry/roles/role[@id = 'man'] and meta/geometry/roles/role[@id = 'woman']</xsl:attribute>
            <svrl:text>
        couple formation with womanSide must declare roles 'man' and 'woman'
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(body/geometry/couples/pair[(@a='man' and @b='woman') or (@a='woman' and @b='man')])">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">body/geometry/couples/pair[(@a='man' and @b='woman') or (@a='woman' and @b='man')]</xsl:attribute>
            <svrl:text>
        couple formation with womanSide must include body/geometry/couples/pair linking man and woman
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(         ($ws = 'left' and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='leftOf') or (@a='man' and @b='woman' and @relation='rightOf')]))         or         ($ws = 'right' and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='rightOf') or (@a='man' and @b='woman' and @relation='leftOf')]))       )">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">         ($ws = 'left' and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='leftOf') or (@a='man' and @b='woman' and @relation='rightOf')]))         or         ($ws = 'right' and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='rightOf') or (@a='man' and @b='woman' and @relation='leftOf')]))       </xsl:attribute>
            <svrl:text>
        couple formation with womanSide must include at least one relpos primitive asserting the correct side between man and woman
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']/body/geometry/circle/order"
                 mode="w96aac25"
                 priority="5">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']/body/geometry/circle/order</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(@role)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">@role</xsl:attribute>
            <svrl:text>
        body/geometry/circle/order must have @role
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/circle/order[@role]"
                 mode="w96aac25"
                 priority="4">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/circle/order[@role]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/meta/geometry/roles/role[@id = @role]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/meta/geometry/roles/role[@id = @role]) &gt; 0</xsl:attribute>
            <svrl:text>
        circle/order/@role must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2']/body/geometry/circle/order[slot]"
                 mode="w96aac25"
                 priority="3">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2']/body/geometry/circle/order[slot]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(slot) &gt;= 4)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(slot) &gt;= 4</xsl:attribute>
            <svrl:text>
        circle/order with explicit slots must include at least 4 slot entries
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(count(slot/@who) = count(distinct-values(slot/@who)))">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(slot/@who) = count(distinct-values(slot/@who))</xsl:attribute>
            <svrl:text>
        circle/order slot list must not contain duplicate who values
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/circle/order/slot[@who]"
                 mode="w96aac25"
                 priority="2">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/circle/order/slot[@who]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/meta/geometry/roles/role[@id = @who]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/meta/geometry/roles/role[@id = @who]) &gt; 0</xsl:attribute>
            <svrl:text>
        circle/order/slot/@who must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/line[@role]"
                 mode="w96aac25"
                 priority="1">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/line[@role]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/meta/geometry/roles/role[@id = @role]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/meta/geometry/roles/role[@id = @role]) &gt; 0</xsl:attribute>
            <svrl:text>
        twoLines/line/@role must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/facing"
                 mode="w96aac25"
                 priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/facing</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@a)]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@a)]) &gt; 0</xsl:attribute>
            <svrl:text>
        twoLines/facing/@a must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@b)]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@b)]) &gt; 0</xsl:attribute>
            <svrl:text>
        twoLines/facing/@b must reference a declared role id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac25" priority="-10">
      <xsl:apply-templates mode="w96aac25" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac25" priority="-10"/>
   <xsl:template name="w96aac29">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="figure-structure"
                           name="figure-structure"/>
      <xsl:apply-templates mode="w96aac29" select="/"/>
   </xsl:template>
   <xsl:template match="figure" mode="w96aac29" priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">figure</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(step or measureRange/step)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">step or measureRange/step</xsl:attribute>
            <svrl:text>
        figure must contain at least one step
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac29" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac29" priority="-10">
      <xsl:apply-templates mode="w96aac29" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac29" priority="-10"/>
   <xsl:template name="w96aac33">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="sequence-refs"
                           name="sequence-refs"/>
      <xsl:apply-templates mode="w96aac33" select="/"/>
   </xsl:template>
   <xsl:template match="sequence/use[@figure]" mode="w96aac33" priority="0">
      <xsl:variable name="targetFigure" select="normalize-space(@figure)"/>
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">sequence/use[@figure]</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(count(/fdml/body//figure[@id = $targetFigure]) &gt; 0)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">count(/fdml/body//figure[@id = $targetFigure]) &gt; 0</xsl:attribute>
            <svrl:text>
        sequence/use/@figure must reference an existing figure id
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac33" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac33" priority="-10">
      <xsl:apply-templates mode="w96aac33" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac33" priority="-10"/>
   <xsl:template name="w96aac37">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="part-structure"
                           name="part-structure"/>
      <xsl:apply-templates mode="w96aac37" select="/"/>
   </xsl:template>
   <xsl:template match="part" mode="w96aac37" priority="0">
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">part</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(figure)">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">figure</xsl:attribute>
            <svrl:text>
        part must contain at least one figure
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac37" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac37" priority="-10">
      <xsl:apply-templates mode="w96aac37" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac37" priority="-10"/>
   <xsl:template name="w96aac41">
      <svrl:active-pattern xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                           id="type-formation-consistency"
                           name="type-formation-consistency"/>
      <xsl:apply-templates mode="w96aac41" select="/"/>
   </xsl:template>
   <xsl:template match="fdml[@version = '1.1']" mode="w96aac41" priority="0">
      <xsl:variable name="formText"
                    select="translate(meta/formation/@text,                                             'ABCDEFGHIJKLMNOPQRSTUVWXYZ',                                             'abcdefghijklmnopqrstuvwxyz')"/>
      <svrl:fired-rule xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
         <xsl:attribute name="context">fdml[@version = '1.1']</xsl:attribute>
      </svrl:fired-rule>
      <xsl:if test="not(not(meta/type/@genre = 'circle') or contains($formText, 'circle'))">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(meta/type/@genre = 'circle') or contains($formText, 'circle')</xsl:attribute>
            <svrl:text>
        If type/@genre is "circle", formation text should mention "circle".
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not(meta/type/@genre = 'line') or contains($formText, 'line'))">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(meta/type/@genre = 'line') or contains($formText, 'line')</xsl:attribute>
            <svrl:text>
        If type/@genre is "line", formation text should mention "line".
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:if test="not(not(meta/type/@genre = 'couple') or contains($formText, 'couple'))">
         <xsl:variable xmlns:svrl="http://purl.oclc.org/dsdl/svrl" name="location">
            <xsl:call-template name="schxslt:location">
               <xsl:with-param name="node" select="."/>
            </xsl:call-template>
         </xsl:variable>
         <svrl:failed-assert xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                             location="{normalize-space($location)}">
            <xsl:attribute name="test">not(meta/type/@genre = 'couple') or contains($formText, 'couple')</xsl:attribute>
            <svrl:text>
        If type/@genre is "couple", formation text should mention "couple".
      </svrl:text>
         </svrl:failed-assert>
      </xsl:if>
      <xsl:apply-templates mode="w96aac41" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="*" mode="w96aac41" priority="-10">
      <xsl:apply-templates mode="w96aac41" select="node() | @*"/>
   </xsl:template>
   <xsl:template match="@* | text()" mode="w96aac41" priority="-10"/>
   <xsl:template xmlns="http://www.w3.org/1999/XSL/TransformAlias"
                 xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
                 name="schxslt:location">
      <xsl:param name="node"/>
      <xsl:variable name="path">
         <xsl:for-each select="$node/ancestor::*">
            <xsl:variable name="position">
               <xsl:number level="single"/>
            </xsl:variable>
            <xsl:text>/</xsl:text>
            <xsl:value-of select="concat('Q{', namespace-uri(.), '}', local-name(.), '[', $position, ']')"/>
         </xsl:for-each>
         <xsl:text>/</xsl:text>
         <xsl:variable name="position">
            <xsl:number level="single"/>
         </xsl:variable>
         <xsl:choose>
            <xsl:when test="$node/self::*">
               <xsl:value-of select="concat('Q{', namespace-uri($node), '}', local-name($node), '[', $position, ']')"/>
            </xsl:when>
            <xsl:when test="count($node/../@*) = count($node|$node/../@*)">
               <xsl:value-of select="concat('@Q{', namespace-uri($node), '}', local-name($node))"/>
            </xsl:when>
            <xsl:when test="$node/self::processing-instruction()">
               <xsl:value-of select="concat('processing-instruction(&#34;', name(.), '&#34;)', '[', $position, ']')"/>
            </xsl:when>
            <xsl:when test="$node/self::comment()">
               <xsl:value-of select="concat('comment()', '[', $position, ']')"/>
            </xsl:when>
            <xsl:when test="$node/self::text()">
               <xsl:value-of select="concat('text()', '[', $position, ']')"/>
            </xsl:when>
         </xsl:choose>
      </xsl:variable>
      <xsl:value-of select="$path"/>
   </xsl:template>
</xsl:transform>
