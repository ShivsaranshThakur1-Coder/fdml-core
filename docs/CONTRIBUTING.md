# Contributing

## Before you open a PR
1. Base branch: `main`.
2. Use short feature/fix branches, e.g. `feat/schematron-rules`, `fix/email-regex`.
3. Commit style: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`).

## Quality gates
Run `make ci` locally. It will:
- build the shaded jar,
- validate the valid corpus by XSD + Schematron,
- assert the invalid corpus fails,
- run tests (including snapshot tests).

PRs must be green on CI (GitHub Actions).

## Coding notes
- Java 17, Maven build, shaded jar.
- XSD for structure; Schematron for business rules; XSLT (Saxon-HE) for renders.
- Keep examples small but representative in `corpus/`.
