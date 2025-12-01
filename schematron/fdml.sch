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

