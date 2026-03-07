.PHONY: html validate-valid validate-invalid json schematron check-schematron export-json-check ingest-check provenance-check enrichment-report-check ingest-batch-check ingest-promote-check conversion-batch-check full-description-coverage-check full-description-quality-check m8-geometry-baseline-check m8-geometry-uplift-check m8-geometry-governance-check m9-geometry-full-corpus-check m9-full-description-uplift-check m10-discovery-run m10-discovery-governance-check m11-contract-promotion-check m11-validator-unified-check m11-pipeline-governance-check m12-semantic-depth-check m13-parameter-registry-check m13-validator-expansion-check m13-pipeline-governance-check m14-contract-uplift-check m14-context-specificity-check m14-validator-burndown-check m15-discovery-run m15-validator-expansion-check m15-pipeline-governance-check m16-contract-promotion-check m16-validator-expansion-check m16-pipeline-governance-check m17-descriptor-registry-check m17-validator-expansion-check m17-pipeline-governance-check m18-realism-uplift-check m18-descriptor-uplift-check m18-pipeline-governance-check m19-corpus-expansion-baseline-check m19-descriptor-validator-expansion-check m19-pipeline-governance-check m20-corpus-expansion-check m20-descriptor-validator-expansion-check m20-pipeline-governance-check m21-descriptor-completion-check m21-validator-expansion-check m21-pipeline-governance-check m22-descriptor-uplift-check m22-validator-expansion-check m22-pipeline-governance-check m23-descriptor-consolidation-check m23-validator-expansion-check m23-pipeline-governance-check m24-residual-failure-closure-check m24-descriptor-completion-check m24-pipeline-governance-check m25-hardening-check m25-release-governance-check m26-activation-check m26-polish-baseline-check m26-polish-execution-check m26-governance-handoff-check m26-archive-check m27-cloud-workflow-check m27-assessor-package-check m27-archive-check m28-activation-check m28-narrative-baseline-check m28-narrative-execution-check m28-governance-handoff-check m28-archive-check m29-activation-check m29-release-baseline-check m29-delivery-stabilization-check m29-governance-freeze-check m29-archive-check m30-activation-check m30-repo-baseline-check m30-repo-execution-check m30-governance-check m30-archive-check m31-activation-check doctor-passrate-check provenance-coverage-check semantic-enrichment-check semantic-issue-trend-check semantic-spec-alignment-check demo-flow-check final-rehearsal-check review-passrate-check license-policy-check site-manifest-check pages-sync pages-check coverage api-check merge-acquire-manifests acquire-sources acquire-sources-nonwiki review-sources goal-state-update goal-state-check program-check task-approval-check program-autopilot program-autopilot-dry-run site-check ci clean

html:
	@set -e; \
		if [ ! -f out/m11_validator_unified_report.json ]; then \
			$(MAKE) m11-validator-unified-check > /dev/null; \
		fi; \
		TS=$${V:-0}; out=out/html; mkdir -p $$out; tmp=$$(mktemp); \
		find corpus/valid -type f -name '*.xml' | sort > $$tmp; \
		while IFS= read -r f; do \
			base=$$(basename "$$f"); stem=$${base%.xml}; \
			echo "HTML  $$out/$$stem.html"; \
			xsltproc --stringparam cssVersion $$TS xslt/card.xsl "$$f" > "$$out/$$stem.html"; \
		done < $$tmp; rm -f $$tmp; \
		mkdir -p site; cp -f docs/style.css site/style.css; find site -maxdepth 1 -type f -name '*.fdml.html' -delete; \
		scripts/build_index.sh $$TS; \

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

provenance-check:
	@set -e; mkdir -p out; \
	bin/fdml ingest --source analysis/gold/ingest/source_minimal.txt --out out/ingest-minimal.fdml.xml --title "Ingest Minimal" --meter 4/4 --tempo 112 --profile v1-basic --provenance-out out/provenance_minimal.json > /dev/null; \
	diff -u analysis/gold/ingest/provenance_minimal.json out/provenance_minimal.json; \
	python3 scripts/validate_json_schema.py schema/provenance.schema.json out/provenance_minimal.json > /dev/null

enrichment-report-check:
	@set -e; mvn -q -DskipTests package > /dev/null; mkdir -p out; \
	bin/fdml ingest --source analysis/gold/ingest/source_minimal.txt --out out/ingest-minimal.fdml.xml --title "Ingest Minimal" --meter 4/4 --tempo 112 --profile v1-basic --enable-enrichment --env-file src/test/resources/enrichment/offline.env --enrichment-report out/enrichment-report.json > /dev/null; \
	python3 scripts/validate_json_schema.py schema/enrichment-report.schema.json out/enrichment-report.json > /dev/null; \
	diff -u src/test/resources/enrichment/expected/offline-report.json out/enrichment-report.json

ingest-batch-check:
	@set -e; mvn -q -DskipTests package > /dev/null; rm -rf out/ingest-batch; mkdir -p out/ingest-batch; \
	bin/fdml ingest-batch --source-dir src/test/resources/ingest_batch/sources --out-dir out/ingest-batch --title-prefix "Batch Fixture" --meter 4/4 --tempo 112 --profile v1-basic --enable-enrichment --env-file src/test/resources/enrichment/offline.env --index-out out/ingest-batch/index.json > /dev/null; \
	python3 -c "import json,pathlib,sys;p=pathlib.Path('out/ingest-batch/index.json');d=json.loads(p.read_text(encoding='utf-8'));sys.exit(0 if d.get('failed')==0 else 1)"; \
	for f in $$(find out/ingest-batch -type f -name '*.provenance.json' | sort); do python3 scripts/validate_json_schema.py schema/provenance.schema.json $$f > /dev/null; done; \
	for f in $$(find out/ingest-batch -type f -name '*.enrichment-report.json' | sort); do python3 scripts/validate_json_schema.py schema/enrichment-report.schema.json $$f > /dev/null; done; \
	for f in $$(find out/ingest-batch -type f -name '*.fdml.xml' | sort); do bin/fdml doctor $$f --strict > /dev/null; done

ingest-promote-check:
	@set -e; mvn -q -DskipTests package > /dev/null; rm -rf out/ingest-batch-promote out/ingest-promoted out/ingest-quarantine; mkdir -p out/ingest-batch-promote; \
	bin/fdml ingest-batch --source-dir src/test/resources/ingest_batch/sources --out-dir out/ingest-batch-promote --title-prefix "Batch Fixture" --meter 4/4 --tempo 112 --profile v1-basic --enable-enrichment --env-file src/test/resources/enrichment/offline.env --index-out out/ingest-batch-promote/index.json > /dev/null; \
	bin/fdml ingest-promote --index out/ingest-batch-promote/index.json --dest out/ingest-promoted --quarantine-dir out/ingest-quarantine --quarantine-out out/ingest-quarantine/quarantine.json > /dev/null; \
	python3 -c "import json,pathlib,sys;p=pathlib.Path('out/ingest-quarantine/quarantine.json');d=json.loads(p.read_text(encoding='utf-8'));sys.exit(0 if d.get('quarantined')==0 and d.get('promoted',0)>0 else 1)"; \
	for f in $$(find out/ingest-promoted -type f -name '*.provenance.json' | sort); do python3 scripts/validate_json_schema.py schema/provenance.schema.json $$f > /dev/null; done; \
	for f in $$(find out/ingest-promoted -type f -name '*.enrichment-report.json' | sort); do python3 scripts/validate_json_schema.py schema/enrichment-report.schema.json $$f > /dev/null; done; \
	for f in $$(find out/ingest-promoted -type f -name '*.fdml.xml' | sort); do bin/fdml doctor $$f --strict > /dev/null; done

conversion-batch-check:
	@set -e; \
	if [ ! -d out/acquired_sources ] || [ ! -d out/acquired_sources_nonwiki ]; then \
		echo "conversion-batch-check: missing acquired source dirs. Run: make acquire-sources && make acquire-sources-nonwiki"; \
		exit 1; \
	fi; \
	mvn -q -DskipTests package > /dev/null; \
	rm -rf out/m2_conversion; mkdir -p out/m2_conversion/run1 out/m2_conversion/run2; \
	python3 scripts/convert_acquired_batch.py --source-dir out/acquired_sources --source-dir out/acquired_sources_nonwiki --out-dir out/m2_conversion/run1 --index-out out/m2_conversion/run1/index.json --title-prefix "M2 Conversion" --meter 4/4 --tempo 112 --profile v1-basic --min-outputs 30 > /dev/null; \
	python3 scripts/convert_acquired_batch.py --source-dir out/acquired_sources --source-dir out/acquired_sources_nonwiki --out-dir out/m2_conversion/run2 --index-out out/m2_conversion/run2/index.json --title-prefix "M2 Conversion" --meter 4/4 --tempo 112 --profile v1-basic --min-outputs 30 > /dev/null; \
	python3 -c "import json,pathlib,sys;a=json.loads(pathlib.Path('out/m2_conversion/run1/index.json').read_text(encoding='utf-8'));b=json.loads(pathlib.Path('out/m2_conversion/run2/index.json').read_text(encoding='utf-8'));sys.exit(0 if a==b else 1)"; \
	python3 -c "import json,pathlib,sys;a=json.loads(pathlib.Path('out/m2_conversion/run1/index.json').read_text(encoding='utf-8'));sys.exit(0 if int(a.get('total',0))>=30 and int(a.get('failed',1))==0 else 1)"

full-description-coverage-check:
	@set -e; \
	if [ ! -d out/m2_conversion/run1 ]; then \
		echo "full-description-coverage-check: missing conversion output. Run: make conversion-batch-check"; \
		exit 1; \
	fi; \
	python3 scripts/full_description_coverage.py --input-dir out/m2_conversion/run1 --report-out out/m6_full_description_current.json --label m6-full-description-current --strict-target-count 30

full-description-quality-check:
	@set -e; \
	python3 scripts/full_description_quality_gate.py --coverage-report src/test/resources/full_description_quality/pass-coverage.json --fdml-bin bin/fdml --min-pass-rate 0.95 --max-placeholder-only 0 --label full-description-quality-fixture-pass > /dev/null; \
	if python3 scripts/full_description_quality_gate.py --coverage-report src/test/resources/full_description_quality/fail-passrate-coverage.json --fdml-bin bin/fdml --min-pass-rate 0.95 --max-placeholder-only 0 --label full-description-quality-fixture-fail-passrate > /dev/null; then \
		echo "full-description-quality-check: expected failure for fail-passrate fixture"; \
		exit 1; \
	fi; \
	if python3 scripts/full_description_quality_gate.py --coverage-report src/test/resources/full_description_quality/fail-placeholder-coverage.json --fdml-bin bin/fdml --min-pass-rate 0.95 --max-placeholder-only 0 --label full-description-quality-fixture-fail-placeholder > /dev/null; then \
		echo "full-description-quality-check: expected failure for fail-placeholder fixture"; \
		exit 1; \
	fi; \
	if [ -d out/m2_conversion/run1 ]; then \
		$(MAKE) full-description-coverage-check > /dev/null; \
		python3 scripts/full_description_quality_gate.py --coverage-report out/m6_full_description_current.json --fdml-bin bin/fdml --min-pass-rate 0.95 --max-placeholder-only 0 --report-out out/m6_full_description_quality.json --label m6-full-description-quality; \
	else \
		echo "full-description-quality-check: conversion output not found; fixture checks only."; \
	fi

m8-geometry-baseline-check:
	@set -e; \
	if [ ! -d out/m2_conversion/run1 ]; then \
		echo "m8-geometry-baseline-check: missing conversion output. Run: make conversion-batch-check"; \
		exit 1; \
	fi; \
	python3 scripts/m8_geometry_baseline.py --input-dir out/m2_conversion/run1 --report-out out/m8_geometry_baseline.json --label m8-geometry-baseline --required-version 1.2 --min-total 90

m8-geometry-uplift-check:
	@set -e; \
	if [ ! -d out/m2_conversion/run1 ]; then \
		echo "m8-geometry-uplift-check: missing conversion output. Run: make conversion-batch-check"; \
		exit 1; \
	fi; \
	if [ ! -f out/m6_full_description_current.json ]; then \
		$(MAKE) full-description-coverage-check > /dev/null; \
	fi; \
	if [ ! -f out/m8_geometry_baseline.json ]; then \
		$(MAKE) m8-geometry-baseline-check > /dev/null; \
		fi; \
	python3 scripts/m8_geometry_uplift.py --source-dir out/m2_conversion/run1 --coverage-report out/m6_full_description_current.json --baseline-report out/m8_geometry_baseline.json --out-dir out/m8_geometry_uplift/run1 --report-out out/m8_geometry_uplift_progress.json --fdml-bin bin/fdml --label m8-geometry-uplift --require-all-strict --min-doctor-pass-rate 0.95 --min-geo-pass-rate 1.0

m8-geometry-governance-check:
	@set -e; \
	python3 scripts/m8_geometry_governance_gate.py --baseline-report src/test/resources/m8_geometry_governance/pass-baseline.json --coverage-report src/test/resources/m8_geometry_governance/pass-coverage.json --uplift-report src/test/resources/m8_geometry_governance/pass-uplift.json --label m8-geometry-governance-fixture-pass --min-baseline-total 4 --min-strict-candidates 3 --min-doctor-pass-rate 0.95 --min-geo-pass-rate 0.95 --min-ready-rate 0.95 > /dev/null 2>&1; \
	if python3 scripts/m8_geometry_governance_gate.py --baseline-report src/test/resources/m8_geometry_governance/pass-baseline.json --coverage-report src/test/resources/m8_geometry_governance/pass-coverage.json --uplift-report src/test/resources/m8_geometry_governance/fail-uplift.json --label m8-geometry-governance-fixture-fail --min-baseline-total 4 --min-strict-candidates 3 --min-doctor-pass-rate 0.95 --min-geo-pass-rate 0.95 --min-ready-rate 0.95 > /dev/null 2>&1; then \
		echo "m8-geometry-governance-check: expected failure for fail-uplift fixture"; \
		exit 1; \
	fi; \
	if [ -d out/m2_conversion/run1 ]; then \
		$(MAKE) m8-geometry-baseline-check > /dev/null; \
		$(MAKE) m8-geometry-uplift-check > /dev/null; \
		python3 scripts/m8_geometry_governance_gate.py --baseline-report out/m8_geometry_baseline.json --coverage-report out/m6_full_description_current.json --uplift-report out/m8_geometry_uplift_progress.json --report-out out/m8_geometry_governance.json --label m8-geometry-governance-live --min-baseline-total 90 --min-strict-candidates 30 --min-doctor-pass-rate 0.95 --min-geo-pass-rate 1.0 --min-ready-rate 1.0; \
	else \
		echo "m8-geometry-governance-check: conversion output not found; fixture checks only."; \
	fi

m9-geometry-full-corpus-check:
	@set -e; \
	if [ ! -d out/m2_conversion/run1 ]; then \
		echo "m9-geometry-full-corpus-check: missing conversion output. Run: make conversion-batch-check"; \
		exit 1; \
	fi; \
	if [ ! -f out/m8_geometry_baseline.json ]; then \
		$(MAKE) m8-geometry-baseline-check > /dev/null; \
	fi; \
	if [ ! -f out/m6_full_description_current.json ]; then \
		$(MAKE) full-description-coverage-check > /dev/null; \
	fi; \
	python3 scripts/m9_full_corpus_promotion.py --source-dir out/m2_conversion/run1 --baseline-report out/m8_geometry_baseline.json --coverage-report out/m6_full_description_current.json --out-dir out/m9_full_corpus_v12/run1 --report-out out/m9_geometry_full_corpus.json --fdml-bin bin/fdml --label m9-full-corpus-promotion --min-total 90 --min-promoted 90 --min-doctor-pass-rate 0.95 --min-geo-pass-rate 1.0 --min-ready-rate 1.0

m9-full-description-uplift-check:
	@set -e; \
	if [ ! -d out/m9_full_corpus_v12/run1 ]; then \
		$(MAKE) m9-geometry-full-corpus-check > /dev/null; \
	fi; \
	if ! python3 -c "from pathlib import Path; src={p.name for p in Path('out/m2_conversion/run1').glob('*.fdml.xml')}; promoted={p.name for p in Path('out/m9_full_corpus_v12/run1').glob('*.fdml.xml')}; raise SystemExit(0 if src==promoted else 1)"; then \
		echo 'm9-full-description-uplift-check: detected stale promoted corpus; regenerating m9 full-corpus promotion'; \
		$(MAKE) m9-geometry-full-corpus-check > /dev/null; \
	fi; \
	if [ ! -f out/m6_full_description_current.json ]; then \
		$(MAKE) full-description-coverage-check > /dev/null; \
	fi; \
	python3 scripts/m9_full_description_uplift.py --source-dir out/m9_full_corpus_v12/run1 --baseline-coverage-report out/m6_full_description_current.json --out-dir out/m9_full_description_uplift/run1 --coverage-report-out out/m9_full_description_current.json --quality-report-out out/m9_full_description_quality.json --report-out out/m9_full_description_progress.json --fdml-bin bin/fdml --label m9-full-description-uplift --strict-target-count 85 --min-total 90 --min-steps 8 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0 --min-quality-pass-rate 0.95 --max-placeholder-only 0

m10-discovery-run:
	@set -e; \
	if [ ! -d out/m9_full_description_uplift/run1 ]; then \
		$(MAKE) m9-full-description-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m10_multi_pass_discovery_offline.py --input-dir out/m9_full_description_uplift/run1 --out-dir out/m10_discovery/run1 --report-out out/m10_discovery/run1/discovery_report.json --ontology-out out/m10_ontology_candidates.json --validator-out out/m10_validator_candidates.json --coverage-gaps-out out/m10_coverage_gaps.json --passes 3 --min-confidence 0.60

m10-discovery-governance-check:
	@set -e; \
	python3 scripts/m10_discovery_governance_gate.py --discovery-report src/test/resources/m10_discovery_governance/pass-discovery-report.json --ontology-candidates src/test/resources/m10_discovery_governance/pass-ontology-candidates.json --validator-candidates src/test/resources/m10_discovery_governance/pass-validator-candidates.json --coverage-gaps src/test/resources/m10_discovery_governance/pass-coverage-gaps.json --label m10-discovery-governance-fixture-pass --min-total-files 3 --min-pass-count 3 --max-growth-ratio 0.05 --required-consecutive-saturation 2 --max-checklist-missing-ratio 0.05 --max-checklist-uncertain-ratio 0.10 --max-unresolved-files 0 --min-parameter-candidates 3 --min-validator-candidates 3 --min-candidate-confidence 0.60 > /dev/null; \
	if python3 scripts/m10_discovery_governance_gate.py --discovery-report src/test/resources/m10_discovery_governance/fail-discovery-report.json --ontology-candidates src/test/resources/m10_discovery_governance/pass-ontology-candidates.json --validator-candidates src/test/resources/m10_discovery_governance/pass-validator-candidates.json --coverage-gaps src/test/resources/m10_discovery_governance/pass-coverage-gaps.json --label m10-discovery-governance-fixture-fail --min-total-files 3 --min-pass-count 3 --max-growth-ratio 0.05 --required-consecutive-saturation 2 --max-checklist-missing-ratio 0.05 --max-checklist-uncertain-ratio 0.10 --max-unresolved-files 0 --min-parameter-candidates 3 --min-validator-candidates 3 --min-candidate-confidence 0.60 > /dev/null; then \
		echo "m10-discovery-governance-check: expected failure for fail-discovery fixture"; \
		exit 1; \
	fi; \
	if [ -f out/m10_discovery/run1/discovery_report.json ] && [ -f out/m10_ontology_candidates.json ] && [ -f out/m10_validator_candidates.json ] && [ -f out/m10_coverage_gaps.json ]; then \
		python3 scripts/m10_discovery_governance_gate.py --discovery-report out/m10_discovery/run1/discovery_report.json --ontology-candidates out/m10_ontology_candidates.json --validator-candidates out/m10_validator_candidates.json --coverage-gaps out/m10_coverage_gaps.json --report-out out/m10_discovery_governance.json --label m10-discovery-governance-live --min-total-files 90 --min-pass-count 3 --max-growth-ratio 0.01 --required-consecutive-saturation 2 --max-checklist-missing-ratio 0.05 --max-checklist-uncertain-ratio 0.10 --max-unresolved-files 0 --min-parameter-candidates 1 --min-validator-candidates 1 --min-candidate-confidence 0.60; \
	else \
		echo "m10-discovery-governance-check: live discovery outputs not found; fixture checks only."; \
	fi

m11-contract-promotion-check:
	@set -e; \
	if [ ! -f out/m10_ontology_candidates.json ]; then \
		$(MAKE) m10-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m11_contract_promotion.py --candidates out/m10_ontology_candidates.json --schema schema/fdml.xsd --spec docs/FDML-SPEC.md --report-out out/m11_contract_promotion.json --label m11-contract-promotion-live --min-confidence 0.60 --min-support-count 1 --min-accepted 4

m11-validator-unified-check:
	@set -e; \
	if [ ! -d out/m9_full_description_uplift/run1 ]; then \
		$(MAKE) m9-full-description-uplift-check > /dev/null; \
	fi; \
	if [ ! -f out/m10_validator_candidates.json ]; then \
		$(MAKE) m10-discovery-run > /dev/null; \
	fi; \
	if [ ! -f out/m11_contract_promotion.json ]; then \
		$(MAKE) m11-contract-promotion-check > /dev/null; \
	fi; \
	python3 scripts/m11_validator_unified.py --input-dir out/m9_full_description_uplift/run1 --validator-candidates out/m10_validator_candidates.json --contract-promotion out/m11_contract_promotion.json --fdml-bin bin/fdml --report-out out/m11_validator_unified_report.json --label m11-validator-unified-live --min-total-files 90 --min-rules 3

m11-pipeline-governance-check:
	@set -e; \
	python3 scripts/m11_pipeline_governance_gate.py --contract-report src/test/resources/m11_pipeline_governance/pass-contract-report.json --validator-report src/test/resources/m11_pipeline_governance/pass-validator-report.json --demo-flow-report src/test/resources/m11_pipeline_governance/pass-demo-flow-report.json --site-index src/test/resources/m11_pipeline_governance/pass-site-index.json --makefile Makefile --build-index-script scripts/build_index.sh --required-corpus-dir out/m9_full_description_uplift/run1 --label m11-pipeline-governance-fixture-pass --min-total-files 3 --min-recognized-rules 2 --min-promoted-fields 2 --min-accepted-rows 2 --min-unified-items 3 --max-legacy-ingest-auto-items 0 > /dev/null 2>&1; \
	if python3 scripts/m11_pipeline_governance_gate.py --contract-report src/test/resources/m11_pipeline_governance/pass-contract-report.json --validator-report src/test/resources/m11_pipeline_governance/fail-validator-report.json --demo-flow-report src/test/resources/m11_pipeline_governance/pass-demo-flow-report.json --site-index src/test/resources/m11_pipeline_governance/pass-site-index.json --makefile Makefile --build-index-script scripts/build_index.sh --required-corpus-dir out/m9_full_description_uplift/run1 --label m11-pipeline-governance-fixture-fail --min-total-files 3 --min-recognized-rules 2 --min-promoted-fields 2 --min-accepted-rows 2 --min-unified-items 3 --max-legacy-ingest-auto-items 0 > /dev/null 2>&1; then \
		echo "m11-pipeline-governance-check: expected failure for fail-validator fixture"; \
		exit 1; \
	fi; \
	$(MAKE) demo-flow-check > /dev/null; \
	python3 scripts/m11_pipeline_governance_gate.py --contract-report out/m11_contract_promotion.json --validator-report out/m11_validator_unified_report.json --demo-flow-report out/demo_flow/demo_flow_report.json --site-index site/index.json --makefile Makefile --build-index-script scripts/build_index.sh --report-out out/m11_pipeline_governance.json --required-corpus-dir out/m9_full_description_uplift/run1 --label m11-pipeline-governance-live --min-total-files 90 --min-recognized-rules 3 --min-promoted-fields 4 --min-accepted-rows 4 --min-unified-items 90 --max-legacy-ingest-auto-items 0

m12-semantic-depth-check:
	@set -e; \
	python3 scripts/m12_semantic_depth_gate.py --discovery-report src/test/resources/m12_semantic_depth/pass-discovery-report.json --ontology-candidates src/test/resources/m12_semantic_depth/pass-ontology-candidates.json --validator-candidates src/test/resources/m12_semantic_depth/pass-validator-candidates.json --contract-promotion src/test/resources/m12_semantic_depth/pass-contract-promotion.json --validator-unified src/test/resources/m12_semantic_depth/pass-validator-unified.json --rubric src/test/resources/m12_semantic_depth/pass-rubric.json --report-out out/m12_semantic_depth_fixture_pass.json --label m12-semantic-depth-fixture-pass --min-total-files 3 > /dev/null 2>&1; \
	if python3 scripts/m12_semantic_depth_gate.py --discovery-report src/test/resources/m12_semantic_depth/fail-discovery-report.json --ontology-candidates src/test/resources/m12_semantic_depth/pass-ontology-candidates.json --validator-candidates src/test/resources/m12_semantic_depth/pass-validator-candidates.json --contract-promotion src/test/resources/m12_semantic_depth/pass-contract-promotion.json --validator-unified src/test/resources/m12_semantic_depth/pass-validator-unified.json --rubric src/test/resources/m12_semantic_depth/pass-rubric.json --report-out out/m12_semantic_depth_fixture_fail.json --label m12-semantic-depth-fixture-fail --min-total-files 3 > /dev/null 2>&1; then \
		echo "m12-semantic-depth-check: expected failure for fail-discovery fixture"; \
		exit 1; \
	fi; \
	if [ -f out/m10_discovery/run1/discovery_report.json ] && [ -f out/m10_ontology_candidates.json ] && [ -f out/m10_validator_candidates.json ] && [ -f out/m11_contract_promotion.json ] && [ -f out/m11_validator_unified_report.json ] && [ -f analysis/program/m12_semantic_rubric.json ]; then \
		python3 scripts/m12_semantic_depth_gate.py --discovery-report out/m10_discovery/run1/discovery_report.json --ontology-candidates out/m10_ontology_candidates.json --validator-candidates out/m10_validator_candidates.json --contract-promotion out/m11_contract_promotion.json --validator-unified out/m11_validator_unified_report.json --rubric analysis/program/m12_semantic_rubric.json --report-out out/m12_semantic_depth_report.json --label m12-semantic-depth-live --min-total-files 90; \
	else \
		echo "m12-semantic-depth-check: live discovery/validator/rubric artifacts not found; fixture checks only."; \
	fi

m13-parameter-registry-check:
	@set -e; \
	if [ ! -d out/m9_full_description_uplift/run1 ]; then \
		$(MAKE) m9-full-description-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m13_parameter_registry.py --input-dir out/m9_full_description_uplift/run1 --report-out out/m13_parameter_registry.json --fit-report-out out/m13_fdml_fit_report.json --label m13-parameter-registry-live --min-total-files 90 --min-unique-keys 15

m13-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m13_parameter_registry.json ] || [ ! -f out/m13_fdml_fit_report.json ]; then \
		$(MAKE) m13-parameter-registry-check > /dev/null; \
	fi; \
	python3 scripts/m13_validator_expansion.py --input-dir out/m9_full_description_uplift/run1 --registry-report out/m13_parameter_registry.json --fit-report out/m13_fdml_fit_report.json --report-out out/m13_validator_expansion_report.json --label m13-validator-expansion-live --min-total-files 90 --min-rules 10

m13-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m10_discovery_governance.json ]; then \
		$(MAKE) m10-discovery-governance-check > /dev/null; \
	fi; \
	if [ ! -f out/m11_contract_promotion.json ]; then \
		$(MAKE) m11-contract-promotion-check > /dev/null; \
	fi; \
	if [ ! -f out/m13_validator_expansion_report.json ]; then \
		$(MAKE) m13-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m13_pipeline_governance_gate.py --discovery-governance out/m10_discovery_governance.json --contract-report out/m11_contract_promotion.json --registry-report out/m13_parameter_registry.json --fit-report out/m13_fdml_fit_report.json --validator-expansion-report out/m13_validator_expansion_report.json --makefile Makefile --report-out out/m13_pipeline_governance.json --label m13-pipeline-governance-live --required-corpus-dir out/m9_full_description_uplift/run1 --min-total-files 90 --min-priority-keys 10 --min-expanded-rules 10 --min-priority-coverage-ratio 1.0 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m14-contract-uplift-check:
	@set -e; \
	if [ ! -d out/m9_full_description_uplift/run1 ]; then \
		$(MAKE) m9-full-description-uplift-check > /dev/null; \
	fi; \
	if [ ! -f out/m13_parameter_registry.json ] || [ ! -f out/m13_fdml_fit_report.json ]; then \
		$(MAKE) m13-parameter-registry-check > /dev/null; \
	fi; \
	python3 scripts/m14_contract_uplift.py --source-dir out/m9_full_description_uplift/run1 --out-dir out/m14_contract_uplift/run1 --baseline-registry-report out/m13_parameter_registry.json --baseline-fit-report out/m13_fdml_fit_report.json --post-registry-report-out out/m14_parameter_registry.json --post-fit-report-out out/m14_fdml_fit_report.json --report-out out/m14_contract_uplift_report.json --fdml-bin bin/fdml --label m14-contract-uplift-live --min-total-files 90 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0 --min-expressive-reduction 50 --min-targeted-keys-improved 6

m14-context-specificity-check:
	@set -e; \
	if [ ! -d out/m14_contract_uplift/run1 ] || [ ! -f out/m14_contract_uplift_report.json ]; then \
		$(MAKE) m14-contract-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m14_context_specificity.py --source-dir out/m14_contract_uplift/run1 --out-dir out/m14_context_specificity/run1 --acquired-index out/acquired_sources/index.json --acquired-nonwiki-index out/acquired_sources_nonwiki/index.json --merged-manifest out/acquired_sources/merged_manifest.json --baseline-registry-report out/m14_parameter_registry.json --baseline-fit-report out/m14_fdml_fit_report.json --post-registry-report-out out/m14_context_parameter_registry.json --post-fit-report-out out/m14_context_fdml_fit_report.json --report-out out/m14_context_specificity_report.json --fdml-bin bin/fdml --label m14-context-specificity-live --min-total-files 90 --min-country-specific-ratio 0.90 --min-region-specific-ratio 0.90 --min-context-gap-reduction 80 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0

m14-validator-burndown-check:
	@set -e; \
	if [ ! -d out/m14_context_specificity/run1 ] || [ ! -f out/m14_context_specificity_report.json ]; then \
		$(MAKE) m14-context-specificity-check > /dev/null; \
	fi; \
	python3 scripts/m13_validator_expansion.py --input-dir out/m14_context_specificity/run1 --registry-report out/m14_context_parameter_registry.json --fit-report out/m14_context_fdml_fit_report.json --report-out out/m14_validator_expansion_report.json --label m14-validator-expansion-live --min-total-files 90 --min-rules 10; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m13_validator_expansion_report.json --current-report out/m14_validator_expansion_report.json --report-out out/m14_validator_burndown_report.json --label m14-validator-burndown-live --min-total-files 90 --min-rule-count 10 --min-reduction-ratio 0.70 --max-files-with-fail-ratio 0.30

m15-discovery-run:
	@set -e; \
	if [ ! -d out/m14_context_specificity/run1 ] || [ ! -f out/m14_context_specificity_report.json ]; then \
		$(MAKE) m14-context-specificity-check > /dev/null; \
	fi; \
	python3 scripts/m10_multi_pass_discovery_offline.py --input-dir out/m14_context_specificity/run1 --out-dir out/m15_discovery/run1 --report-out out/m15_discovery/run1/discovery_report.json --ontology-out out/m15_ontology_candidates.json --validator-out out/m15_validator_candidates.json --coverage-gaps-out out/m15_coverage_gaps.json --passes 5 --label m15-multi-pass-discovery-offline --min-confidence 0.60

m15-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m15_discovery/run1/discovery_report.json ] || [ ! -f out/m15_validator_candidates.json ]; then \
		$(MAKE) m15-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m15_validator_expansion.py --input-dir out/m9_full_description_uplift/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m15_validator_expansion_baseline_report.json --label m15-validator-expansion-baseline --min-total-files 90 --min-rules 15; \
	python3 scripts/m15_validator_expansion.py --input-dir out/m14_context_specificity/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m15_validator_expansion_report.json --label m15-validator-expansion-live --min-total-files 90 --min-rules 15; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m15_validator_expansion_baseline_report.json --current-report out/m15_validator_expansion_report.json --report-out out/m15_validator_burndown_report.json --label m15-validator-burndown-live --min-total-files 90 --min-rule-count 15 --min-reduction-ratio 0.70 --max-files-with-fail-ratio 0.30

m15-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m15_validator_expansion_report.json ] || [ ! -f out/m15_validator_burndown_report.json ]; then \
		$(MAKE) m15-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m15_pipeline_governance_gate.py --discovery-report out/m15_discovery/run1/discovery_report.json --validator-report out/m15_validator_expansion_report.json --burndown-report out/m15_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --report-out out/m15_pipeline_governance.json --label m15-pipeline-governance-live --required-corpus-dir out/m14_context_specificity/run1 --min-total-files 90 --min-validator-candidates 13 --min-expanded-rules 15 --min-reduction-ratio 0.70 --max-failure-file-ratio 0.30 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m16-contract-promotion-check:
	@set -e; \
	if [ ! -f out/m15_ontology_candidates.json ]; then \
		$(MAKE) m15-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m11_contract_promotion.py --candidates out/m15_ontology_candidates.json --schema schema/fdml.xsd --spec docs/FDML-SPEC.md --report-out out/m16_contract_promotion.json --label m16-contract-promotion-live --min-confidence 0.60 --min-support-count 1 --min-accepted 6

m16-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m16_contract_promotion.json ]; then \
		$(MAKE) m16-contract-promotion-check > /dev/null; \
	fi; \
	if [ ! -f out/m15_validator_candidates.json ]; then \
		$(MAKE) m15-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m16_validator_expansion.py --input-dir out/m9_full_description_uplift/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m16_validator_expansion_baseline_report.json --label m16-validator-expansion-baseline --min-total-files 90 --min-rules 25; \
	python3 scripts/m16_validator_expansion.py --input-dir out/m14_context_specificity/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m16_validator_expansion_report.json --label m16-validator-expansion-live --min-total-files 90 --min-rules 25; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m16_validator_expansion_baseline_report.json --current-report out/m16_validator_expansion_report.json --report-out out/m16_validator_burndown_report.json --label m16-validator-burndown-live --min-total-files 90 --min-rule-count 25 --min-reduction-ratio 0.70 --max-files-with-fail-ratio 0.30

m16-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m16_validator_expansion_report.json ] || [ ! -f out/m16_validator_burndown_report.json ]; then \
		$(MAKE) m16-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m16_pipeline_governance_gate.py --contract-report out/m16_contract_promotion.json --validator-report out/m16_validator_expansion_report.json --burndown-report out/m16_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --report-out out/m16_pipeline_governance.json --label m16-pipeline-governance-live --required-live-corpus-dir out/m14_context_specificity/run1 --required-baseline-corpus-dir out/m9_full_description_uplift/run1 --required-candidate-report out/m15_validator_candidates.json --min-total-files 90 --min-accepted-rows 15 --min-promoted-fields 15 --max-unknown-key-count 0 --min-expanded-rules 25 --min-reduction-ratio 0.70 --max-failure-file-ratio 0.30 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m17-descriptor-registry-check:
	@set -e; \
	if [ ! -d out/m14_context_specificity/run1 ] || [ ! -f out/m14_context_specificity_report.json ]; then \
		$(MAKE) m14-context-specificity-check > /dev/null; \
	fi; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m14_context_specificity/run1 --report-out out/m17_descriptor_registry.json --coverage-report-out out/m17_fdml_coverage_report.json --label m17-descriptor-registry-live --min-total-files 90 --min-unique-keys 20 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 55 --min-files-with-combined-depth 45

m17-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m17_descriptor_registry.json ] || [ ! -f out/m17_fdml_coverage_report.json ]; then \
		$(MAKE) m17-descriptor-registry-check > /dev/null; \
	fi; \
	if [ ! -f out/m15_validator_candidates.json ]; then \
		$(MAKE) m15-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m9_full_description_uplift/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m17_validator_expansion_baseline_report.json --label m17-validator-expansion-baseline --min-total-files 90 --min-rules 35; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m14_context_specificity/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m17_validator_expansion_report.json --label m17-validator-expansion-live --min-total-files 90 --min-rules 35; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m17_validator_expansion_baseline_report.json --current-report out/m17_validator_expansion_report.json --report-out out/m17_validator_burndown_report.json --label m17-validator-burndown-live --min-total-files 90 --min-rule-count 35 --min-reduction-ratio 0.70 --max-files-with-fail-ratio 0.30

m17-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m17_validator_expansion_report.json ] || [ ! -f out/m17_validator_burndown_report.json ]; then \
		$(MAKE) m17-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m17_pipeline_governance_gate.py --descriptor-registry-report out/m17_descriptor_registry.json --descriptor-coverage-report out/m17_fdml_coverage_report.json --validator-report out/m17_validator_expansion_report.json --burndown-report out/m17_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --report-out out/m17_pipeline_governance.json --label m17-pipeline-governance-live --required-live-corpus-dir out/m14_context_specificity/run1 --required-baseline-corpus-dir out/m9_full_description_uplift/run1 --required-candidate-report out/m15_validator_candidates.json --min-total-files 90 --min-descriptor-keys-with-support 20 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 55 --min-files-with-combined-depth 45 --min-expanded-rules 35 --min-reduction-ratio 0.70 --max-failure-file-ratio 0.30 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m18-realism-uplift-check:
	@set -e; \
	if [ ! -f out/m17_validator_expansion_report.json ]; then \
		$(MAKE) m17-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m18_realism_uplift.py --source-dir out/m14_context_specificity/run1 --out-dir out/m18_realism_uplift/run1 --report-out out/m18_realism_uplift_report.json --fdml-bin bin/fdml --label m18-realism-uplift-live --min-total-files 90 --min-files-updated 20 --min-turn-axis-coverage 0.90 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m18_realism_uplift/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m18_validator_realism_uplift_report.json --label m18-validator-realism-uplift-live --min-total-files 90 --min-rules 35; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m17_validator_expansion_report.json --current-report out/m18_validator_realism_uplift_report.json --report-out out/m18_validator_burndown_report.json --label m18-validator-burndown-live --min-total-files 90 --min-rule-count 35 --min-reduction-ratio 0.50 --max-files-with-fail-ratio 0.30

m18-descriptor-uplift-check:
	@set -e; \
	if [ ! -d out/m18_realism_uplift/run1 ] || [ ! -f out/m18_realism_uplift_report.json ]; then \
		$(MAKE) m18-realism-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m18_descriptor_uplift.py --source-dir out/m18_realism_uplift/run1 --out-dir out/m18_descriptor_uplift/run1 --baseline-coverage-report out/m17_fdml_coverage_report.json --report-out out/m18_descriptor_uplift_report.json --fdml-bin bin/fdml --label m18-descriptor-uplift-live --min-total-files 90 --min-files-updated 16 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m18_descriptor_uplift/run1 --report-out out/m18_descriptor_registry.json --coverage-report-out out/m18_fdml_coverage_report.json --label m18-fdml-coverage-live --min-total-files 90 --min-unique-keys 20 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 60

m18-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m18_validator_realism_uplift_report.json ] || [ ! -f out/m18_validator_burndown_report.json ]; then \
		$(MAKE) m18-realism-uplift-check > /dev/null; \
	fi; \
	if [ ! -f out/m18_fdml_coverage_report.json ] || [ ! -f out/m18_descriptor_registry.json ]; then \
		$(MAKE) m18-descriptor-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m18_pipeline_governance_gate.py --realism-report out/m18_realism_uplift_report.json --descriptor-uplift-report out/m18_descriptor_uplift_report.json --descriptor-registry-report out/m18_descriptor_registry.json --descriptor-coverage-report out/m18_fdml_coverage_report.json --validator-report out/m18_validator_realism_uplift_report.json --burndown-report out/m18_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --report-out out/m18_pipeline_governance.json --label m18-pipeline-governance-live --required-realism-source-dir out/m14_context_specificity/run1 --required-realism-out-dir out/m18_realism_uplift/run1 --required-descriptor-out-dir out/m18_descriptor_uplift/run1 --required-candidate-report out/m15_validator_candidates.json --required-baseline-report out/m17_validator_expansion_report.json --min-total-files 90 --min-realism-files-updated 20 --min-descriptor-files-updated 16 --min-descriptor-keys-with-support 20 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 60 --min-expanded-rules 35 --min-reduction-ratio 0.50 --max-failure-file-ratio 0.30 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m19-corpus-expansion-baseline-check:
	@set -e; \
	if [ ! -d out/m18_descriptor_uplift/run1 ] || [ ! -f out/m18_descriptor_uplift_report.json ]; then \
		$(MAKE) m18-descriptor-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m18_descriptor_uplift/run1 --report-out out/m19_descriptor_registry.json --coverage-report-out out/m19_fdml_coverage_report.json --label m19-fdml-coverage-baseline-live --min-total-files 90 --min-unique-keys 20 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 60; \
	python3 scripts/m19_corpus_expansion_baseline.py --input-dir out/m18_descriptor_uplift/run1 --coverage-report out/m19_fdml_coverage_report.json --manifest out/acquired_sources/merged_manifest.json --report-out out/m19_corpus_expansion_report.json --label m19-corpus-expansion-baseline-live --min-total-files 90 --min-country-coverage-ratio 0.95 --min-region-coverage-ratio 0.95 --min-region-buckets 5

m19-descriptor-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m19_corpus_expansion_report.json ] || [ ! -f out/m19_fdml_coverage_report.json ]; then \
		$(MAKE) m19-corpus-expansion-baseline-check > /dev/null; \
	fi; \
	python3 scripts/m19_descriptor_depth_uplift.py --source-dir out/m18_descriptor_uplift/run1 --out-dir out/m19_descriptor_uplift/run1 --baseline-coverage-report out/m19_fdml_coverage_report.json --report-out out/m19_descriptor_uplift_report.json --fdml-bin bin/fdml --label m19-descriptor-uplift-live --min-total-files 90 --min-files-updated 50 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0 --min-target-key-support-ratio 0.85; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m19_descriptor_uplift/run1 --report-out out/m19_descriptor_registry.json --coverage-report-out out/m19_fdml_coverage_report.json --label m19-fdml-coverage-live --min-total-files 90 --min-unique-keys 20 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 60; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m18_descriptor_uplift/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m19_validator_expansion_baseline_m17_report.json --label m19-validator-baseline-m17-live --min-total-files 90 --min-rules 35; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m19_descriptor_uplift/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m19_validator_expansion_m17_report.json --label m19-validator-current-m17-live --min-total-files 90 --min-rules 35; \
	python3 scripts/m19_validator_expansion.py --input-dir out/m18_descriptor_uplift/run1 --base-report out/m19_validator_expansion_baseline_m17_report.json --report-out out/m19_validator_expansion_baseline_report.json --label m19-validator-expansion-baseline-live --min-total-files 90 --min-rules 45 --max-rules-with-no-applicability 1; \
	python3 scripts/m19_validator_expansion.py --input-dir out/m19_descriptor_uplift/run1 --base-report out/m19_validator_expansion_m17_report.json --report-out out/m19_validator_expansion_report.json --label m19-validator-expansion-live --min-total-files 90 --min-rules 45 --max-rules-with-no-applicability 1; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m19_validator_expansion_baseline_report.json --current-report out/m19_validator_expansion_report.json --report-out out/m19_validator_burndown_report.json --label m19-validator-burndown-live --min-total-files 90 --min-rule-count 45 --min-reduction-ratio 0.70 --max-files-with-fail-ratio 0.30

m19-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m19_corpus_expansion_report.json ] || [ ! -f out/m19_fdml_coverage_report.json ]; then \
		$(MAKE) m19-corpus-expansion-baseline-check > /dev/null; \
	fi; \
	if [ ! -f out/m19_validator_expansion_report.json ] || [ ! -f out/m19_validator_burndown_report.json ]; then \
		$(MAKE) m19-descriptor-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m19_pipeline_governance_gate.py --expansion-report out/m19_corpus_expansion_report.json --descriptor-uplift-report out/m19_descriptor_uplift_report.json --descriptor-registry-report out/m19_descriptor_registry.json --descriptor-coverage-report out/m19_fdml_coverage_report.json --validator-m17-baseline-report out/m19_validator_expansion_baseline_m17_report.json --validator-m17-current-report out/m19_validator_expansion_m17_report.json --validator-baseline-report out/m19_validator_expansion_baseline_report.json --validator-current-report out/m19_validator_expansion_report.json --burndown-report out/m19_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --report-out out/m19_pipeline_governance.json --label m19-pipeline-governance-live --required-source-dir out/m18_descriptor_uplift/run1 --required-descriptor-out-dir out/m19_descriptor_uplift/run1 --required-candidate-report out/m15_validator_candidates.json --required-m17-baseline-report out/m19_validator_expansion_baseline_m17_report.json --required-m17-current-report out/m19_validator_expansion_m17_report.json --required-baseline-report out/m19_validator_expansion_baseline_report.json --required-current-report out/m19_validator_expansion_report.json --required-coverage-report out/m19_fdml_coverage_report.json --min-total-files 90 --min-country-coverage-ratio 0.95 --min-region-coverage-ratio 0.95 --min-region-buckets 5 --min-descriptor-files-updated 50 --min-descriptor-keys-with-support 20 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 60 --min-target-key-support-ratio 0.85 --min-expanded-rules 45 --min-reduction-ratio 0.70 --max-failure-file-ratio 0.30 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m20-corpus-expansion-check:
	@set -e; \
	if [ ! -f out/m19_corpus_expansion_report.json ]; then \
		$(MAKE) m19-corpus-expansion-baseline-check > /dev/null; \
	fi; \
	$(MAKE) acquire-sources > /dev/null; \
	$(MAKE) acquire-sources-nonwiki > /dev/null; \
	$(MAKE) conversion-batch-check > /dev/null; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m2_conversion/run1 --report-out out/m20_descriptor_registry.json --coverage-report-out out/m20_fdml_coverage_report.json --label m20-fdml-coverage-live --min-total-files 100 --min-unique-keys 18 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 80 --min-files-with-combined-depth 70; \
	python3 scripts/m20_corpus_expansion.py --input-dir out/m2_conversion/run1 --coverage-report out/m20_fdml_coverage_report.json --manifest out/acquired_sources/merged_manifest.json --baseline-report out/m19_corpus_expansion_report.json --report-out out/m20_corpus_expansion_report.json --label m20-corpus-expansion-live --min-total-files 100 --min-country-coverage-ratio 0.0 --min-region-coverage-ratio 0.0 --min-region-buckets 5 --min-baseline-gap-reduction-ratio 0.60 --min-gap-buckets-improved 3

m20-descriptor-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m20_corpus_expansion_report.json ] || [ ! -f out/m20_fdml_coverage_report.json ]; then \
		$(MAKE) m20-corpus-expansion-check > /dev/null; \
	fi; \
	if [ ! -f out/m15_validator_candidates.json ]; then \
		$(MAKE) m15-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m20_descriptor_evidence.py --source-dir out/m2_conversion/run1 --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --out-dir out/m20_descriptor_evidence/run1 --report-out out/m20_descriptor_evidence_report.json --fdml-bin bin/fdml --label m20-descriptor-evidence-live --min-total-files 100 --min-files-updated 40 --min-source-grounded-additions 80 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0 --min-keys-with-growth 6; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m20_descriptor_evidence/run1 --report-out out/m20_descriptor_registry.json --coverage-report-out out/m20_fdml_coverage_report.json --label m20-fdml-coverage-evidence-live --min-total-files 100 --min-unique-keys 18 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 85; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m2_conversion/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m20_validator_expansion_baseline_m17_report.json --label m20-validator-expansion-baseline-m17-live --min-total-files 100 --min-rules 35 --max-rules-with-no-applicability 30; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m20_descriptor_evidence/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m20_validator_expansion_m17_report.json --label m20-validator-expansion-m17-live --min-total-files 100 --min-rules 35 --max-rules-with-no-applicability 30; \
	python3 scripts/m20_validator_expansion.py --input-dir out/m2_conversion/run1 --base-report out/m20_validator_expansion_baseline_m17_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m20_validator_expansion_baseline_report.json --label m20-validator-expansion-baseline-live --min-total-files 100 --min-rules 8 --max-rules-with-no-applicability 30 --min-total-applicable 80; \
	python3 scripts/m20_validator_expansion.py --input-dir out/m20_descriptor_evidence/run1 --base-report out/m20_validator_expansion_m17_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m20_validator_expansion_report.json --label m20-validator-expansion-live --min-total-files 100 --min-rules 8 --max-rules-with-no-applicability 30 --min-total-applicable 80; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m20_validator_expansion_baseline_report.json --current-report out/m20_validator_expansion_report.json --report-out out/m20_validator_burndown_report.json --label m20-validator-burndown-live --min-total-files 100 --min-rule-count 8 --min-reduction-ratio 0.60 --max-files-with-fail-ratio 0.35

m20-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m20_corpus_expansion_report.json ] || [ ! -f out/m20_fdml_coverage_report.json ]; then \
		$(MAKE) m20-corpus-expansion-check > /dev/null; \
	fi; \
	if [ ! -f out/m20_validator_expansion_report.json ] || [ ! -f out/m20_validator_burndown_report.json ]; then \
		$(MAKE) m20-descriptor-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m20_pipeline_governance_gate.py --expansion-report out/m20_corpus_expansion_report.json --descriptor-report out/m20_descriptor_evidence_report.json --descriptor-registry-report out/m20_descriptor_registry.json --descriptor-coverage-report out/m20_fdml_coverage_report.json --validator-m17-baseline-report out/m20_validator_expansion_baseline_m17_report.json --validator-m17-current-report out/m20_validator_expansion_m17_report.json --validator-baseline-report out/m20_validator_expansion_baseline_report.json --validator-current-report out/m20_validator_expansion_report.json --burndown-report out/m20_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --report-out out/m20_pipeline_governance.json --label m20-pipeline-governance-live --required-source-dir out/m2_conversion/run1 --required-descriptor-out-dir out/m20_descriptor_evidence/run1 --required-source-text-dir out/acquired_sources --required-source-text-dir out/acquired_sources_nonwiki --required-manifest out/acquired_sources/merged_manifest.json --required-candidate-report out/m15_validator_candidates.json --required-m17-baseline-report out/m20_validator_expansion_baseline_m17_report.json --required-m17-current-report out/m20_validator_expansion_m17_report.json --required-baseline-report out/m20_validator_expansion_baseline_report.json --required-current-report out/m20_validator_expansion_report.json --required-coverage-report out/m20_fdml_coverage_report.json --required-baseline-gap-report out/m19_corpus_expansion_report.json --min-total-files 100 --min-country-coverage-ratio 0.0 --min-region-coverage-ratio 0.0 --min-region-buckets 5 --min-gap-reduction-ratio 0.60 --min-gap-buckets-improved 3 --min-descriptor-files-updated 40 --min-source-grounded-additions 80 --min-descriptor-keys-with-growth 6 --min-descriptor-keys-with-support 18 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 85 --min-files-with-combined-depth 85 --min-expanded-rules 8 --min-source-grounded-applicable 80 --min-reduction-ratio 0.60 --max-failure-file-ratio 0.35 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m21-descriptor-completion-check:
	@set -e; \
	if [ ! -f out/m20_descriptor_evidence_report.json ] || [ ! -f out/m20_fdml_coverage_report.json ]; then \
		$(MAKE) m20-descriptor-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m21_descriptor_completion.py --source-dir out/m20_descriptor_evidence/run1 --baseline-coverage-report out/m20_fdml_coverage_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --out-dir out/m21_descriptor_completion/run1 --report-out out/m21_descriptor_completion_report.json --fdml-bin bin/fdml --label m21-descriptor-completion-live --min-total-files 100 --min-files-updated 12 --min-source-grounded-additions 18 --min-style-depth-gain 4 --min-cultural-depth-gain 4 --min-combined-depth-gain 3 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0 --min-keys-with-growth 8; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m21_descriptor_completion/run1 --report-out out/m21_descriptor_registry.json --coverage-report-out out/m21_fdml_coverage_report.json --label m21-fdml-coverage-live --min-total-files 100 --min-unique-keys 18 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 106 --min-files-with-combined-depth 103

m21-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m21_descriptor_completion_report.json ] || [ ! -f out/m21_fdml_coverage_report.json ]; then \
		$(MAKE) m21-descriptor-completion-check > /dev/null; \
	fi; \
	if [ ! -f out/m15_validator_candidates.json ]; then \
		$(MAKE) m15-discovery-run > /dev/null; \
	fi; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m20_descriptor_evidence/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m21_validator_expansion_baseline_m17_report.json --label m21-validator-expansion-baseline-m17-live --min-total-files 100 --min-rules 35 --max-rules-with-no-applicability 30; \
	python3 scripts/m17_validator_expansion.py --input-dir out/m21_descriptor_completion/run1 --candidate-report out/m15_validator_candidates.json --report-out out/m21_validator_expansion_m17_report.json --label m21-validator-expansion-m17-live --min-total-files 100 --min-rules 35 --max-rules-with-no-applicability 30; \
	python3 scripts/m21_validator_expansion.py --input-dir out/m20_descriptor_evidence/run1 --base-report out/m21_validator_expansion_baseline_m17_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m21_validator_expansion_baseline_report.json --label m21-validator-expansion-baseline-live --min-total-files 100 --min-rules 12 --max-rules-with-no-applicability 30 --min-total-applicable 200; \
	python3 scripts/m21_validator_expansion.py --input-dir out/m21_descriptor_completion/run1 --base-report out/m21_validator_expansion_m17_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m21_validator_expansion_report.json --label m21-validator-expansion-live --min-total-files 100 --min-rules 12 --max-rules-with-no-applicability 30 --min-total-applicable 200; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m21_validator_expansion_baseline_report.json --current-report out/m21_validator_expansion_report.json --report-out out/m21_validator_burndown_report.json --label m21-validator-burndown-live --min-total-files 100 --min-rule-count 12 --min-reduction-ratio 0.05 --max-files-with-fail-ratio 0.90

m21-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m21_descriptor_completion_report.json ] || [ ! -f out/m21_fdml_coverage_report.json ]; then \
		$(MAKE) m21-descriptor-completion-check > /dev/null; \
	fi; \
	if [ ! -f out/m21_validator_expansion_report.json ] || [ ! -f out/m21_validator_burndown_report.json ]; then \
		$(MAKE) m21-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m21_pipeline_governance_gate.py --descriptor-report out/m21_descriptor_completion_report.json --descriptor-registry-report out/m21_descriptor_registry.json --descriptor-coverage-report out/m21_fdml_coverage_report.json --validator-m17-baseline-report out/m21_validator_expansion_baseline_m17_report.json --validator-m17-current-report out/m21_validator_expansion_m17_report.json --validator-baseline-report out/m21_validator_expansion_baseline_report.json --validator-current-report out/m21_validator_expansion_report.json --burndown-report out/m21_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --report-out out/m21_pipeline_governance.json --label m21-pipeline-governance-live --required-source-dir out/m20_descriptor_evidence/run1 --required-descriptor-out-dir out/m21_descriptor_completion/run1 --required-baseline-coverage-report out/m20_fdml_coverage_report.json --required-source-text-dir out/acquired_sources --required-source-text-dir out/acquired_sources_nonwiki --required-candidate-report out/m15_validator_candidates.json --required-m17-baseline-report out/m21_validator_expansion_baseline_m17_report.json --required-m17-current-report out/m21_validator_expansion_m17_report.json --required-baseline-report out/m21_validator_expansion_baseline_report.json --required-current-report out/m21_validator_expansion_report.json --min-total-files 100 --min-descriptor-files-updated 12 --min-source-grounded-additions 18 --min-descriptor-keys-with-growth 8 --min-style-depth-gain 4 --min-cultural-depth-gain 4 --min-combined-depth-gain 3 --min-descriptor-keys-with-support 18 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 106 --min-files-with-combined-depth 103 --min-expanded-rules 12 --min-source-grounded-applicable 200 --min-reduction-ratio 0.05 --max-failure-file-ratio 0.90 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m22-descriptor-uplift-check:
	@set -e; \
	if [ ! -f out/m21_descriptor_completion_report.json ] || [ ! -f out/m21_fdml_coverage_report.json ]; then \
		$(MAKE) m21-descriptor-completion-check > /dev/null; \
	fi; \
	python3 scripts/m22_descriptor_uplift.py --source-dir out/m21_descriptor_completion/run1 --baseline-coverage-report out/m21_fdml_coverage_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --out-dir out/m22_descriptor_uplift/run1 --report-out out/m22_descriptor_uplift_report.json --fdml-bin bin/fdml --label m22-descriptor-uplift-live --min-total-files 100 --min-files-updated 20 --min-source-grounded-additions 40 --max-low-support-ratio 0.45 --min-low-support-keys 6 --min-low-support-keys-with-growth 5 --max-additions-per-file 3 --max-missing-source-text-files 0 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m22_descriptor_uplift/run1 --report-out out/m22_descriptor_registry.json --coverage-report-out out/m22_fdml_coverage_report.json --label m22-fdml-coverage-live --min-total-files 100 --min-unique-keys 18 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 109 --min-files-with-combined-depth 105

m23-descriptor-consolidation-check:
	@set -e; \
	if [ ! -f out/m22_descriptor_uplift_report.json ] || [ ! -f out/m22_fdml_coverage_report.json ]; then \
		$(MAKE) m22-descriptor-uplift-check > /dev/null; \
	fi; \
	python3 scripts/m23_descriptor_consolidation.py --source-dir out/m22_descriptor_uplift/run1 --baseline-coverage-report out/m22_fdml_coverage_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --out-dir out/m23_descriptor_consolidation/run1 --report-out out/m23_descriptor_consolidation_report.json --fdml-bin bin/fdml --label m23-descriptor-consolidation-live --min-total-files 100 --min-files-updated 30 --min-source-grounded-additions 60 --max-low-support-ratio 0.75 --min-low-support-keys 6 --min-low-support-keys-with-growth 6 --min-potential-growth-gap 8 --max-additions-per-file 3 --max-missing-source-text-files 0 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m23_descriptor_consolidation/run1 --report-out out/m23_descriptor_registry.json --coverage-report-out out/m23_fdml_coverage_report.json --label m23-fdml-coverage-live --min-total-files 100 --min-unique-keys 18 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 109 --min-files-with-combined-depth 105

m23-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m23_descriptor_consolidation_report.json ] || [ ! -f out/m23_fdml_coverage_report.json ]; then \
		$(MAKE) m23-descriptor-consolidation-check > /dev/null; \
	fi; \
	if [ ! -f out/m22_validator_expansion_report.json ]; then \
		$(MAKE) m22-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m23_validator_expansion.py --input-dir out/m22_descriptor_uplift/run1 --base-report out/m22_validator_expansion_report.json --descriptor-report out/m23_descriptor_consolidation_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m23_validator_expansion_baseline_report.json --label m23-validator-expansion-baseline-live --min-total-files 100 --min-rules 20 --max-rules-with-no-applicability 30 --min-total-applicable 300; \
	python3 scripts/m23_validator_expansion.py --input-dir out/m23_descriptor_consolidation/run1 --base-report out/m22_validator_expansion_report.json --descriptor-report out/m23_descriptor_consolidation_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m23_validator_expansion_report.json --label m23-validator-expansion-live --min-total-files 100 --min-rules 20 --max-rules-with-no-applicability 30 --min-total-applicable 300; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m23_validator_expansion_baseline_report.json --current-report out/m23_validator_expansion_report.json --report-out out/m23_validator_burndown_report.json --label m23-validator-burndown-live --min-total-files 100 --min-rule-count 20 --min-reduction-ratio 0.10 --max-files-with-fail-ratio 0.70

m23-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m23_descriptor_consolidation_report.json ] || [ ! -f out/m23_fdml_coverage_report.json ]; then \
		$(MAKE) m23-descriptor-consolidation-check > /dev/null; \
	fi; \
	if [ ! -f out/m23_validator_expansion_report.json ] || [ ! -f out/m23_validator_burndown_report.json ]; then \
		$(MAKE) m23-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m23_pipeline_governance_gate.py --descriptor-report out/m23_descriptor_consolidation_report.json --descriptor-registry-report out/m23_descriptor_registry.json --descriptor-coverage-report out/m23_fdml_coverage_report.json --validator-baseline-report out/m23_validator_expansion_baseline_report.json --validator-current-report out/m23_validator_expansion_report.json --burndown-report out/m23_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --report-out out/m23_pipeline_governance.json --label m23-pipeline-governance-live --required-source-dir out/m22_descriptor_uplift/run1 --required-descriptor-out-dir out/m23_descriptor_consolidation/run1 --required-baseline-coverage-report out/m22_fdml_coverage_report.json --required-base-validator-report out/m22_validator_expansion_report.json --required-descriptor-report-path out/m23_descriptor_consolidation_report.json --required-source-text-dir out/acquired_sources --required-source-text-dir out/acquired_sources_nonwiki --required-baseline-report out/m23_validator_expansion_baseline_report.json --required-current-report out/m23_validator_expansion_report.json --min-total-files 100 --min-descriptor-files-updated 30 --min-source-grounded-additions 60 --min-low-support-keys 6 --min-low-support-keys-with-growth 6 --min-descriptor-keys-with-support 18 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 109 --min-files-with-combined-depth 105 --min-expanded-rules 20 --min-alignment-rules 16 --min-coherence-rules 4 --min-source-grounded-applicable 300 --min-coherence-applicable 100 --min-reduction-ratio 0.10 --max-failure-file-ratio 0.70 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m24-residual-failure-closure-check:
	@set -e; \
	if [ ! -f out/m23_validator_expansion_report.json ] || [ ! -f out/m23_descriptor_consolidation_report.json ]; then \
		$(MAKE) m23-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m24_residual_failure_closure.py --source-dir out/m23_descriptor_consolidation/run1 --residual-report out/m23_validator_expansion_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --out-dir out/m24_residual_failure_closure/run1 --report-out out/m24_residual_failure_closure_report.json --fdml-bin bin/fdml --label m24-residual-failure-closure-live --min-total-files 100 --min-targeted-files 5 --min-files-updated 5 --min-source-grounded-additions 6 --max-additions-per-file 3 --max-missing-source-text-files 0 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0; \
	python3 scripts/m23_validator_expansion.py --input-dir out/m23_descriptor_consolidation/run1 --base-report out/m22_validator_expansion_report.json --descriptor-report out/m23_descriptor_consolidation_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m24_validator_expansion_baseline_report.json --label m24-validator-expansion-baseline-live --min-total-files 100 --min-rules 20 --max-rules-with-no-applicability 30 --min-total-applicable 300; \
	python3 scripts/m23_validator_expansion.py --input-dir out/m24_residual_failure_closure/run1 --base-report out/m22_validator_expansion_report.json --descriptor-report out/m23_descriptor_consolidation_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m24_validator_expansion_report.json --label m24-validator-expansion-live --min-total-files 100 --min-rules 20 --max-rules-with-no-applicability 30 --min-total-applicable 300; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m24_validator_expansion_baseline_report.json --current-report out/m24_validator_expansion_report.json --report-out out/m24_validator_burndown_report.json --label m24-validator-burndown-live --min-total-files 100 --min-rule-count 20 --min-reduction-ratio 1.0 --max-files-with-fail-ratio 0.0

m24-descriptor-completion-check:
	@set -e; \
	if [ ! -f out/m24_residual_failure_closure_report.json ] || [ ! -f out/m24_validator_expansion_report.json ]; then \
		$(MAKE) m24-residual-failure-closure-check > /dev/null; \
	fi; \
	python3 scripts/m24_descriptor_completion.py --source-dir out/m24_residual_failure_closure/run1 --residual-closure-report out/m24_residual_failure_closure_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --out-dir out/m24_descriptor_completion/run1 --report-out out/m24_descriptor_completion_report.json --fdml-bin bin/fdml --label m24-descriptor-completion-live --min-total-files 100 --max-low-support-ratio 0.80 --min-low-support-cultural-keys 2 --min-targeted-files 5 --min-files-updated 5 --min-source-grounded-additions 5 --min-low-support-keys-with-growth 2 --max-additions-per-file 3 --min-residual-focus-files 5 --max-missing-source-text-files 0 --min-doctor-pass-rate 1.0 --min-geo-pass-rate 1.0; \
	python3 scripts/m17_descriptor_registry.py --input-dir out/m24_descriptor_completion/run1 --report-out out/m24_descriptor_registry.json --coverage-report-out out/m24_fdml_coverage_report.json --label m24-fdml-coverage-live --min-total-files 100 --min-unique-keys 18 --min-style-keys 8 --min-cultural-keys 6 --min-files-with-cultural-depth 109 --min-files-with-combined-depth 105

m24-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m24_descriptor_completion_report.json ] || [ ! -f out/m24_fdml_coverage_report.json ]; then \
		$(MAKE) m24-descriptor-completion-check > /dev/null; \
	fi; \
	if [ ! -f out/m24_validator_expansion_report.json ] || [ ! -f out/m24_validator_burndown_report.json ]; then \
		$(MAKE) m24-residual-failure-closure-check > /dev/null; \
	fi; \
	python3 scripts/m24_pipeline_governance_gate.py --residual-closure-report out/m24_residual_failure_closure_report.json --descriptor-report out/m24_descriptor_completion_report.json --descriptor-registry-report out/m24_descriptor_registry.json --descriptor-coverage-report out/m24_fdml_coverage_report.json --validator-baseline-report out/m24_validator_expansion_baseline_report.json --validator-current-report out/m24_validator_expansion_report.json --burndown-report out/m24_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --report-out out/m24_pipeline_governance.json --label m24-pipeline-governance-live --required-source-dir out/m23_descriptor_consolidation/run1 --required-residual-out-dir out/m24_residual_failure_closure/run1 --required-descriptor-out-dir out/m24_descriptor_completion/run1 --required-residual-reference-report out/m23_validator_expansion_report.json --required-residual-report-path out/m24_residual_failure_closure_report.json --required-base-validator-report out/m22_validator_expansion_report.json --required-validator-descriptor-report-path out/m23_descriptor_consolidation_report.json --required-source-text-dir out/acquired_sources --required-source-text-dir out/acquired_sources_nonwiki --required-baseline-report out/m24_validator_expansion_baseline_report.json --required-current-report out/m24_validator_expansion_report.json --min-total-files 100 --min-residual-targeted-files 5 --min-residual-files-updated 5 --min-residual-source-grounded-additions 6 --min-descriptor-targeted-files 5 --min-descriptor-files-updated 5 --min-descriptor-source-grounded-additions 5 --min-low-support-cultural-keys 2 --min-low-support-keys-with-growth 2 --min-residual-focus-files 5 --min-descriptor-keys-with-support 18 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 109 --min-files-with-combined-depth 105 --min-expanded-rules 20 --min-alignment-rules 16 --min-coherence-rules 4 --min-source-grounded-applicable 300 --min-coherence-applicable 100 --min-reduction-ratio 1.0 --max-failure-file-ratio 0.0 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

m22-validator-expansion-check:
	@set -e; \
	if [ ! -f out/m22_descriptor_uplift_report.json ] || [ ! -f out/m22_fdml_coverage_report.json ]; then \
		$(MAKE) m22-descriptor-uplift-check > /dev/null; \
	fi; \
	if [ ! -f out/m21_validator_expansion_report.json ]; then \
		$(MAKE) m21-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m22_validator_expansion.py --input-dir out/m21_descriptor_completion/run1 --base-report out/m21_validator_expansion_report.json --descriptor-report out/m22_descriptor_uplift_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m22_validator_expansion_baseline_report.json --label m22-validator-expansion-baseline-live --min-total-files 100 --min-rules 20 --max-rules-with-no-applicability 30 --min-total-applicable 200; \
	python3 scripts/m22_validator_expansion.py --input-dir out/m22_descriptor_uplift/run1 --base-report out/m21_validator_expansion_report.json --descriptor-report out/m22_descriptor_uplift_report.json --source-text-dir out/acquired_sources --source-text-dir out/acquired_sources_nonwiki --report-out out/m22_validator_expansion_report.json --label m22-validator-expansion-live --min-total-files 100 --min-rules 20 --max-rules-with-no-applicability 30 --min-total-applicable 200; \
	python3 scripts/m14_validator_burndown.py --baseline-report out/m22_validator_expansion_baseline_report.json --current-report out/m22_validator_expansion_report.json --report-out out/m22_validator_burndown_report.json --label m22-validator-burndown-live --min-total-files 100 --min-rule-count 20 --min-reduction-ratio 0.30 --max-files-with-fail-ratio 0.70

m22-pipeline-governance-check:
	@set -e; \
	if [ ! -f out/m22_descriptor_uplift_report.json ] || [ ! -f out/m22_fdml_coverage_report.json ]; then \
		$(MAKE) m22-descriptor-uplift-check > /dev/null; \
	fi; \
	if [ ! -f out/m22_validator_expansion_report.json ] || [ ! -f out/m22_validator_burndown_report.json ]; then \
		$(MAKE) m22-validator-expansion-check > /dev/null; \
	fi; \
	python3 scripts/m22_pipeline_governance_gate.py --descriptor-report out/m22_descriptor_uplift_report.json --descriptor-registry-report out/m22_descriptor_registry.json --descriptor-coverage-report out/m22_fdml_coverage_report.json --validator-baseline-report out/m22_validator_expansion_baseline_report.json --validator-current-report out/m22_validator_expansion_report.json --burndown-report out/m22_validator_burndown_report.json --makefile Makefile --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --report-out out/m22_pipeline_governance.json --label m22-pipeline-governance-live --required-source-dir out/m21_descriptor_completion/run1 --required-descriptor-out-dir out/m22_descriptor_uplift/run1 --required-baseline-coverage-report out/m21_fdml_coverage_report.json --required-base-validator-report out/m21_validator_expansion_report.json --required-descriptor-report-path out/m22_descriptor_uplift_report.json --required-source-text-dir out/acquired_sources --required-source-text-dir out/acquired_sources_nonwiki --required-baseline-report out/m22_validator_expansion_baseline_report.json --required-current-report out/m22_validator_expansion_report.json --min-total-files 100 --min-descriptor-files-updated 20 --min-source-grounded-additions 40 --min-low-support-keys 6 --min-low-support-keys-with-growth 5 --min-descriptor-keys-with-support 18 --min-style-keys-with-support 8 --min-culture-keys-with-support 6 --min-files-with-cultural-depth 109 --min-files-with-combined-depth 105 --min-expanded-rules 20 --min-alignment-rules 16 --min-coherence-rules 4 --min-source-grounded-applicable 200 --min-coherence-applicable 100 --min-reduction-ratio 0.30 --max-failure-file-ratio 0.70 --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5

doctor-passrate-check:
	@set -e; \
	python3 scripts/doctor_passrate_gate.py --index src/test/resources/doctor_passrate/pass-index.json --root-dir corpus/valid --min-pass-rate 0.90 --label doctor-passrate-fixture-pass > /dev/null; \
	if python3 scripts/doctor_passrate_gate.py --index src/test/resources/doctor_passrate/fail-index.json --root-dir corpus/invalid --min-pass-rate 0.90 --label doctor-passrate-fixture-fail > /dev/null; then \
		echo "doctor-passrate-check: expected failure for fail-index fixture"; \
		exit 1; \
	fi; \
	if [ -d out/acquired_sources ] && [ -d out/acquired_sources_nonwiki ]; then \
		if [ ! -f out/m2_conversion/run1/index.json ]; then \
			$(MAKE) conversion-batch-check > /dev/null; \
		fi; \
		python3 scripts/doctor_passrate_gate.py --index out/m2_conversion/run1/index.json --root-dir out/m2_conversion/run1 --min-pass-rate 0.90 --report-out out/m2_conversion/run1/doctor_passrate.json --label doctor-passrate-live; \
	else \
		echo "doctor-passrate-check: acquired source dirs not found; fixture checks only."; \
	fi

provenance-coverage-check:
	@set -e; \
	python3 scripts/provenance_coverage_gate.py --index src/test/resources/provenance_coverage/pass-index.json --root-dir . --min-coverage 1.0 --label provenance-coverage-fixture-pass > /dev/null; \
	if python3 scripts/provenance_coverage_gate.py --index src/test/resources/provenance_coverage/fail-index.json --root-dir . --min-coverage 1.0 --label provenance-coverage-fixture-fail > /dev/null; then \
		echo "provenance-coverage-check: expected failure for fail-index fixture"; \
		exit 1; \
	fi; \
	if [ -d out/acquired_sources ] && [ -d out/acquired_sources_nonwiki ]; then \
		if [ ! -f out/m2_conversion/run1/index.json ]; then \
			$(MAKE) conversion-batch-check > /dev/null; \
		fi; \
		python3 scripts/provenance_coverage_gate.py --index out/m2_conversion/run1/index.json --root-dir out/m2_conversion/run1 --min-coverage 1.0 --report-out out/m2_conversion/run1/provenance_coverage.json --label provenance-coverage-live; \
	else \
		echo "provenance-coverage-check: acquired source dirs not found; fixture checks only."; \
	fi

semantic-enrichment-check:
	@set -e; \
	python3 scripts/semantic_enrichment_inventory.py --input-dir corpus/valid_v12 --fdml-bin bin/fdml --target 15 --min-enriched 15 --report-out out/m3_semantic_inventory.json --label m3-semantic-enrichment

semantic-issue-trend-check:
	@set -e; \
	python3 scripts/semantic_issue_trend_gate.py --target corpus/valid_v12 --fdml-bin bin/fdml --baseline analysis/program/m3_issue_baseline.json --report-out out/m3_issue_current.json --label m3-issue-trend

semantic-spec-alignment-check:
	@set -e; \
	python3 scripts/semantic_spec_alignment_gate.py --mapping analysis/program/semantic_issue_code_map.json --report-out out/m3_semantic_spec_alignment.json --label m3-spec-alignment

demo-flow-check:
	@set -e; \
	if [ ! -f out/m11_validator_unified_report.json ]; then \
		$(MAKE) m11-validator-unified-check > /dev/null; \
	fi; \
	python3 scripts/demo_flow_check.py --fdml-bin bin/fdml --make-bin make --work-dir out/demo_flow --report-out out/demo_flow/demo_flow_report.json

final-rehearsal-check:
	@set -e; \
	$(MAKE) ci; \
	if [ -d target/surefire-reports ]; then find target/surefire-reports -type f -delete; fi; \
	mvn test; \
	if [ ! -f out/m2_conversion/run1/index.json ]; then \
		echo "final-rehearsal-check: missing conversion index after ci"; \
		exit 1; \
	fi; \
	python3 scripts/doctor_passrate_gate.py --index out/m2_conversion/run1/index.json --root-dir out/m2_conversion/run1 --min-pass-rate 0.90 --label doctor-passrate-live --report-out out/m2_conversion/run1/doctor_passrate.json; \
	python3 scripts/provenance_coverage_gate.py --index out/m2_conversion/run1/index.json --root-dir out/m2_conversion/run1 --schema schema/provenance.schema.json --schema-validator scripts/validate_json_schema.py --min-coverage 1.0 --label provenance-coverage-live --report-out out/m2_conversion/run1/provenance_coverage.json; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json

m25-hardening-check:
	@set -e; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m25_hardening_check.py --architecture-doc docs/ARCHITECTURE.md --submission-doc docs/SUBMISSION.md --coverage-doc docs/COVERAGE.md --usage-doc docs/USAGE.md --makefile Makefile --goal-state analysis/program/goal_state.json --final-report out/final_rehearsal/report.json --report-out out/m25_hardening_report.json --required-final-label m25-final-product-baseline --min-architecture-lines 60 --min-open-gaps 0

m25-release-governance-check:
	@set -e; \
	python3 scripts/program_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m25_hardening_check.py --architecture-doc docs/ARCHITECTURE.md --submission-doc docs/SUBMISSION.md --coverage-doc docs/COVERAGE.md --usage-doc docs/USAGE.md --makefile Makefile --goal-state analysis/program/goal_state.json --final-report out/final_rehearsal/report.json --report-out out/m25_hardening_report.json --required-active-milestone M25 --required-final-label m25-final-product-baseline --min-architecture-lines 60 --min-open-gaps 0 > /dev/null; \
	python3 scripts/m25_release_governance_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --final-report out/final_rehearsal/report.json --hardening-report out/m25_hardening_report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --makefile Makefile --report-out out/m25_release_governance.json --required-active-milestone M25 --required-final-label m25-final-product-baseline --required-prg-id PRG-253 --required-ci-target m25-release-governance-check --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5 > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null

m26-activation-check:
	@set -e; \
	python3 scripts/m26_activation_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m26_activation_report.json --required-active-milestone M26 --required-previous-milestone M25 --required-activation-work-id PRG-260 --required-next-work-id PRG-261 --min-active-queue 0

m26-polish-baseline-check:
	@set -e; \
	python3 scripts/program_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/m26_activation_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m26_activation_report.json --required-active-milestone M26 --required-previous-milestone M25 --required-activation-work-id PRG-260 --required-next-work-id PRG-261 --min-active-queue 0 > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m25_hardening_check.py --architecture-doc docs/ARCHITECTURE.md --submission-doc docs/SUBMISSION.md --coverage-doc docs/COVERAGE.md --usage-doc docs/USAGE.md --makefile Makefile --goal-state analysis/program/goal_state.json --final-report out/final_rehearsal/report.json --report-out out/m25_hardening_report.json --required-final-label m25-final-product-baseline --min-architecture-lines 60 --min-open-gaps 0 > /dev/null; \
	python3 scripts/m26_polish_baseline.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --activation-report out/m26_activation_report.json --final-report out/final_rehearsal/report.json --hardening-report out/m25_hardening_report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --coverage-doc docs/COVERAGE.md --usage-doc docs/USAGE.md --makefile Makefile --report-out out/m26_polish_baseline_report.json --required-active-milestone M26 --required-previous-milestone M25 --required-work-id PRG-261 --required-next-work-id PRG-262 --required-ci-target m26-polish-baseline-check --min-backlog-items 1

m26-polish-execution-check:
	@set -e; \
	$(MAKE) m26-polish-baseline-check > /dev/null; \
	python3 scripts/m26_polish_execution.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --baseline-report out/m26_polish_baseline_report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --coverage-doc docs/COVERAGE.md --usage-doc docs/USAGE.md --makefile Makefile --gitignore .gitignore --report-out out/m26_polish_execution_report.json --required-active-milestone M26 --required-work-id PRG-262 --required-next-work-id PRG-263 --required-baseline-label m26-production-polish-baseline --required-ci-target m26-polish-execution-check --max-doc-gap-after 0 --max-docs-missing-m26-after 0 --max-pycache-after 0

m26-governance-handoff-check:
	@set -e; \
	$(MAKE) m26-polish-execution-check > /dev/null; \
	python3 scripts/program_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m26_handoff_governance_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --baseline-report out/m26_polish_baseline_report.json --execution-report out/m26_polish_execution_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --coverage-doc docs/COVERAGE.md --usage-doc docs/USAGE.md --makefile Makefile --report-out out/m26_handoff_governance_report.json --required-active-milestone M26 --required-previous-work-id PRG-262 --required-work-id PRG-263 --required-baseline-label m26-production-polish-baseline --required-execution-label m26-polish-execution-live --required-final-label m25-final-product-baseline --required-ci-target m26-governance-handoff-check --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5 > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null

m26-archive-check:
	@set -e; \
	python3 scripts/m26_archive_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --makefile Makefile --report-out out/m26_archive_gate_report.json --required-milestone-id M26 --required-work-id PRG-260 --required-work-id PRG-261 --required-work-id PRG-262 --required-work-id PRG-263 --required-work-id PRG-264 --required-artifact out/m26_activation_report.json --required-artifact out/m26_polish_baseline_report.json --required-artifact out/m26_polish_execution_report.json --required-artifact out/m26_handoff_governance_report.json --required-ci-target m26-archive-check

m27-cloud-workflow-check:
	@set -e; \
	python3 scripts/m27_cloud_workflow_check.py --usage-doc docs/USAGE.md --submission-doc docs/SUBMISSION.md --step-map analysis/program/step_execution_map.json --makefile Makefile --report-out out/m27_cloud_workflow_report.json --required-work-id PRG-266 --required-next-work-id PRG-267 --required-ci-target m27-cloud-workflow-check

m27-assessor-package-check:
	@set -e; \
	python3 scripts/m27_assessor_package_check.py --walkthrough-doc docs/ASSESSOR_WALKTHROUGH.md --submission-doc docs/SUBMISSION.md --program-plan-doc docs/PROGRAM_PLAN.md --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --makefile Makefile --report-out out/m27_assessor_package_report.json --required-work-id PRG-267 --required-ci-target m27-assessor-package-check

m27-archive-check:
	@set -e; \
	python3 scripts/m26_archive_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --makefile Makefile --report-out out/m27_archive_gate_report.json --required-milestone-id M27 --required-work-id PRG-265 --required-work-id PRG-266 --required-work-id PRG-267 --required-artifact out/m27_cloud_workflow_report.json --required-artifact out/m27_assessor_package_report.json --required-ci-target m27-archive-check

m28-activation-check:
	@set -e; \
	python3 scripts/m28_activation_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m28_activation_report.json --required-active-milestone M28 --required-previous-milestone M27 --required-activation-work-id PRG-270 --required-next-work-id PRG-271 --min-active-queue 0

m28-narrative-baseline-check:
	@set -e; \
	python3 scripts/m28_website_narrative_baseline.py --demo-doc docs/DEMO.html --search-doc docs/search.html --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --program-plan-doc docs/PROGRAM_PLAN.md --goal-state analysis/program/goal_state.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --makefile Makefile --report-out out/m28_narrative_baseline_report.json --required-work-id PRG-271 --required-next-work-id PRG-272 --required-ci-target m28-narrative-baseline-check --min-backlog-items 0 --min-active-queue-count 0

m28-narrative-execution-check:
	@set -e; \
	$(MAKE) site-check > /dev/null; \
	python3 scripts/m28_narrative_execution_check.py --demo-doc docs/DEMO.html --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --program-plan-doc docs/PROGRAM_PLAN.md --baseline-report out/m28_narrative_baseline_report.json --step-map analysis/program/step_execution_map.json --makefile Makefile --report-out out/m28_narrative_execution_report.json --required-work-id PRG-272 --required-next-work-id PRG-273 --required-ci-target m28-narrative-execution-check

m28-governance-handoff-check:
	@set -e; \
	python3 scripts/m28_governance_handoff_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --activation-report out/m28_activation_report.json --baseline-report out/m28_narrative_baseline_report.json --execution-report out/m28_narrative_execution_report.json --demo-doc docs/DEMO.html --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --program-plan-doc docs/PROGRAM_PLAN.md --step-map analysis/program/step_execution_map.json --makefile Makefile --build-index-script scripts/build_index.sh --site-smoke-script scripts/site_smoke.py --report-out out/m28_governance_handoff_report.json --required-active-milestone M28 --required-previous-work-id PRG-272 --required-work-id PRG-273 --required-ci-target m28-governance-handoff-check; \
	$(MAKE) site-check > /dev/null

m28-archive-check:
	@set -e; \
	python3 scripts/m26_archive_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --makefile Makefile --report-out out/m28_archive_gate_report.json --required-milestone-id M28 --required-work-id PRG-270 --required-work-id PRG-271 --required-work-id PRG-272 --required-work-id PRG-273 --required-work-id PRG-274 --required-artifact out/m28_activation_report.json --required-artifact out/m28_narrative_baseline_report.json --required-artifact out/m28_narrative_execution_report.json --required-artifact out/m28_governance_handoff_report.json --required-ci-target m28-archive-check

m29-archive-check:
	@set -e; \
	python3 scripts/m26_archive_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --makefile Makefile --report-out out/m29_archive_gate_report.json --required-milestone-id M29 --required-work-id PRG-275 --required-work-id PRG-276 --required-work-id PRG-277 --required-work-id PRG-278 --required-artifact out/m29_activation_report.json --required-artifact out/m29_release_baseline_report.json --required-artifact out/m29_delivery_stabilization_report.json --required-artifact out/m29_governance_freeze_report.json --required-ci-target m29-archive-check

m30-activation-check:
	@set -e; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/m30_activation_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m30_activation_report.json --required-active-milestone M30 --required-previous-milestone M29 --required-activation-work-id PRG-279 --required-next-work-id PRG-280 --min-active-queue 0

m30-repo-baseline-check:
	@set -e; \
	mkdir -p out; \
	if [ ! -f out/m30_repo_execution_report.json ]; then \
		printf '{"schemaVersion":"1","label":"m30-repo-execution-bootstrap","ok":false}\n' > out/m30_repo_execution_report.json; \
	fi; \
	if [ ! -f out/m30_governance_report.json ]; then \
		printf '{"schemaVersion":"1","label":"m30-governance-bootstrap","ok":false}\n' > out/m30_governance_report.json; \
	fi; \
	$(MAKE) m30-activation-check > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m30_repo_baseline.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --activation-report out/m30_activation_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --usage-doc docs/USAGE.md --submission-doc docs/SUBMISSION.md --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m30_repo_baseline_report.json --required-active-milestone M30 --required-previous-milestone M29 --required-work-id PRG-280 --required-next-work-id PRG-281 --required-governance-work-id PRG-282 --required-ci-target m30-repo-baseline-check --min-backlog-items 1

m30-repo-execution-check:
	@set -e; \
	mkdir -p out; \
	if [ ! -f out/m30_repo_execution_report.json ]; then \
		printf '{"schemaVersion":"1","label":"m30-repo-execution-bootstrap","ok":false}\n' > out/m30_repo_execution_report.json; \
	fi; \
	if [ ! -f out/m30_governance_report.json ]; then \
		printf '{"schemaVersion":"1","label":"m30-governance-bootstrap","ok":false}\n' > out/m30_governance_report.json; \
	fi; \
	$(MAKE) m30-repo-baseline-check > /dev/null; \
	python3 scripts/program_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m30_repo_execution_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --baseline-report out/m30_repo_baseline_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --makefile Makefile --gitignore .gitignore --report-out out/m30_repo_execution_report.json --required-active-milestone M30 --required-work-id PRG-281 --required-next-work-id PRG-282 --required-baseline-label m30-repo-baseline-live --required-final-label m25-final-product-baseline --required-ci-target m30-repo-execution-check --max-queued-gap-after 2 --max-open-queue-after 1 --max-dirty-delta 6; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null

m30-governance-check:
	@set -e; \
	mkdir -p out; \
	if [ ! -f out/m30_governance_report.json ]; then \
		printf '{"schemaVersion":"1","label":"m30-governance-bootstrap","ok":false}\n' > out/m30_governance_report.json; \
	fi; \
	$(MAKE) m30-repo-execution-check > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m30_governance_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --activation-report out/m30_activation_report.json --baseline-report out/m30_repo_baseline_report.json --execution-report out/m30_repo_execution_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --demo-doc docs/DEMO.html --makefile Makefile --build-index-script scripts/build_index.sh --site-smoke-script scripts/site_smoke.py --report-out out/m30_governance_report.json --required-active-milestone M30 --required-previous-work-id PRG-281 --required-work-id PRG-282 --required-baseline-label m30-repo-baseline-live --required-execution-label m30-repo-execution-live --required-final-label m25-final-product-baseline --required-ci-target m30-governance-check --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5; \
	$(MAKE) site-check > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null

m30-archive-check:
	@set -e; \
	python3 scripts/m26_archive_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --makefile Makefile --report-out out/m30_archive_gate_report.json --required-milestone-id M30 --required-work-id PRG-279 --required-work-id PRG-280 --required-work-id PRG-281 --required-work-id PRG-282 --required-artifact out/m30_activation_report.json --required-artifact out/m30_repo_baseline_report.json --required-artifact out/m30_repo_execution_report.json --required-artifact out/m30_governance_report.json --required-ci-target m30-archive-check

m31-activation-check:
	@set -e; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/m31_activation_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m31_activation_report.json --required-active-milestone M31 --required-previous-milestone M30 --required-activation-work-id PRG-283 --min-active-queue 0

m29-activation-check:
	@set -e; \
	python3 scripts/m29_activation_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m29_activation_report.json --required-active-milestone M29 --required-previous-milestone M28 --required-activation-work-id PRG-275 --required-next-work-id PRG-276 --min-active-queue 0

m29-release-baseline-check:
	@set -e; \
	python3 scripts/m29_release_workflow_baseline.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --activation-report out/m29_activation_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --usage-doc docs/USAGE.md --submission-doc docs/SUBMISSION.md --program-plan-doc docs/PROGRAM_PLAN.md --makefile Makefile --report-out out/m29_release_baseline_report.json --required-active-milestone M29 --required-previous-milestone M28 --required-work-id PRG-276 --required-next-work-id PRG-277 --required-governance-work-id PRG-278 --required-ci-target m29-release-baseline-check --min-backlog-items 0

m29-delivery-stabilization-check:
	@set -e; \
	$(MAKE) m29-release-baseline-check > /dev/null; \
	python3 scripts/program_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/m29_delivery_stabilization_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --baseline-report out/m29_release_baseline_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --makefile Makefile --gitignore .gitignore --report-out out/m29_delivery_stabilization_report.json --required-active-milestone M29 --required-work-id PRG-277 --required-next-work-id PRG-278 --required-baseline-label m29-release-workflow-baseline-live --required-final-label m25-final-product-baseline --required-ci-target m29-delivery-stabilization-check --max-queued-gap-after 3 --max-open-queue-after 1 > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	python3 scripts/m29_delivery_stabilization_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --baseline-report out/m29_release_baseline_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --makefile Makefile --gitignore .gitignore --report-out out/m29_delivery_stabilization_report.json --required-active-milestone M29 --required-work-id PRG-277 --required-next-work-id PRG-278 --required-baseline-label m29-release-workflow-baseline-live --required-final-label m25-final-product-baseline --required-ci-target m29-delivery-stabilization-check --max-queued-gap-after 2 --max-open-queue-after 1; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null

m29-governance-freeze-check:
	@set -e; \
	mkdir -p out; \
	if [ ! -f out/m29_governance_freeze_report.json ]; then \
		printf '{"schemaVersion":"1","label":"m29-governance-freeze-bootstrap","ok":false}\n' > out/m29_governance_freeze_report.json; \
	fi; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null; \
	$(MAKE) m29-release-baseline-check > /dev/null; \
	python3 scripts/m29_delivery_stabilization_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --baseline-report out/m29_release_baseline_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --makefile Makefile --gitignore .gitignore --report-out out/m29_delivery_stabilization_report.json --required-active-milestone M29 --required-work-id PRG-277 --required-next-work-id PRG-278 --required-baseline-label m29-release-workflow-baseline-live --required-final-label m25-final-product-baseline --required-ci-target m29-delivery-stabilization-check --max-queued-gap-after 2 --max-open-queue-after 1 > /dev/null; \
	python3 scripts/m29_governance_freeze_check.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --activation-report out/m29_activation_report.json --baseline-report out/m29_release_baseline_report.json --execution-report out/m29_delivery_stabilization_report.json --final-report out/final_rehearsal/report.json --step-map analysis/program/step_execution_map.json --program-plan-doc docs/PROGRAM_PLAN.md --submission-doc docs/SUBMISSION.md --usage-doc docs/USAGE.md --demo-doc docs/DEMO.html --makefile Makefile --build-index-script scripts/build_index.sh --site-smoke-script scripts/site_smoke.py --report-out out/m29_governance_freeze_report.json --required-active-milestone M29 --required-previous-work-id PRG-277 --required-work-id PRG-278 --required-baseline-label m29-release-workflow-baseline-live --required-execution-label m29-delivery-stabilization-live --required-final-label m25-final-product-baseline --required-ci-target m29-governance-freeze-check --min-decision-count 5 --min-assumption-count 5 --min-risk-count 5; \
	$(MAKE) site-check > /dev/null; \
	python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json > /dev/null; \
	python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json > /dev/null; \
	python3 scripts/final_rehearsal_check.py --report-out out/final_rehearsal/report.json > /dev/null

site-manifest-check:
	@set -e; \
	$(MAKE) html; \
	python3 scripts/site_manifest.py site --out out/site_manifest.json; \
	if ! diff -u docs/manifest.expected.json out/site_manifest.json; then \
		echo "Site manifest drift detected. If intentional, regenerate with:"; \
		echo "  make html && python3 scripts/site_manifest.py site --out docs/manifest.expected.json"; \
		exit 1; \
	fi

pages-sync:
	@./scripts/sync_pages_snapshot.sh site pages

pages-check:
	@set -e; \
	python3 scripts/site_smoke.py --site-dir pages; \
	python3 scripts/site_manifest.py pages --out out/pages_manifest.json; \
	if ! diff -u docs/manifest.expected.json out/pages_manifest.json; then \
		echo "Pages snapshot drift detected. Refresh with:"; \
		echo "  make html && make pages-sync"; \
		exit 1; \
	fi

coverage:
	@python3 scripts/coverage_report.py

api-check:
	@python3 scripts/api_healthcheck.py --env-file .env

acquire-sources:
	@rm -rf out/acquired_sources
	@mkdir -p out/acquired_sources
	@$(MAKE) merge-acquire-manifests > /dev/null
	@python3 scripts/acquire_sources.py --manifest out/acquired_sources/merged_manifest.json --out-dir out/acquired_sources
	@python3 scripts/license_policy_gate.py --index out/acquired_sources/index.json --label acquire-sources-license
	@python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources --report out/acquired_sources/review.json
	@python3 scripts/review_passrate_gate.py --report out/acquired_sources/review.json --min-pass-rate 0.95 --label acquire-sources

merge-acquire-manifests:
	@python3 scripts/merge_source_manifests.py \
		--manifest analysis/sources/web_seed_manifest.json \
		--manifest analysis/sources/m5_expansion_seed_manifest.json \
		--manifest analysis/sources/m20_expansion_seed_manifest.json \
		--out out/acquired_sources/merged_manifest.json

acquire-sources-nonwiki:
	@python3 scripts/acquire_sources.py --manifest analysis/sources/non_wikipedia_public_domain_manifest.json --out-dir out/acquired_sources_nonwiki
	@python3 scripts/license_policy_gate.py --index out/acquired_sources_nonwiki/index.json --label acquire-sources-nonwiki-license
	@python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources_nonwiki --report out/acquired_sources_nonwiki/review.json
	@python3 scripts/review_passrate_gate.py --report out/acquired_sources_nonwiki/review.json --min-pass-rate 0.95 --label acquire-sources-nonwiki

review-sources:
	@python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources --report out/acquired_sources/review.json
	@python3 scripts/review_passrate_gate.py --report out/acquired_sources/review.json --min-pass-rate 0.95 --label review-sources

review-passrate-check:
	@set -e; \
	python3 scripts/review_passrate_gate.py --report src/test/resources/review_passrate/pass-95.json --min-pass-rate 0.95 --label review-passrate-fixture > /dev/null; \
	if python3 scripts/review_passrate_gate.py --report src/test/resources/review_passrate/fail-95.json --min-pass-rate 0.95 --label review-passrate-fixture > /dev/null; then \
		echo "review-passrate-check: expected failure for fail-95 fixture"; \
		exit 1; \
	fi; \
	args=""; \
	if [ -f out/acquired_sources/review.json ]; then args="$$args --report out/acquired_sources/review.json"; fi; \
	if [ -f out/acquired_sources_nonwiki/review.json ]; then args="$$args --report out/acquired_sources_nonwiki/review.json"; fi; \
	if [ -n "$$args" ]; then \
		python3 scripts/review_passrate_gate.py $$args --min-pass-rate 0.95 --label review-passrate-live; \
	else \
		echo "review-passrate-check: no local acquisition review reports found; fixture checks only."; \
	fi

license-policy-check:
	@set -e; \
	python3 scripts/license_policy_gate.py --index src/test/resources/license_policy/pass-index.json --label license-policy-fixture > /dev/null; \
	if python3 scripts/license_policy_gate.py --index src/test/resources/license_policy/fail-index.json --label license-policy-fixture > /dev/null; then \
		echo "license-policy-check: expected failure for fail-index fixture"; \
		exit 1; \
	fi; \
	args=""; \
	if [ -f out/acquired_sources/index.json ]; then args="$$args --index out/acquired_sources/index.json"; fi; \
	if [ -f out/acquired_sources_nonwiki/index.json ]; then args="$$args --index out/acquired_sources_nonwiki/index.json"; fi; \
	if [ -n "$$args" ]; then \
		python3 scripts/license_policy_gate.py $$args --label license-policy-live; \
	else \
		echo "license-policy-check: no local acquisition index files found; fixture checks only."; \
	fi

goal-state-update:
	@python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json

goal-state-check:
	@python3 scripts/update_goal_state.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --approval analysis/program/approval_report.json --out analysis/program/goal_state.json --check

program-check:
	@python3 scripts/program_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv
	@$(MAKE) goal-state-update > /dev/null

task-approval-check:
	@python3 scripts/task_approval_gate.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --report analysis/program/approval_report.json
	@$(MAKE) goal-state-update > /dev/null

program-autopilot:
	@python3 scripts/program_autopilot.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --map analysis/program/step_execution_map.json --max-items 10

program-autopilot-dry-run:
	@python3 scripts/program_autopilot.py --plan analysis/program/plan.json --work analysis/program/work_items.csv --goal-state analysis/program/goal_state.json --map analysis/program/step_execution_map.json --max-items 10 --dry-run

site-check:
	@$(MAKE) html
	@python3 scripts/site_smoke.py

ci: program-check task-approval-check goal-state-check review-passrate-check license-policy-check doctor-passrate-check provenance-coverage-check full-description-quality-check m8-geometry-governance-check m9-full-description-uplift-check m10-discovery-governance-check m11-pipeline-governance-check m13-pipeline-governance-check m15-pipeline-governance-check m16-pipeline-governance-check m17-pipeline-governance-check m18-pipeline-governance-check m19-pipeline-governance-check m20-pipeline-governance-check m21-pipeline-governance-check m22-pipeline-governance-check m23-pipeline-governance-check m24-pipeline-governance-check m25-hardening-check m26-archive-check m27-cloud-workflow-check m27-archive-check m28-archive-check m29-archive-check m30-archive-check m31-activation-check semantic-enrichment-check semantic-issue-trend-check semantic-spec-alignment-check check-schematron validate-valid validate-invalid export-json-check ingest-check provenance-check site-manifest-check site-check pages-check

clean:
	rm -rf out site

serve:
	cd site && python3 -m http.server 8000

report:
	cd docs/progress-report && latexmk -pdf -silent progress_2025-10-28_v2.tex
