.PHONY: html validate-valid validate-invalid json schematron check-schematron export-json-check ingest-check coverage site-check ci clean

html:
	@set -e; TS=$$(date +%s); out=out/html; mkdir -p $$out; tmp=$$(mktemp); \
		find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do \
			base=$$(basename "$$f"); stem=$${base%.xml}; \
			echo "HTML  $$out/$$stem.html"; \
			xsltproc --stringparam cssVersion $$TS xslt/card.xsl "$$f" > "$$out/$$stem.html"; \
		done < $$tmp; rm -f $$tmp; \
		mkdir -p site; cp -f docs/style.css site/style.css; find site -maxdepth 1 -type f -name '*.fdml.html' -delete; \
	scripts/build_index.sh $$TS \
	bin/fdml index corpus/valid --out site/index.json; \

validate-valid:
	@set -e; tmp=$$(mktemp); find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do echo "VALID  $$f"; ./bin/fdml validate "$$f"; done < $$tmp; rm -f $$tmp

validate-invalid:
	@set -e; tmp=$$(mktemp); find corpus/invalid -type f -name '*.xml' | sort > $$tmp; failures=0; \
		while IFS= read -r f; do echo "INVALID $$f"; if ./bin/fdml validate "$$f"; then echo "EXPECTED FAILURE but got success: $$f"; failures=$$((failures+1)); fi; done < $$tmp; \
		rm -f $$tmp; test $$failures -eq 0

json:
	@set -e; out=out/json; mkdir -p $$out; tmp=$$(mktemp); \
		find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do base=$$(basename "$$f"); stem=$${base%.xml}; \
			echo "JSON  $$out/$$stem.json"; ./bin/fdml validate "$$f" --json --json-out "$$out/$$stem.json"; \
		done < $$tmp; rm -f $$tmp

schematron:
	@./scripts/compile_schematron.sh

check-schematron:
	@set -e; tmp=$$(mktemp); \
	./scripts/compile_schematron.sh schematron/fdml.sch "$$tmp" > /dev/null; \
	if ! cmp -s "$$tmp" schematron/fdml-compiled.xsl; then \
		echo "Schematron compiled output is stale. Run: make schematron"; \
		diff -u schematron/fdml-compiled.xsl "$$tmp" || true; \
		rm -f "$$tmp"; \
		exit 1; \
	fi; \
	rm -f "$$tmp"; \
	echo "Schematron compiled output is up to date."

export-json-check:
	@set -e; mkdir -p site; \
	bin/fdml export-json corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml --out site/export-json-sample.json > /dev/null; \
	python3 scripts/validate_json_schema.py schema/export-json.schema.json site/export-json-sample.json

ingest-check:
	@set -e; mkdir -p out; \
	bin/fdml ingest --source analysis/gold/ingest/source_minimal.txt --out out/ingest-minimal.fdml.xml --title "Ingest Minimal" --meter 4/4 --tempo 112 --profile v1-basic > /dev/null; \
	diff -u corpus/valid_ingest/ingest-minimal.fdml.xml out/ingest-minimal.fdml.xml; \
	bin/fdml doctor out/ingest-minimal.fdml.xml --strict > /dev/null

coverage:
	@python3 scripts/coverage_report.py

site-check:
	@$(MAKE) html
	@python3 scripts/site_smoke.py

ci: check-schematron validate-valid validate-invalid export-json-check ingest-check site-check

clean:
	rm -rf out site

serve:
	cd site && python3 -m http.server 8000

report:
	cd docs/progress-report && latexmk -pdf -silent progress_2025-10-28_v2.tex
