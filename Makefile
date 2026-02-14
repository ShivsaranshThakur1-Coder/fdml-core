.PHONY: html validate-valid validate-invalid json schematron check-schematron coverage ci clean

html:
	@set -e; TS=$$(date +%s); out=out/html; mkdir -p $$out; tmp=$$(mktemp); \
		find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do \
			base=$$(basename "$$f"); stem=$${base%.xml}; \
			echo "HTML  $$out/$$stem.html"; \
			xsltproc --stringparam cssVersion $$TS xslt/card.xsl "$$f" > "$$out/$$stem.html"; \
		done < $$tmp; rm -f $$tmp; \
		mkdir -p site; cp -f docs/style.css site/style.css; cp -f $$out/*.html site/; \
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

coverage:
	@python3 scripts/coverage_report.py

ci: check-schematron validate-valid validate-invalid html

clean:
	rm -rf out site

serve:
	cd site && python3 -m http.server 8000

report:
	cd docs/progress-report && latexmk -pdf -silent progress_2025-10-28_v2.tex
