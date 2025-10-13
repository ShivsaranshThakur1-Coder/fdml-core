<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron">
  <pattern id="basic-rules">
    <rule context="fdml">
      <assert test="meta">fdml must contain meta</assert>
      <assert test="body">fdml must contain body</assert>
    </rule>
  </pattern>
</schema>
