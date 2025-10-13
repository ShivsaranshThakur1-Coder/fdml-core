.DEFAULT_GOAL := help

help:
	@echo "Targets: help, build, validate, validate-sch, validate-all, render, test, docs, ci"

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

test:
	mvn -q test

docs: build
	./scripts/gen_examples.sh
	@echo "Docs generated in docs/examples/ (open docs/examples/index.html)"

ci: build
	@echo "✓ XSD: valid corpus should pass"
	java -jar target/fdml-core.jar validate corpus/valid
	@echo "✓ Schematron: valid corpus should pass"
	java -jar target/fdml-core.jar validate-sch corpus/valid
	@echo "✓ XSD: invalid corpus should fail (expected non-zero)"
	@if java -jar target/fdml-core.jar validate corpus/invalid; then echo "Expected invalid corpus to fail XSD, but it passed"; exit 1; else echo "Invalid corpus correctly failed XSD (at least one file)"; fi
	@echo "✓ Schematron: invalid corpus should fail (expected non-zero)"
	@if java -jar target/fdml-core.jar validate-sch corpus/invalid; then echo "Expected invalid corpus to fail Schematron, but it passed"; exit 1; else echo "Invalid corpus correctly failed Schematron"; fi
	@echo "✓ Tests"
	mvn -q test
