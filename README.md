# GenoSeq AI

GenoSeq AI is a Flask web app for first-pass FASTA, FASTQ, and VCF summaries. It is a learning prototype, not a clinical diagnosis or pathogenicity classifier.

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

- DNA/RNA FASTA: named A/T/G/C/N counts and percentages, GC/AT content and skew, estimated melting temperature for eligible sequences, translation in six reading frames, and complete ATG-to-stop ORFs scanned in all six frames (minimum 90 bp).
- Protein FASTA: molecular weight, theoretical pI, GRAVY hydropathy, acidic/basic/hydrophobic residue percentages, interactive per-amino-acid composition, and an explicit protein-Tm status.
- FASTQ: read and base counts, length summaries, GC, mean quality, Q20/Q30, and per-position quality.
- VCF: variant and allele counts, basic variant classes, filters, quality, samples, and contigs.

Sequence composition charts, amino-acid filters, translation-frame tabs, ORF-frame summaries, FASTQ quality curves, and VCF bars are interactive in the browser. Report exports remain available.

DNA Tm is estimated at 50 mM Na+ for DNA/RNA sequences from 8 to 10,000 bases. Unambiguous sequences use nearest-neighbor thermodynamics; sequences containing IUPAC ambiguity codes use an empirical GC-content estimate weighted by each code's possible bases. This is an estimate, not a lab measurement. Protein Tm is a separate property: it requires a protein-specific validated predictor or an experiment. No protein-Tm model is bundled, so the report states this instead of silently omitting the field or displaying a made-up number. Translation is previewed for the first 30,000 bases per strand. Disease prediction is not active: no labeled training dataset or validated prediction model is included. The application does not determine whether a variant causes disease.
