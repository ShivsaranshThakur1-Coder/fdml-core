SHELL := /bin/bash

.PHONY: ci validate-valid validate-invalid

ci: validate-valid validate-invalid

validate-valid:
	@set -e; tmp=$$(mktemp); find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
	while IFS= read -r f; do \
		echo "VALID  $$f"; \
		fdml validate "$$f"; \
	done < $$tmp; rm -f $$tmp

validate-invalid:
	@set -e; tmp=$$(mktemp); find corpus/invalid -type f -name '*.xml' | sort > $$tmp; \
	failures=0; \
	while IFS= read -r f; do \
		echo "INVALID $$f"; \
		if fdml validate "$$f"; then \
			echo "EXPECTED FAILURE but got success: $$f"; \
			failures=$$((failures+1)); \
		fi; \
	done < $$tmp; rm -f $$tmp; test $$failures -eq 0
