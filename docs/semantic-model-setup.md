# Semantic Model Setup

## Goal
- Add a lightweight multilingual semantic layer for listing filtering.
- Keep it CPU-friendly for an Intel i5-6500T with 16 GB RAM.

## Ubuntu Packages
- `python3-venv`
- `python3-dev`
- `build-essential`
- `git`
- `libgomp1`

## Python Packages
- Core runtime: `requirements.txt`
- ML extras: `requirements-ml.txt`
- `torch`
- `sentence-transformers`
- `fasttext-wheel`
- `scikit-learn`

## Suggested Install
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential git libgomp1
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-ml.txt
```

## Model Choices
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` for multilingual embeddings.
- `intfloat/multilingual-e5-small` if you want a slightly stronger small embedding model.
- `fastText lid.176.ftz` for language detection when you want explicit language codes.

## Notes
- The current code ships with a heuristic fallback so the bot keeps working before the real model is plugged in.
- When you add the real model, prefer quantized CPU execution or OpenVINO on this server class.

## Retraining Loop
- Review listings in the dashboard and save human feedback labels.
- Export dataset with `python -m scripts.cli export-feedback-dataset`.
- Train the semantic classifier offline from the exported JSONL.
- Replace the heuristic backend with the trained model only after validation.
