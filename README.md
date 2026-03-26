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
- Match origin (`index`, `ocr`, `fuzzy`, `semantic`)
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

Optional dependencies for semantic reranking and transformer OCR:

```bash
pip install -r requirements-ml.txt
```

Kraken OCR note:

- Kraken is typically used on Linux/macOS with Python 3.9-3.11.
- On Windows or newer Python versions, install may fail with `No matching distribution found`.
- Recommended workaround: run Kraken in WSL (Ubuntu) with Python 3.11, then use `--ocr-backend kraken`.

Install Tesseract OCR engine (required for real OCR from images):

- Windows: install "Tesseract OCR" and ensure `tesseract.exe` is in `PATH`
- Linux: install package `tesseract-ocr` (and `tesseract-ocr-ita` for Italian)
- macOS: `brew install tesseract tesseract-lang`

### Windows quick setup (PowerShell)

```powershell
winget install UB-Mannheim.TesseractOCR
```

Typical install path:

`C:\Program Files\Tesseract-OCR\tesseract.exe`

Verify installation:

```powershell
tesseract --version
```

If command is not found, add it to PATH for the current shell:

```powershell
$env:Path += ';C:\Program Files\Tesseract-OCR'
tesseract --version
```

Persist PATH for future shells:

```powershell
setx PATH "$env:PATH;C:\Program Files\Tesseract-OCR"
```

If `ita.traineddata` / `lat.traineddata` are missing and you cannot write to `C:\Program Files`, use a project-local `tessdata` folder:

```powershell
$td = "$PWD\tessdata"
New-Item -ItemType Directory -Force -Path $td | Out-Null

Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_fast/raw/main/ita.traineddata -OutFile "$td\ita.traineddata"
Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_fast/raw/main/lat.traineddata -OutFile "$td\lat.traineddata"

$env:TESSDATA_PREFIX = $td
```

Persist `TESSDATA_PREFIX` for future shells:

```powershell
setx TESSDATA_PREFIX "$PWD\tessdata"
```

## Project layout

```text
main.py
requirements.txt
requirements-ml.txt
config.example.json
config.kraken.example.json
input_images/
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
    factory.py
    kraken_backend.py
    tesseract_backend.py
    trocr_backend.py
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
python main.py --query-file queries.txt
python main.py --query "Mosca" --input-folder ".\\input_images" --semantic-search --semantic-threshold 42
python main.py --query "Mosca" --input-folder ".\\input_images" --ocr-backend trocr --ocr-model "microsoft/trocr-large-handwritten"
```

If you run without `--url` and without `--input-folder`, the tool uses `./input_images` by default and creates it if missing.

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

### Semantic rerank (optional)

```bash
python main.py --input-folder ".\\input_images" --query "Mosca" --semantic-search --semantic-threshold 42
```

Notes:
- Requires packages from `requirements-ml.txt`; without them the tool logs a warning and continues with fuzzy-only matching.
- Semantic score is reported in JSON output (`semantic_score`) and in table output (`Semantic` column).

### OCR backend selection

```bash
# Hybrid OCR (recommended first): TrOCR + automatic Tesseract fallback
python main.py --input-folder ".\\input_images" --query "Mosca" --ocr-backend hybrid --ocr-model "microsoft/trocr-large-handwritten"

# Transformer handwritten OCR
python main.py --input-folder ".\\input_images" --query "Mosca" --ocr-backend trocr --ocr-model "microsoft/trocr-large-handwritten"

# Kraken OCR (requires a local .mlmodel path)
python main.py --input-folder ".\\input_images" --query "Mosca" --ocr-backend kraken --ocr-model ".\\models\\kraken\\italian_htr.mlmodel"

# Kraken using a dedicated config file
python main.py --config config.kraken.example.json

# Pure tesseract OCR
python main.py --input-folder ".\\input_images" --query "Mosca" --ocr-backend tesseract --ocr-model "ita+lat+eng"
```

### OCR debug mode (see exactly what OCR reads)

```bash
python main.py --input-folder ".\\input_images" --query "Mosca" --debug-ocr-text --verbose
```

This prints OCR previews to terminal and dumps full OCR text per page to `.cache/ocr_debug/`.
Use `--debug-ocr-dir <path>` to choose another output folder.

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
5. Extract text via selected OCR backend (`hybrid`, `tesseract`, `trocr`, or `kraken`)
6. Normalize and fuzzy-match all queries
7. (Optional) semantic rerank/filter of fuzzy candidates
8. Score candidates and rank by confidence
9. Export as table/JSON/(optional) CSV

## OCR backend in v1

Supported OCR backends:

- `hybrid` (default): `trocr` first, then automatic `tesseract` fallback on weak output
- `tesseract`: robust baseline with multi-pass preprocessing
- `trocr`: Transformer-based handwritten OCR via Hugging Face model (`--ocr-model`)
- `kraken`: HTR engine using a local recognition model file (`--ocr-model` path to `.mlmodel`)

Notes:

- `tesseract` auto-detects `tesseract.exe` on Windows (`C:\Program Files\Tesseract-OCR\tesseract.exe`) if PATH is missing
- `tesseract` auto-uses local `./tessdata` when `TESSDATA_PREFIX` is not set
- `trocr` requires optional ML dependencies and first-run model download
- `trocr` now falls back to line segmentation when full-page OCR is too short/empty
- `kraken` requires optional ML dependencies and a local recognition model path

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
3. Run:

```bash
python main.py --input-folder "C:\\records\\registry_1868" --query-file queries.txt --output-format json
```

Default local folder shortcut:

```bash
python main.py --query-file queries.txt --output-format json
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
