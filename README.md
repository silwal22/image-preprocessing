# Vision-based PAN Card Extractor

This project builds a lightweight vision pipeline for extracting fields from dummy PAN cards using Google Gemini with multimodal JSON extraction.

## Setup

1. Create a Python 3.11+ virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
3. Set environment variables:
   ```bash
   export GEMINI_MODEL="gemini-2.0-flash"
   export GEMINI_API_KEY="your_api_key_here"
   ```

## File order

1. Generate dummy PAN cards:
   ```bash
   python make_dummy_cards.py
   ```
2. Validate the generated ground truth:
   ```bash
   python validate_ground_truth.py
   ```
3. Run extraction on a single sample:
   ```bash
   python extractor.py samples/clean_01.jpg --steps rotate brightness
   ```
4. Run the full evaluation suite:
   ```bash
   python evaluate.py
   ```

## Notes

- All sample cards are synthetic and intended for local testing only.
- The model name and API key are loaded from environment variables; they are not hardcoded.
- The extractor gracefully handles missing OCR dependencies and API failures.
- Evaluation output is written to `results.csv` and `quality_report.md`.
