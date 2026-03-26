# Italian Civil Registry Name Finder (POC)

A small, Windows-friendly Python project to search names/keywords in Italian historical civil registry records, including handwritten image-based registries (for example pages viewed on Portale Antenati).

> This is a **best-effort** tool. Handwritten historical records are difficult for generic OCR and can produce false positives/false negatives.

## What this tool does

Given one or more sources and a list of queries, it tries to report likely page numbers where those queries appear:

- Source URL or local folder
- Page number
- Confidence score (0-100)
- Text snippet (if available)
- Backend used
- Match origin (`index`, `ocr`, `fuzzy`)
- Warnings and errors

## Key principles

- Polite, non-aggressive network behavior
- Never crawl beyond provided URLs
- Request throttling and retries with backoff
- Caching to reduce repeated requests
- Graceful behavior when remote access is blocked
- **Local-folder mode is first-class** and often the most practical workflow
- OCR backend is pluggable for future handwritten-text systems

## Requirements

- Python 3.11+
- Works on Windows, macOS, Linux

Install dependencies:

```bash
pip install -r requirements.txt
```

## Project layout

```text
main.py
requirements.txt
config.example.json
src/
  cli.py
  config.py
  models.py
  logging_utils.py
  cache.py
  fetchers/
    antenati_fetcher.py
    local_folder_fetcher.py
  extractors/
    page_discovery.py
    image_loader.py
  ocr/
    base.py
    simple_backend.py
  matching/
    normalize.py
    fuzzy_match.py
    scorer.py
  reporting/
    console_report.py
    json_report.py
    csv_report.py
tests/
```

## CLI usage

### Basic examples

```bash
python main.py --url "https://antenati.cultura.gov.it/ark:/12657/an_ua334892/wRv8rGx" --query "Giovanni"
python main.py --config config.example.json
python main.py --url "https://antenati.cultura.gov.it/..." --query-file queries.txt --aggressiveness balanced
python main.py --input-folder "C:\\records\\lessona_1868" --query-file queries.txt
```

### Multiple URLs and direct queries

```bash
python main.py \
  --urls "https://antenati.cultura.gov.it/ark:/.../abc" "https://antenati.cultura.gov.it/ark:/.../def" \
  --query "Giovanni" \
  --aggressiveness gentle \
  --output-format table
```

### JSON output + CSV export

```bash
python main.py --config config.example.json --output-format json --csv-output out.csv
```

### Dry run (no remote fetches)

```bash
python main.py --url "https://antenati.cultura.gov.it/ark:/..." --query "Bourne" --dry-run
```

## Input methods

You can provide inputs via:

1. CLI flags
2. JSON config file

CLI values override JSON values when both are present.

## Aggressiveness profiles

All profiles are polite and limited to the provided URL(s).

- `gentle`
  - Slower requests
  - Metadata/page discovery first
  - Lower remote page cap
- `balanced`
  - Moderate throttling
  - General best-effort defaults
- `deep`
  - More exhaustive inspection (still respectful)
  - Higher remote page cap and retries

## How search works

1. Parse inputs
2. Detect source type (remote URL vs local folder)
3. Discover pages
4. Load images
5. Extract text via OCR backend (default placeholder sidecar backend)
6. Normalize and fuzzy-match all queries
7. Score candidates and rank by confidence
8. Export as table/JSON/(optional) CSV

## OCR backend in v1

The default `SimpleOCRBackend` is intentionally lightweight:

- It reads a sidecar `.txt` file if available next to each image (`0001.jpg` -> `0001.txt`)
- If no sidecar file exists, it returns empty text with low confidence

This is by design so you can:

- Run quick local experiments with manual transcriptions
- Plug in a better handwritten OCR/HTR backend later without changing the pipeline

## Confidence scoring

Current formula (see `src/matching/scorer.py`):

- Base: `0.6 * fuzzy_score + 0.3 * (ocr_confidence * 100)`
- Bonus: `+8` for exact match
- Bonus: `+6` for index-like page hint
- Penalty: `-10` for weak fuzzy score (`<55`)
- Final score clamped to `0..100`

## Local-folder mode (recommended workflow)

Because viewer automation can be blocked, local mode is a primary path:

1. User exports/downloads page images manually
2. Put images in a folder
3. (Optional but useful) add sidecar text files with the same basename
4. Run:

```bash
python main.py --input-folder "C:\\records\\registry_1868" --query-file queries.txt --output-format json
```

Output structure is the same as remote mode.

## Remote mode limitations and fallback behavior

If direct page/image access is blocked (403/429/etc), the tool will:

- Stop aggressive activity
- Emit explicit warnings
- Suggest the semi-manual local-folder workflow

It never silently hides these failures.

## Respectful-use note

Use this tool responsibly:

- Only on URLs you are allowed to access
- Do not bypass access restrictions
- Keep request frequency low
- Prefer cached/local workflows when possible

## Running tests

```bash
pytest -q
```

## Optional GUI

GUI is intentionally not core in v1 to keep architecture simple and robust.

TODO idea:

- Small Tkinter window with URL(s), query list, aggressiveness dropdown, start button, and results panel.

## Future improvements

- Add specialized handwritten Italian OCR/HTR backend (Transkribus/API or custom model)
- Add better index-page detection via layout heuristics
- Add optional image preprocessing pipeline for faded handwriting
- Add per-query alias dictionaries and phonetic matching
- Add persisted run history and incremental resume
- Add minimal Tkinter GUI wrapper for non-CLI users
