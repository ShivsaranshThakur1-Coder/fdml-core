<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron">

  <!-- Basic presence checks (applies to all FDML versions) -->
  <pattern id="basic-rules">
    <rule context="fdml">
      <assert test="meta">fdml must contain meta</assert>
      <assert test="body">fdml must contain body</assert>
    </rule>
  </pattern>

  <!-- Richer meta rules for FDML v1.1 documents -->
  <pattern id="v11-meta-rules">
    <rule context="fdml[@version = '1.1']">
      <assert test="meta/origin/@country">
        v1.1 dances must specify an origin country
      </assert>
      <assert test="meta/type/@genre">
        v1.1 dances must specify a type/genre
      </assert>
      <assert test="meta/meter/@value">
        v1.1 dances must specify a meter value
      </assert>
    </rule>
  </pattern>

  <!-- Ensure v1.1 dances have both notes and setup sections -->
  <pattern id="v11-sections">
    <rule context="fdml[@version = '1.1']">
      <assert test="body/section[@type = 'notes']">
        v1.1 dances should include a section with type="notes"
      </assert>
      <assert test="body/section[@type = 'setup']">
        v1.1 dances should include a section with type="setup"
      </assert>
    </rule>
  </pattern>

  <!-- FDML v1.2 geometry: basic structural consistency checks.
       Note: deeper stateful invariants are validated by the Java GeometryValidator.
  -->
  <pattern id="v12-geometry-meta">
    <rule context="fdml[@version = '1.2']">
      <assert test="meta/geometry/formation/@kind">
        v1.2 dances must include meta/geometry/formation/@kind
      </assert>

      <!-- If any step contains geo primitives, roles should be declared so @who can be checked. -->
      <assert test="not(.//step/geo) or meta/geometry/roles/role">
        v1.2 dances that use step/geo should declare meta/geometry/roles/role
      </assert>

      <!-- Ontology Batch 1: meter rhythm pattern for 9/16. -->
      <assert test="not(contains(meta/meter/@value, '9/16')) or meta/meter/@rhythmPattern = '2+2+2+3'">
        v1.2 dances with meter 9/16 must specify meter/@rhythmPattern='2+2+2+3'
      </assert>

      <!-- Ontology Batch 2: hold kind should be a known value (XSD enforces; Schematron provides message). -->
      <assert test="not(meta/geometry/hold) or meta/geometry/hold/@kind = 'vPosition' or meta/geometry/hold/@kind = 'beltHold' or meta/geometry/hold/@kind = 'armenianHold' or meta/geometry/hold/@kind = 'palmToPalm' or meta/geometry/hold/@kind = 'none'">
        v1.2 meta/geometry/hold/@kind must be one of: vPosition|beltHold|armenianHold|palmToPalm|none
      </assert>

      <!-- Ontology Batch 2: releaseHold only allowed when declared hold kind is none. -->
      <assert test="not(meta/geometry/hold) or meta/geometry/hold/@kind = 'none' or count(.//step/geo/primitive[@kind = 'releaseHold']) = 0">
        v1.2 dances with hold/@kind != 'none' must not use primitive kind='releaseHold'
      </assert>
    </rule>
  </pattern>

  <pattern id="v12-geometry-step-primitives">
    <rule context="fdml[@version = '1.2']//step[geo]">
      <assert test="geo/primitive">
        step/geo must contain at least one primitive
      </assert>
      <assert test="count(geo/primitive[not(@kind)]) = 0">
        each geo/primitive must have @kind
      </assert>
    </rule>
  </pattern>

  <!-- Role reference checks for v1.2 (lightweight).
       We only check @who when roles are declared.
  -->
  <pattern id="v12-geometry-role-refs">
    <rule context="fdml[@version = '1.2'][meta/geometry/roles/role]//step">
      <let name="who" value="normalize-space(@who)"/>
      <assert test="$who = '' or count(/fdml/meta/geometry/roles/role[@id = $who]) &gt; 0">
        step/@who should reference a declared meta/geometry/roles/role/@id (for v1.2)
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][meta/geometry/roles/role]//geo/primitive[@who]">
      <let name="pwho" value="normalize-space(@who)"/>
      <assert test="count(/fdml/meta/geometry/roles/role[@id = $pwho]) &gt; 0">
        geo/primitive/@who must reference a declared meta/geometry/roles/role/@id (for v1.2)
      </assert>
    </rule>
  </pattern>

  <!-- Body geometry cross-reference checks (v1.2).
       XSD enforces presence of attributes; Schematron checks their referents if roles are declared.
  -->
  <pattern id="v12-body-geometry">
    <!-- Ontology Batch 4B: primitive structural requirements for stateful semantics. -->
    <rule context="fdml[@version = '1.2']//step/geo/primitive[@kind='relpos']">
      <assert test="@a and @b">
        relpos primitive must declare @a and @b
      </assert>
      <assert test="@relation">
        relpos primitive must declare @relation
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2']//step/geo/primitive[@kind='swapPlaces']">
      <assert test="@a and @b">
        swapPlaces primitive must declare @a and @b
      </assert>
    </rule>

    <!-- Ontology Batch 4C: any primitive with @dir must declare a disambiguating @frame. -->
    <rule context="fdml[@version = '1.2']//step/geo/primitive[@dir]">
      <assert test="@frame">
        geo/primitive with @dir must declare @frame
      </assert>
      <let name="d" value="normalize-space(@dir)"/>
      <assert test="not($d = 'clockwise' or $d = 'counterclockwise' or $d = 'inward' or $d = 'outward' or $d = 'center') or @frame = 'formation'">
        geo/primitive with formation-frame dir must use frame='formation'
      </assert>
      <assert test="not($d = 'forward' or $d = 'backward' or $d = 'left' or $d = 'right') or @frame = 'dancer'">
        geo/primitive with dancer-frame dir must use frame='dancer'
      </assert>
    </rule>

    <!-- Ontology Batch 4A: line progression requires explicit line order slots and progress deltas. -->
    <rule context="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'line'][.//step/geo/primitive[@kind='progress']]">
      <assert test="count(body/geometry/line/order/slot) &gt;= 2">
        line formation with progress primitives must declare body/geometry/line/order with at least 2 slots
      </assert>
      <assert test="count(body/geometry/line/order/slot/@who) = count(distinct-values(body/geometry/line/order/slot/@who))">
        line order slot list must not contain duplicate who values
      </assert>
      <assert test="count(.//step/geo/primitive[@kind='progress' and not(@delta)]) = 0">
        every progress primitive must have @delta
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'line'][.//step/geo/primitive[@kind='progress']][meta/geometry/roles/role]//body/geometry/line/order/slot[@who]">
      <assert test="count(/fdml/meta/geometry/roles/role[@id = current()/@who]) &gt; 0">
        line/order/slot/@who must reference a declared role id
      </assert>
    </rule>

    <!-- Ontology Batch 1: twoLinesFacing must declare which lines face each other. -->
    <rule context="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'twoLinesFacing']">
      <assert test="body/geometry/twoLines/facing">
        twoLinesFacing formation must declare body/geometry/twoLines/facing
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'twoLinesFacing'][meta/geometry/roles/role]//body/geometry/twoLines/facing">
      <assert test="count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@a)]) > 0">
        twoLines/facing/@a must reference a declared role id
      </assert>
      <assert test="count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@b)]) > 0">
        twoLines/facing/@b must reference a declared role id
      </assert>
    </rule>

    <!-- Ontology Batch 4B: couple formation with womanSide needs explicit relative-position evidence. -->
    <rule context="fdml[@version = '1.2'][meta/geometry/formation/@kind = 'couple'][meta/geometry/formation/@womanSide]">
      <assert test="meta/geometry/roles/role[@id = 'man'] and meta/geometry/roles/role[@id = 'woman']">
        couple formation with womanSide must declare roles 'man' and 'woman'
      </assert>
      <assert test="body/geometry/couples/pair[(@a='man' and @b='woman') or (@a='woman' and @b='man')]">
        couple formation with womanSide must include body/geometry/couples/pair linking man and woman
      </assert>

      <!-- Evidence of partner-side semantics: at least one relpos assertion consistent with womanSide. -->
      <let name="ws" value="normalize-space(meta/geometry/formation/@womanSide)"/>
      <assert test="
        ($ws = 'left' and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='leftOf') or (@a='man' and @b='woman' and @relation='rightOf')]))
        or
        ($ws = 'right' and (.//step/geo/primitive[@kind='relpos'][(@a='woman' and @b='man' and @relation='rightOf') or (@a='man' and @b='woman' and @relation='leftOf')]))
      ">
        couple formation with womanSide must include at least one relpos primitive asserting the correct side between man and woman
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2']/body/geometry/circle/order">
      <assert test="@role">
        body/geometry/circle/order must have @role
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/circle/order[@role]">
      <assert test="count(/fdml/meta/geometry/roles/role[@id = @role]) &gt; 0">
        circle/order/@role must reference a declared role id
      </assert>
    </rule>

    <!-- FDML v1.2: explicit circle order slots (only enforced when slots are present). -->
    <rule context="fdml[@version = '1.2']/body/geometry/circle/order[slot]">
      <assert test="count(slot) &gt;= 4">
        circle/order with explicit slots must include at least 4 slot entries
      </assert>
      <assert test="count(slot/@who) = count(distinct-values(slot/@who))">
        circle/order slot list must not contain duplicate who values
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/circle/order/slot[@who]">
      <assert test="count(/fdml/meta/geometry/roles/role[@id = current()/@who]) &gt; 0">
        circle/order/slot/@who must reference a declared role id
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/line[@role]">
      <assert test="count(/fdml/meta/geometry/roles/role[@id = current()/@role]) &gt; 0">
        twoLines/line/@role must reference a declared role id
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/facing">
      <assert test="count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@a)]) > 0">
        twoLines/facing/@a must reference a declared role id
      </assert>
      <assert test="count(/fdml/body/geometry/twoLines/line[@id = normalize-space(/fdml/body/geometry/twoLines/facing/@b)]) > 0">
        twoLines/facing/@b must reference a declared role id
      </assert>
    </rule>
  </pattern>

  <!-- Every figure must contain at least one step -->
  <pattern id="figure-structure">
    <rule context="figure">
      <assert test="step or measureRange/step">
        figure must contain at least one step
      </assert>
    </rule>
  </pattern>

  <!-- Sequence/use must reference existing figure ids -->
  <pattern id="sequence-refs">
    <rule context="sequence/use[@figure]">
      <let name="targetFigure" value="normalize-space(@figure)"/>
      <assert test="count(/fdml/body//figure[@id = $targetFigure]) &gt; 0">
        sequence/use/@figure must reference an existing figure id
      </assert>
    </rule>
  </pattern>

  <!-- Each part should contain at least one figure -->
  <pattern id="part-structure">
    <rule context="part">
      <assert test="figure">
        part must contain at least one figure
      </assert>
    </rule>
  </pattern>

  <!-- Consistency between type/genre and formation text in v1.1 -->
  <pattern id="type-formation-consistency">
    <rule context="fdml[@version = '1.1']">
      <!-- normalize formation text to lowercase for case-insensitive contains() -->
      <let name="formText" value="translate(meta/formation/@text,
                                            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                                            'abcdefghijklmnopqrstuvwxyz')"/>

      <assert test="not(meta/type/@genre = 'circle') or contains($formText, 'circle')">
        If type/@genre is "circle", formation text should mention "circle".
      </assert>
      <assert test="not(meta/type/@genre = 'line') or contains($formText, 'line')">
        If type/@genre is "line", formation text should mention "line".
      </assert>
      <assert test="not(meta/type/@genre = 'couple') or contains($formText, 'couple')">
        If type/@genre is "couple", formation text should mention "couple".
      </assert>
    </rule>
  </pattern>

</schema>
