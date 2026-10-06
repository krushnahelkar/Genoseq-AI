"""File detection and first-pass analysis for Genoseq AI uploads."""
from collections import Counter
from io import StringIO
from pathlib import Path

from Bio import SeqIO
from Bio.SeqUtils.ProtParam import ProteinAnalysis

from fasta_reader import analyze_sequence, protein_analysis


FASTA_EXTENSIONS = {".fa", ".fasta", ".fna", ".fas", ".faa"}
FASTQ_EXTENSIONS = {".fq", ".fastq"}
VCF_EXTENSIONS = {".vcf"}
TEXT_EXTENSIONS = {".txt"}


def detect_format(filename, text):
    """Detect the supported format from its extension or recognizable header."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in FASTA_EXTENSIONS:
        return "fasta"
    if suffix in FASTQ_EXTENSIONS:
        return "fastq"
    if suffix in VCF_EXTENSIONS:
        return "vcf"
    if suffix not in TEXT_EXTENSIONS and suffix:
        raise ValueError("Unsupported file type. Upload DNA/protein FASTA (.fa/.fasta/.faa), FASTQ (.fq/.fastq), or VCF (.vcf).")

    first_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not first_lines:
        raise ValueError("The uploaded file is empty.")
    if any(line.startswith("##fileformat=VCF") for line in first_lines[:10]) or any(
        line.startswith("#CHROM\tPOS\tID\tREF\tALT") for line in first_lines
    ):
        return "vcf"
    if first_lines[0].startswith(">"):
        return "fasta"
    if first_lines[0].startswith("@"):
        return "fastq"
    raise ValueError("Could not identify the file. Use a FASTA, FASTQ, or VCF file with the correct extension/header.")


def analyze_fasta(text):
    try:
        records = list(SeqIO.parse(StringIO(text), "fasta-pearson"))
    except Exception as exc:
        raise ValueError(f"Could not parse the FASTA file: {exc}") from exc
    if not records:
        raise ValueError("No FASTA records found. Each sequence needs a header line beginning with >.")

    results = []
    nucleotide_alphabet = set("ACGTUNRYSWKMBDHV")
    protein_alphabet = set("ACDEFGHIKLMNPQRSTVWY")
    amino_acid_names = {
        "A": "Alanine", "C": "Cysteine", "D": "Aspartic acid", "E": "Glutamic acid",
        "F": "Phenylalanine", "G": "Glycine", "H": "Histidine", "I": "Isoleucine",
        "K": "Lysine", "L": "Leucine", "M": "Methionine", "N": "Asparagine",
        "P": "Proline", "Q": "Glutamine", "R": "Arginine", "S": "Serine",
        "T": "Threonine", "V": "Valine", "W": "Tryptophan", "Y": "Tyrosine",
    }
    acidic_residues = set("DE")
    basic_residues = set("KRH")
    hydrophobic_residues = set("ACFILMVWY")
    for record in records:
        sequence = str(record.seq).upper()
        base = {
            "id": record.id,
            "description": record.description if record.description != record.id else "",
        }
        if set(sequence) <= nucleotide_alphabet:
            analysis = analyze_sequence(sequence)
            results.append({
                **base,
                "record_type": "DNA/RNA",
                "stats": analysis["Statistics"],
                "gc_skew": analysis["Skew"]["GC_skew"],
                "at_skew": analysis["Skew"]["AT_skew"],
                "valid": analysis["Validation"]["Valid_DNA"],
                "invalid_bases": analysis["Validation"]["Invalid_Bases"],
                "orf_count": analysis["ORF_Count"],
                "orfs": analysis["ORFs"],
                "translation_frames": analysis["Six_Frame_Translation"],
                "translation_truncated": analysis["Translation_Truncated"],
                "melting_temperature_c": analysis["Melting_Temperature_C"],
            })
            continue

        # Protein FASTA often uses .faa, but .fa/.fasta files may contain
        # proteins too. Remove alignment gaps and a terminal stop marker.
        protein_sequence = sequence.replace("-", "").replace(".", "").rstrip("*")
        invalid_residues = sorted(set(protein_sequence) - protein_alphabet)
        if not protein_sequence or invalid_residues:
            invalid = ", ".join(invalid_residues) if invalid_residues else "no residues"
            raise ValueError(
                f"FASTA record {record.id!r} contains unsupported protein residue(s): {invalid}. "
                "Use standard one-letter amino-acid codes."
            )
        protein = ProteinAnalysis(protein_sequence)
        composition = protein.count_amino_acids()
        protein_properties = protein_analysis(protein_sequence)
        composition_detail = []
        for aa in sorted(amino_acid_names):
            if aa in acidic_residues:
                group = "acidic"
            elif aa in basic_residues:
                group = "basic"
            elif aa in hydrophobic_residues:
                group = "hydrophobic"
            else:
                group = "polar"
            count = composition.get(aa, 0)
            composition_detail.append({
                "code": aa,
                "name": amino_acid_names[aa],
                "count": count,
                "percent": round(count / len(protein_sequence) * 100, 2),
                "group": group,
            })
        acidic_detail = [item for item in composition_detail if item["group"] == "acidic"]
        basic_detail = [item for item in composition_detail if item["group"] == "basic"]
        hydrophobic_detail = [item for item in composition_detail if item["group"] == "hydrophobic"]
        results.append({
            **base,
            "record_type": "Protein",
            "valid": True,
            "protein_length": len(protein_sequence),
            "molecular_weight": protein_properties["Molecular_Weight"],
            "isoelectric_point": protein_properties["Isoelectric_Point"],
            "gravy": protein_properties["GRAVY"],
            "acidic_percent": protein_properties["Acidic_Percent"],
            "basic_percent": protein_properties["Basic_Percent"],
            "hydrophobic_percent": protein_properties["Hydrophobic_Percent"],
            "acidic_residues": acidic_detail,
            "basic_residues": basic_detail,
            "hydrophobic_residues": hydrophobic_detail,
            "amino_acid_detail": composition_detail,
            "melting_temperature_c": None,
            "melting_temperature_status": "not_available",
            "melting_temperature_note": (
                "Protein Tm needs a validated protein-specific predictor or an experimental measurement; "
                "the DNA nearest-neighbor calculation does not apply to amino-acid sequences."
            ),
            "amino_acid_composition": {
                aa: round(count / len(protein_sequence) * 100, 2)
                for aa, count in sorted(composition.items())
            },
        })
    return {"kind": "fasta", "record_count": len(results), "records": results}


def analyze_fastq(text):
    try:
        records = list(SeqIO.parse(StringIO(text), "fastq"))
    except Exception as exc:
        raise ValueError(f"Could not parse the FASTQ file. Check its sequence and quality lines: {exc}") from exc
    if not records:
        raise ValueError("No FASTQ reads found. FASTQ records must include sequence and quality lines.")

    read_lengths = []
    quality_values = []
    total_bases = 0
    gc_bases = 0
    q20_bases = 0
    q30_bases = 0
    quality_by_position = []

    for record in records:
        sequence = str(record.seq).upper()
        qualities = record.letter_annotations.get("phred_quality")
        if qualities is None or len(qualities) != len(sequence):
            raise ValueError(f"Read {record.id!r} is missing matching per-base quality scores.")

        read_lengths.append(len(sequence))
        total_bases += len(sequence)
        gc_bases += sequence.count("G") + sequence.count("C")
        quality_values.extend(qualities)
        q20_bases += sum(score >= 20 for score in qualities)
        q30_bases += sum(score >= 30 for score in qualities)

        for position, score in enumerate(qualities):
            if position == len(quality_by_position):
                quality_by_position.append([0, 0])
            quality_by_position[position][0] += score
            quality_by_position[position][1] += 1

    mean_quality = sum(quality_values) / len(quality_values) if quality_values else 0.0
    return {
        "kind": "fastq",
        "total_reads": len(records),
        "total_bases": total_bases,
        "mean_read_length": total_bases / len(records) if records else 0.0,
        "min_read_length": min(read_lengths) if read_lengths else 0,
        "max_read_length": max(read_lengths) if read_lengths else 0,
        "read_length_distribution": dict(sorted(Counter(read_lengths).items())),
        "gc_percent": gc_bases / total_bases * 100 if total_bases else 0.0,
        "mean_quality": mean_quality,
        "q20_percent": q20_bases / total_bases * 100 if total_bases else 0.0,
        "q30_percent": q30_bases / total_bases * 100 if total_bases else 0.0,
        "quality_by_position": [
            round(total / count, 2) for total, count in quality_by_position
        ],
    }


def analyze_vcf(text):
    header_columns = None
    variants = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            header_columns = line.lstrip("#").split("\t")
            required = ["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
            if header_columns[:8] != required:
                raise ValueError("The VCF header columns are not in the expected order.")
            continue
        if line.startswith("#"):
            continue
        if header_columns is None:
            raise ValueError("VCF header is missing. Expected a #CHROM header before variant rows.")

        columns = line.split("\t")
        if len(columns) < 8:
            raise ValueError(f"VCF line {line_number} has fewer than 8 tab-separated columns.")
        try:
            position = int(columns[1])
        except ValueError as exc:
            raise ValueError(f"VCF line {line_number} has a non-numeric POS value.") from exc
        if position < 1:
            raise ValueError(f"VCF line {line_number} has POS less than 1.")

        ref = columns[3].upper()
        alts = [allele.upper() for allele in columns[4].split(",") if allele and allele != "."]
        if not ref or ref == "." or not alts:
            raise ValueError(f"VCF line {line_number} must include REF and ALT alleles.")
        qual = None if columns[5] == "." else float_or_none(columns[5])
        variants.append({
            "chrom": columns[0],
            "pos": position,
            "ref": ref,
            "alts": alts,
            "qual": qual,
            "filter": columns[6],
        })

    if header_columns is None:
        raise ValueError("This does not look like a VCF file: the #CHROM header is missing.")
    if not variants:
        raise ValueError("The VCF header is valid, but it contains no variant rows.")

    counts = Counter()
    chromosomes = Counter()
    qualities = []
    passing_records = 0

    for variant in variants:
        chromosomes[variant["chrom"]] += 1
        if variant["filter"] in {"PASS", "."}:
            passing_records += 1
        if variant["qual"] is not None:
            qualities.append(variant["qual"])
        for alt in variant["alts"]:
            counts["alleles"] += 1
            if len(variant["ref"]) == 1 and len(alt) == 1 and alt not in {"*"}:
                counts["snps"] += 1
            elif len(alt) > len(variant["ref"]):
                counts["insertions"] += 1
            elif len(alt) < len(variant["ref"]):
                counts["deletions"] += 1
            elif len(alt) > 1 and len(alt) == len(variant["ref"]):
                counts["mnvs"] += 1
            else:
                counts["complex"] += 1

    sample_columns = header_columns[9:]
    return {
        "kind": "vcf",
        "total_variants": len(variants),
        "total_alt_alleles": counts["alleles"],
        "snp_count": counts["snps"],
        "indel_count": counts["insertions"] + counts["deletions"],
        "insertion_count": counts["insertions"],
        "deletion_count": counts["deletions"],
        "mnv_count": counts["mnvs"],
        "complex_count": counts["complex"],
        "passing_records": passing_records,
        "mean_quality": sum(qualities) / len(qualities) if qualities else None,
        "chromosome_distribution": dict(sorted(chromosomes.items())),
        "sample_count": len(sample_columns),
        "samples": sample_columns,
    }


def float_or_none(value):
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError("VCF QUAL values must be numeric or .") from exc


def analyze_upload(filename, raw_bytes):
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Upload a UTF-8 text file, not a compressed or binary file.") from exc

    file_kind = detect_format(filename, text)
    if file_kind == "fasta":
        result = analyze_fasta(text)
    elif file_kind == "fastq":
        result = analyze_fastq(text)
    else:
        result = analyze_vcf(text)
    result["filename"] = filename
    return result
