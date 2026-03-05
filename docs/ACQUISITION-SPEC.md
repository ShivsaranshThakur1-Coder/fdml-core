# Source Acquisition Spec (Web -> FDML)

## Goal
Scale FDML coverage using a legally safe, deterministic pipeline:

1. Curate allowed-source manifests.
2. Acquire text from the web with license + attribution metadata.
3. Feed acquired text through `fdml ingest`.
4. Validate generated FDML with `fdml doctor --strict`.

This is the expansion path for broader folk-dance modeling.

## License Policy
Only ingest sources with explicit reuse rights.

Allowed-by-default licenses in `scripts/acquire_sources.py`:

- `Public Domain`
- `CC0 1.0`
- `CC BY 4.0`
- `CC BY-SA 4.0`

If a source is not clearly licensed, do not add it to the manifest.

## Manifest Contract
Manifest path (seed set):

- `analysis/sources/web_seed_manifest.json`
- `analysis/sources/m5_expansion_seed_manifest.json`
- `analysis/sources/m20_expansion_seed_manifest.json`
- `analysis/sources/non_wikipedia_public_domain_manifest.json` (non-Wikipedia, Project Gutenberg)

Schema (per entry under `sources[]`):

- `id`: stable ASCII id (used for output filename)
- `title`: human-readable title
- `url`: fetch URL
- `parser`: `mediawiki_extract` or `plain_text`
- `license`: explicit license string
- `attribution`: required attribution text
- `language`: language code (informational)

## Acquisition Command
Acquire the curated seed set:

```bash
python3 scripts/acquire_sources.py \
  --manifest analysis/sources/web_seed_manifest.json \
  --out-dir out/acquired_sources
```

Acquire non-Wikipedia public-domain set:

```bash
python3 scripts/acquire_sources.py \
  --manifest analysis/sources/non_wikipedia_public_domain_manifest.json \
  --out-dir out/acquired_sources_nonwiki
```

Outputs:

- `out/acquired_sources/<id>.txt` (normalized text + metadata header)
- `out/acquired_sources/index.json` (deterministic fetch index with hashes)
- `out/acquired_sources/review.json` (quality-gate report)

For the non-Wikipedia set:

- `out/acquired_sources_nonwiki/<id>.txt`
- `out/acquired_sources_nonwiki/index.json`
- `out/acquired_sources_nonwiki/review.json`

## Review Gate (blocks bad extracts)
Run the quality gate:

```bash
python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources
python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources_nonwiki
```

The gate fails non-zero if a file does not meet minimum quality checks:

- required metadata header keys are present
- header `source_sha256` matches body
- minimum chars and words
- minimum alphabetic ratio
- maximum control-character ratio
- maximum noisy-line ratio
- maximum repeated symbol runs

`make acquire-sources` and `make acquire-sources-nonwiki` run this review automatically before ingest.

License policy is enforced by `scripts/license_policy_gate.py` (wired into both make targets and CI).

## Ingest Command (Batch)
Convert acquired text into FDML stubs:

```bash
mkdir -p out/acquired_fdml
for txt in out/acquired_sources/*.txt; do
  stem="$(basename "$txt" .txt)"
  ./bin/fdml ingest \
    --source "$txt" \
    --out "out/acquired_fdml/${stem}.fdml.xml" \
    --title "$stem" \
    --meter 4/4 \
    --tempo 112 \
    --profile v1-basic
done
```

Run strict validation:

```bash
./bin/fdml doctor out/acquired_fdml --strict
```

## Seed Batch Included
The seed manifest currently includes 12 openly licensed folk-dance pages via the MediaWiki API:

- Mayim Mayim
- Dabke
- Hora (dance)
- Kolo (dance)
- Kalamatianos
- Syrtos
- Tarantella
- Csardas
- Polka
- Mazurka
- Sirtaki
- Schuhplattler

## Non-Wikipedia Seed Batch Included
`analysis/sources/non_wikipedia_public_domain_manifest.json` includes 5 Project Gutenberg public-domain dance sources:

- English Folk-Song and Dance
- The Morris Book, Part 1
- Jamaican Song and Story
- The Dance (Historic Illustrations of Dancing)
- Orchesography, or, the Art of Dancing

## Governance Rules
1. Every source must have license + attribution in the manifest.
2. Keep `id` stable once added (for reproducible history).
3. Prefer deterministic API endpoints over ad-hoc scraping.
4. Store source hashes in acquisition index for drift detection.
5. Treat acquisition as data ingestion, not as a bypass of site terms.
