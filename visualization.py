"""Create compact PNG and SVG charts for analysis results."""
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _chart(draw):
    figure, axis = plt.subplots(figsize=(7, 4))
    draw(axis)
    figure.tight_layout()
    outputs = {}
    for file_type in ("png", "svg"):
        buffer = BytesIO()
        figure.savefig(buffer, format=file_type, dpi=140, bbox_inches="tight", facecolor="white")
        outputs[file_type] = buffer.getvalue()
    plt.close(figure)
    return outputs


def build_charts(result):
    """Return named charts, each containing PNG and SVG bytes."""
    charts = {}
    if result["kind"] == "fasta":
        dna_records = [row for row in result["records"] if row["record_type"] == "DNA/RNA"]
        protein_records = [row for row in result["records"] if row["record_type"] == "Protein"]
        if dna_records:
            counts = {base: sum(row["stats"].get(f"{base}_count", 0) for row in dna_records)
                      for base in "ATGCN"}
            charts["nucleotide_composition"] = _chart(lambda ax: (
                ax.bar(list(counts), list(counts.values()), color=["#21845b", "#3776b8", "#ef9c32", "#8656aa", "#aab3ae"]),
                ax.set(title="Nucleotide composition", ylabel="Bases"), ax.grid(axis="y", alpha=.2)))
            labels = [row["id"] for row in dna_records]
            gc_values = [row["stats"].get("GC_percent", 0) for row in dna_records]
            charts["gc_content"] = _chart(lambda ax: (
                ax.bar(labels, gc_values, color="#21845b"),
                ax.set(title="GC content by sequence", ylabel="GC content (%)"),
                ax.tick_params(axis="x", rotation=25), ax.grid(axis="y", alpha=.2)))
        if protein_records:
            totals = {}
            for row in protein_records:
                for amino_acid, percent in row["amino_acid_composition"].items():
                    totals[amino_acid] = totals.get(amino_acid, 0) + percent
            top = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:15]
            charts["amino_acid_composition"] = _chart(lambda ax: (
                ax.bar([item[0] for item in top], [item[1] for item in top], color="#8656aa"),
                ax.set(title="Amino-acid composition", ylabel="Summed composition (%)")))
    elif result["kind"] == "fastq":
        quality = result.get("quality_by_position", [])
        if quality:
            charts["quality_by_position"] = _chart(lambda ax: (
                ax.plot(range(1, len(quality) + 1), quality, color="#8656aa", linewidth=2),
                ax.axhline(20, color="#ef9c32", linestyle="--", label="Q20"),
                ax.axhline(30, color="#21845b", linestyle=":", label="Q30"),
                ax.set(title="Mean base quality by read position", xlabel="Read position", ylabel="Mean Phred score"),
                ax.legend(), ax.grid(alpha=.2)))
        distribution = result.get("read_length_distribution", {})
        if distribution:
            charts["read_length_distribution"] = _chart(lambda ax: (
                ax.bar([str(key) for key in distribution], list(distribution.values()), color="#3776b8"),
                ax.set(title="Read length distribution", xlabel="Read length (bp)", ylabel="Read count")))
    else:
        counts = {"SNP": result["snp_count"], "Insertions": result["insertion_count"],
                  "Deletions": result["deletion_count"], "MNV": result["mnv_count"],
                  "Other": result["complex_count"]}
        charts["variant_types"] = _chart(lambda ax: (
            ax.bar(list(counts), list(counts.values()), color="#3776b8"),
            ax.set(title="Variant allele types", ylabel="Alternate alleles"),
            ax.tick_params(axis="x", rotation=18), ax.grid(axis="y", alpha=.2)))
        contigs = result["chromosome_distribution"]
        charts["variants_by_contig"] = _chart(lambda ax: (
            ax.bar(list(contigs), list(contigs.values()), color="#21845b"),
            ax.set(title="Variant records by contig", ylabel="Variant records"),
            ax.tick_params(axis="x", rotation=25)))
    return charts
