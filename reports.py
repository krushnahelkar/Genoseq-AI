"""CSV and JSON serialization for Genoseq AI pipeline results."""
import csv
import json
import zipfile
from io import BytesIO
from io import StringIO


def result_as_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


def result_as_csv(result):
    """Flatten numeric feature rows into a spreadsheet-friendly CSV."""
    output = StringIO(newline="")
    feature_rows = result.get("feature_rows", [])
    if not feature_rows:
        writer = csv.writer(output)
        writer.writerow(["file_type", "record_id", "feature", "value"])
        return output.getvalue()

    columns = sorted({key for row in feature_rows for key in row})
    fieldnames = ["file_type", "filename"] + columns
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in feature_rows:
        writer.writerow({
            "file_type": result.get("kind", ""),
            "filename": result.get("filename", ""),
            **row,
        })
    return output.getvalue()


def charts_as_zip(charts):
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, formats in charts.items():
            for extension, data in formats.items():
                archive.writestr(f"{name}.{extension}", data)
    return output.getvalue()


def result_as_pdf(result, charts):
    """Build a concise PDF summary with the generated charts appended."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    output = BytesIO()
    with PdfPages(output) as pdf:
        figure, axis = plt.subplots(figsize=(8.27, 11.69))
        axis.axis("off")
        lines = [
            "Genoseq AI Analysis Report", "", f"File: {result.get('filename', '')}",
            f"Input type: {result.get('kind', '').upper()}", "", "Summary",
        ]
        if result["kind"] == "fasta":
            lines.append(f"Sequences: {result['record_count']}")
            for record in result["records"]:
                if record["record_type"] == "Protein":
                    lines.append(
                        f"{record['id']}: protein, {record['protein_length']} aa; "
                        f"molecular weight {record['molecular_weight']:.2f} Da; "
                        f"theoretical pI {record['isoelectric_point']:.2f}"
                    )
                else:
                    lines.append(
                        f"{record['id']}: {record['stats']['Length']} bp; "
                        f"GC {record['stats']['GC_percent']:.2f}%; ORFs {record['orf_count']}"
                    )
        elif result["kind"] == "fastq":
            lines.extend((f"Reads: {result['total_reads']}", f"Bases: {result['total_bases']}",
                          f"Mean read length: {result['mean_read_length']:.2f} bp",
                          f"Mean quality: {result['mean_quality']:.2f}",
                          f"Q20 / Q30: {result['q20_percent']:.2f}% / {result['q30_percent']:.2f}%"))
        else:
            lines.extend((f"Variant records: {result['total_variants']}",
                          f"Alternate alleles: {result['total_alt_alleles']}",
                          f"SNPs: {result['snp_count']}; insertions: {result['insertion_count']}; "
                          f"deletions: {result['deletion_count']}",
                          f"Passing records: {result['passing_records']}",
                          "This report provides technical summaries, not clinical interpretation."))
        axis.text(.08, .94, "\n".join(lines), va="top", fontsize=11, wrap=True)
        pdf.savefig(figure, bbox_inches="tight")
        plt.close(figure)
        for name, formats in charts.items():
            image = plt.imread(BytesIO(formats["png"]))
            figure, axis = plt.subplots(figsize=(10, 6))
            axis.imshow(image)
            axis.axis("off")
            axis.set_title(name.replace("_", " ").title())
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)
    return output.getvalue()
