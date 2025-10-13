.DEFAULT_GOAL := help

help:
	@echo "Targets: help, build, validate, validate-sch, validate-all, render, export-pdf, index, lint, lint-strict, init-demo, doctor, pdfs, docs, test, ci"

build:
	mvn -q -DskipTests package

validate: build
	java -jar target/fdml-core.jar validate corpus/valid

validate-sch: build
	java -jar target/fdml-core.jar validate-sch corpus/valid

validate-all: build
	java -jar target/fdml-core.jar validate-all corpus/valid

render: build
	java -jar target/fdml-core.jar render corpus/valid/example-01.fdml.xml --out out/example-01.html

export-pdf: build
	java -jar target/fdml-core.jar export-pdf corpus/valid/example-01.fdml.xml --out out/example-01.pdf

index: build
	java -jar target/fdml-core.jar index corpus/valid --out out/index.json
	@echo "Index written to out/index.json"

lint: build
	java -jar target/fdml-core.jar lint corpus/valid

lint-strict: build
	java -jar target/fdml-core.jar lint corpus/valid --strict

init-demo: build
	java -jar target/fdml-core.jar init corpus/valid/example-08-init.fdml.xml --title "Demo Init" --dance "Demo" --meter 3/4 --tempo 96 --figure-id f-demo --figure-name "Demo Figure" --formation circle

doctor: build
	java -jar target/fdml-core.jar doctor corpus

pdfs: build
	./scripts/gen_examples.sh

docs: build
	./scripts/gen_examples.sh
	@echo "Docs generated in docs/examples/ and PDFs in docs/pdfs/"

test:
	mvn -q test

ci: build
	java -jar target/fdml-core.jar validate corpus/valid
	java -jar target/fdml-core.jar validate-sch corpus/valid
	set +e; java -jar target/fdml-core.jar validate corpus/invalid; s=$$?; if [ $$s -eq 0 ]; then echo "Expected invalid corpus to fail XSD, but it passed"; exit 1; else echo "Invalid corpus correctly failed XSD"; fi
	set +e; java -jar target/fdml-core.jar validate-sch corpus/invalid; s=$$?; if [ $$s -eq 0 ]; then echo "Expected invalid corpus to fail Schematron, but it passed"; exit 1; else echo "Invalid corpus correctly failed Schematron"; fi
	mvn -q test
