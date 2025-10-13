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

ci: validate
