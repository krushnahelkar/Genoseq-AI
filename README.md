# Genoseq AI

Genoseq AI is a Flask web app for first-pass FASTA, FASTQ, and VCF summaries. It is a learning prototype, not a clinical diagnosis or pathogenicity classifier.

## Run locally

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in a browser on the same computer.

## Deploy on Render

The `render.yaml` Blueprint is configured for this project root. Connect a Git repository containing these files to Render and create a Blueprint instance from `render.yaml`. Render uses:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT`

The deployed web service provides an internet-accessible `onrender.com` address. Uploads are limited to 25 MB and processed in memory by the web upload route.

## Supported summaries

- FASTA: DNA/RNA composition, GC/AT content, ORFs, or protein composition, estimated molecular weight, and theoretical pI.
- FASTQ: read and base counts, length summaries, GC, mean quality, Q20/Q30, and per-position quality.
- VCF: variant and allele counts, basic variant classes, filters, quality, samples, and contigs.

The current app does not match sequences against external protein databases or determine whether a variant causes disease.
