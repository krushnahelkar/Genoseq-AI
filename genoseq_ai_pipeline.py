"""End-to-end IndiGen processing pipeline used by the web application."""
from file_analysis import analyze_upload
from ml_model import extract_features, model_readiness


def run_analysis_pipeline(filename, raw_bytes):
    """Detect, validate, analyze, and prepare model features for one upload."""
    # analyze_upload detects the format and fully parses it; malformed inputs
    # raise ValueError before a result is returned.
    result = analyze_upload(filename, raw_bytes)
    features = extract_features(result)

    if result["kind"] == "fasta":
        invalid_records = sum(not record["valid"] for record in result["records"])
        validation_message = (
            f"Parsed {result['record_count']} FASTA sequence(s); "
            f"{invalid_records} sequence(s) contain unsupported DNA letters."
        )
        protein_records = sum(record.get("record_type") == "Protein" for record in result["records"])
        dna_records = result["record_count"] - protein_records
        analysis_message = (
            f"Analyzed {dna_records} DNA/RNA and {protein_records} protein record(s), "
            "including nucleotide or amino-acid properties as appropriate."
        )
    elif result["kind"] == "fastq":
        validation_message = "Parsed FASTQ sequence and per-base quality values."
        analysis_message = "Calculated read counts, length distribution, GC content, and Q20/Q30 metrics."
    else:
        validation_message = "Parsed VCF header and validated variant positions and allele fields."
        analysis_message = "Calculated variant-type, filter, quality, sample, and contig summaries."

    result["workflow"] = [
        {"name": "File detection and validation", "status": "complete", "details": f"Detected {result['kind'].upper()} format. {validation_message}"},
        {"name": "Format-specific analysis", "status": "complete", "details": analysis_message},
        {"name": "Feature engineering", "status": "complete", "details": f"Prepared {len(features)} numeric feature row(s)."},
        {"name": "Prediction", "status": "not_ready", "details": model_readiness()["message"]},
        {"name": "Results", "status": "complete", "details": "Structured results are ready for display or report export."},
    ]
    result["feature_rows"] = features
    result["model"] = model_readiness()
    return result
