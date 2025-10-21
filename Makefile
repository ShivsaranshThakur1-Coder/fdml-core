.PHONY: html validate-valid validate-invalid json ci clean

html:
	@set -e; TS=$$(date +%s); out=out/html; mkdir -p $$out; tmp=$$(mktemp); \
		find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do \
			base=$$(basename "$$f"); stem=$${base%.xml}; \
			echo "HTML  $$out/$$stem.html"; \
			xsltproc --stringparam cssVersion $$TS xslt/card.xsl "$$f" > "$$out/$$stem.html"; \
		done < $$tmp; rm -f $$tmp; \
		mkdir -p site; cp -f docs/style.css site/style.css; cp -f $$out/*.html site/; \
		scripts/build_index.sh $$TS

validate-valid:
	@set -e; tmp=$$(mktemp); find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do echo "VALID  $$f"; fdml validate "$$f"; done; rm -f $$tmp

validate-invalid:
	@set -e; tmp=$$(mktemp); find corpus/invalid -type f -name '*.xml' | sort > $$tmp; failures=0; \
		while IFS= read -r f; do echo "INVALID $$f"; if fdml validate "$$f"; then echo "EXPECTED FAILURE but got success: $$f"; failures=$$((failures+1)); fi; done; \
		rm -f $$tmp; test $$failures -eq 0

json:
	@set -e; out=out/json; mkdir -p $$out; tmp=$$(mktemp); \
		find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do base=$$(basename "$$f"); stem=$${base%.xml}; \
			echo "JSON  $$out/$$stem.json"; fdml validate "$$f" --json --json-out "$$out/$$stem.json"; \
		done < $$tmp; rm -f $$tmp

ci: validate-valid validate-invalid html

clean:
	rm -rf out site
