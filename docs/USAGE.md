# FDML — Usage

## CLI
~~~bash
./bin/fdml validate <file-or-dir> [--json]
./bin/fdml validate-sch <file-or-dir> [--json]
./bin/fdml validate-all <file-or-dir> [--json]
./bin/fdml render <fdml-file> [--out out.html]
~~~

### Exit codes
- **0** = OK
- **2** = Validation errors (XSD or Schematron)
- **3** = Transform/render error
- **4** = I/O / usage error

### Examples
~~~bash
./bin/fdml validate corpus/valid
./bin/fdml validate-sch corpus/valid --json
./bin/fdml validate-all corpus/valid --json
./bin/fdml render corpus/valid/example-01.fdml.xml --out out/example-01.html
~~~
