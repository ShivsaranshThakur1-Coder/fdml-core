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
      <assert test="count(/fdml/meta/geometry/roles/role[@id = @who]) &gt; 0">
        circle/order/slot/@who must reference a declared role id
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/line[@role]">
      <assert test="count(/fdml/meta/geometry/roles/role[@id = @role]) &gt; 0">
        twoLines/line/@role must reference a declared role id
      </assert>
    </rule>

    <rule context="fdml[@version = '1.2'][/fdml/meta/geometry/roles/role]//body/geometry/twoLines/facing">
      <assert test="count(/fdml/meta/geometry/roles/role[@id = @a]) &gt; 0">
        twoLines/facing/@a must reference a declared role id
      </assert>
      <assert test="count(/fdml/meta/geometry/roles/role[@id = @b]) &gt; 0">
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
      <assert test="count(/fdml/body//figure[@id = @figure]) &gt; 0">
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
