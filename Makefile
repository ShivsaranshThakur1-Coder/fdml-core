.DEFAULT_GOAL := help

help:
	@echo "Targets: help, build, validate, validate-sch, validate-all, render, test, ci"

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

ci: build
	@echo "✓ XSD: valid corpus should pass"
	java -jar target/fdml-core.jar validate corpus/valid
	@echo "✓ Schematron: valid corpus should pass"
	java -jar target/fdml-core.jar validate-sch corpus/valid
	@echo "✓ XSD: invalid corpus should fail (expected non-zero)"
	@if java -jar target/fdml-core.jar validate corpus/invalid; then echo "Expected invalid corpus to fail, but it passed"; exit 1; else echo "Invalid corpus correctly failed"; fi
	@echo "✓ Tests"
	mvn -q test
