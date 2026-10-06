# Genoseq AI project status

## Workflow implemented
1. File detection and parsing for text FASTA, FASTQ, and VCF uploads.
2. Format-specific validation and summary analysis.
3. Numeric feature extraction for future ML work.
4. Structured workflow status displayed by the web app.
5. CSV and JSON downloads from the upload form.
6. JSON API endpoint at `/api/analyze` for a multipart upload using field `sequence_file`.
7. Per-format PNG/SVG visual summaries, a chart ZIP download, and a PDF report with charts.
8. Upload error handling: invalid files show a page-level message; unexpected failures are logged server-side, and API errors return JSON without exposing exception details.

## Current analysis coverage
- FASTA: DNA/RNA sequence length, nucleotide counts and percentages, GC/AT content and skew, validity, and ORFs; protein length, amino-acid composition, molecular weight, and theoretical pI.
- FASTQ: total reads and bases, read length distribution, GC content, mean Phred quality, Q20/Q30 percentages, and mean quality by read position.
- VCF: variant records and alternate alleles, basic SNP/indel/MNV grouping, PASS count, mean QUAL, sample names, and contig distribution.

## Remaining workflow-chart work
- Adapter-content analysis, richer quality visualizations, motifs, and protein-focused FASTA analysis.
- Interactive charts, cross-file comparison, and a downloadable variant-prioritization list.
- Reference-backed VCF annotation. Pathogenic/benign classification must not be guessed from variant type alone.
- Train and evaluate a model only after a labeled dataset and a clear prediction target are selected.
- Public hosting. The app currently runs locally; a hosting service and a connected Git repository are needed for a shareable URL.

## Run locally
From the project folder: `python -m pip install -r requirements.txt`, then `python app.py`, then open `http://127.0.0.1:5000`.
