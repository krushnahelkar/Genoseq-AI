import csv
from collections import Counter
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils import MeltingTemp
from Bio.SeqUtils.ProtParam import ProteinAnalysis


# The FASTA file is expected at: <project folder>\data\test.fasta
FASTA_FILE = Path(__file__).resolve().parent / "data" / "test.fasta"
MIN_ORF_LENGTH = 90
MAX_TRANSLATION_NT = 30000
MAX_DNA_TM_NT = 10000
IUPAC_DNA_BASES = set("ACGTRYSWKMBDHVN")


def clean_sequence(sequence):
    """Uppercase a sequence and remove spaces, digits, and punctuation."""
    return "".join(base for base in str(sequence).upper() if base.isalpha())


def sequence_statistics(sequence):
    # Treat RNA uracil as thymine for the requested A/T/G/C/N summary.
    sequence = clean_sequence(sequence).replace("U", "T")
    counts = Counter(sequence)
    length = len(sequence)

    a_count = counts.get("A", 0)
    t_count = counts.get("T", 0)
    g_count = counts.get("G", 0)
    c_count = counts.get("C", 0)
    n_count = counts.get("N", 0)

    def percentage(count):
        return (count / length * 100) if length else 0.0

    return {
        "Length": length,
        "A_count": a_count,
        "T_count": t_count,
        "G_count": g_count,
        "C_count": c_count,
        "N_count": n_count,
        "A_percent": percentage(a_count),
        "T_percent": percentage(t_count),
        "G_percent": percentage(g_count),
        "C_percent": percentage(c_count),
        "GC_percent": percentage(g_count + c_count),
        "AT_percent": percentage(a_count + t_count),
        "N_percent": percentage(n_count),
    }


def calculate_skew(sequence):
    sequence = clean_sequence(sequence)
    g_count = sequence.count("G")
    c_count = sequence.count("C")
    a_count = sequence.count("A")
    t_count = sequence.count("T")

    gc_total = g_count + c_count
    at_total = a_count + t_count

    return {
        "GC_skew": (g_count - c_count) / gc_total if gc_total else 0.0,
        "AT_skew": (a_count - t_count) / at_total if at_total else 0.0,
    }


def nucleotide_classification(sequence):
    sequence = clean_sequence(sequence)
    purines = sequence.count("A") + sequence.count("G")
    pyrimidines = sequence.count("C") + sequence.count("T")

    return {
        "Purines": purines,
        "Pyrimidines": pyrimidines,
        "Purine_Pyrimidine_Ratio": (
            purines / pyrimidines if pyrimidines else 0.0
        ),
    }


def validate_sequence(sequence):
    sequence = clean_sequence(sequence).replace("U", "T")
    valid_bases = IUPAC_DNA_BASES
    invalid_bases = sorted(set(sequence) - valid_bases)

    return {
        "Valid_DNA": len(invalid_bases) == 0,
        "Invalid_Bases": invalid_bases,
    }


def reverse_complement(sequence):
    sequence = clean_sequence(sequence).replace("U", "T")
    return str(Seq(sequence).reverse_complement())


def translate_sequence(sequence, frame=0):
    sequence = clean_sequence(sequence).replace("U", "T")
    # FASTA files can contain protein sequences or other non-DNA letters.
    # Keep their validation results, but don't pass invalid codons to the
    # nucleotide translator, which raises TranslationError.
    if set(sequence) - set("ATGCN"):
        return ""
    sequence = sequence[frame:]
    usable_length = len(sequence) - (len(sequence) % 3)
    sequence = sequence[:usable_length]

    if not sequence:
        return ""

    return str(Seq(sequence).translate(to_stop=False))


def six_frame_translation(sequence, max_bases=MAX_TRANSLATION_NT):
    sequence = clean_sequence(sequence)
    reverse_sequence = reverse_complement(sequence)
    sequence = sequence[:max_bases]
    reverse_sequence = reverse_sequence[:max_bases]

    return {
        "+1": translate_sequence(sequence, 0),
        "+2": translate_sequence(sequence, 1),
        "+3": translate_sequence(sequence, 2),
        "-1": translate_sequence(reverse_sequence, 0),
        "-2": translate_sequence(reverse_sequence, 1),
        "-3": translate_sequence(reverse_sequence, 2),
    }


def find_orfs(sequence, min_length=MIN_ORF_LENGTH):
    """Find complete ATG-to-stop ORFs in all six frames (1-based coordinates)."""
    sequence = clean_sequence(sequence).replace("U", "T")
    orfs = []
    original_length = len(sequence)
    strands = {
        "+": sequence,
        "-": reverse_complement(sequence),
    }
    stop_codons = {"TAA", "TAG", "TGA"}

    for strand, dna in strands.items():
        for frame in range(3):
            starts = []
            for position in range(frame, len(dna) - 2, 3):
                codon = dna[position:position + 3]
                if codon == "ATG":
                    starts.append(position)
                elif codon in stop_codons and starts:
                    end = position + 3
                    for start in starts:
                        orf_length = end - start
                        if orf_length < min_length:
                            continue
                        if strand == "+":
                            genomic_start, genomic_end = start + 1, end
                        else:
                            genomic_start = original_length - end + 1
                            genomic_end = original_length - start
                        coding_dna = dna[start:end]
                        peptide = str(Seq(coding_dna).translate(to_stop=True))
                        peptide_properties = (
                            protein_analysis(peptide)
                            if peptide and set(peptide) <= set("ACDEFGHIKLMNPQRSTVWY")
                            else None
                        )
                        orfs.append({
                            "Strand": strand,
                            "Frame": f"{strand}{frame + 1}",
                            "Start": genomic_start,
                            "End": genomic_end,
                            "Length": orf_length,
                            "Sequence": coding_dna,
                            "Protein": peptide,
                            "Protein_Length": len(peptide),
                            "Molecular_Weight": peptide_properties["Molecular_Weight"] if peptide_properties else None,
                            "Isoelectric_Point": peptide_properties["Isoelectric_Point"] if peptide_properties else None,
                            "GRAVY": peptide_properties["GRAVY"] if peptide_properties else None,
                        })
                    starts = []

    return orfs


def protein_analysis(protein):
    protein = protein.replace("*", "")

    if not protein:
        return {
            "Length": 0,
            "Molecular_Weight": 0.0,
            "Isoelectric_Point": 0.0,
            "GRAVY": 0.0,
            "Acidic_Percent": 0.0,
            "Basic_Percent": 0.0,
            "Hydrophobic_Percent": 0.0,
        }

    try:
        analysis = ProteinAnalysis(protein)
        molecular_weight = analysis.molecular_weight()
        isoelectric_point = analysis.isoelectric_point()
        gravy = analysis.gravy()
        counts = analysis.count_amino_acids()
        length = len(protein)
        acidic_percent = 100 * sum(counts.get(aa, 0) for aa in "DE") / length
        basic_percent = 100 * sum(counts.get(aa, 0) for aa in "KRH") / length
        hydrophobic_percent = 100 * sum(counts.get(aa, 0) for aa in "ACFILMVWY") / length
    except Exception:
        molecular_weight = 0.0
        isoelectric_point = 0.0
        gravy = acidic_percent = basic_percent = hydrophobic_percent = 0.0

    return {
        "Length": len(protein),
        "Molecular_Weight": molecular_weight,
        "Isoelectric_Point": isoelectric_point,
        "GRAVY": gravy,
        "Acidic_Percent": acidic_percent,
        "Basic_Percent": basic_percent,
        "Hydrophobic_Percent": hydrophobic_percent,
    }


def estimate_melting_temperature(sequence):
    """Estimate dsDNA Tm up to 10 kb at 50 mM Na+.

    Use nearest-neighbor thermodynamics for unambiguous sequences. For valid
    IUPAC ambiguity codes, use Biopython's empirical GC-content model, which
    weights each ambiguous base by its possible GC fraction.
    """
    dna = clean_sequence(sequence).replace("U", "T")
    if len(dna) < 8 or len(dna) > MAX_DNA_TM_NT or set(dna) - IUPAC_DNA_BASES:
        return None
    try:
        if set(dna) - set("ATGC"):
            return float(MeltingTemp.Tm_GC(
                dna,
                check=False,
                strict=False,
                valueset=7,
                Na=50,
            ))
        return float(MeltingTemp.Tm_NN(dna, Na=50))
    except (ValueError, ZeroDivisionError, KeyError):
        return None


def analyze_sequence(sequence):
    sequence = clean_sequence(sequence).replace("U", "T")
    orfs = find_orfs(sequence, min_length=MIN_ORF_LENGTH)

    return {
        "Statistics": sequence_statistics(sequence),
        "Skew": calculate_skew(sequence),
        "Nucleotide_Classification": nucleotide_classification(sequence),
        "Validation": validate_sequence(sequence),
        "Reverse_Complement": reverse_complement(sequence),
        "Six_Frame_Translation": six_frame_translation(sequence),
        "Translation_Truncated": len(sequence) > MAX_TRANSLATION_NT,
        "Melting_Temperature_C": estimate_melting_temperature(sequence),
        "ORFs": orfs,
        "ORF_Count": len(orfs),
    }


def print_analysis(record):
    result = analyze_sequence(str(record.seq))
    stats = result["Statistics"]

    print("\n" + "=" * 52)
    print("Genoseq AI Sequence Analysis")
    print("=" * 52)
    print("Record ID:", record.id)
    print("Description:", record.description)
    print("Sequence Length:", stats["Length"])
    print("A / T / G / C / N counts:",
          stats["A_count"], stats["T_count"], stats["G_count"],
          stats["C_count"], stats["N_count"])
    print("GC Content (%):", round(stats["GC_percent"], 2))
    print("AT Content (%):", round(stats["AT_percent"], 2))
    print("GC Skew:", round(result["Skew"]["GC_skew"], 4))
    print("AT Skew:", round(result["Skew"]["AT_skew"], 4))
    print("Valid DNA:", result["Validation"]["Valid_DNA"])
    if result["Validation"]["Invalid_Bases"]:
        print("Unexpected letters:", ", ".join(result["Validation"]["Invalid_Bases"]))
    print("ORF Count (minimum length", MIN_ORF_LENGTH, "bp):", result["ORF_Count"])

    for index, orf in enumerate(result["ORFs"], start=1):
        print("\nORF", index)
        print("  Strand:", orf["Strand"])
        print("  Frame:", orf["Frame"])
        print("  Start:", orf["Start"])
        print("  End:", orf["End"])
        print("  Length:", orf["Length"], "bp")


def save_csv_report(records):
    """Save one summary row per FASTA record beside this script."""
    report_path = Path(__file__).resolve().parent / "genoseq_ai_report.csv"
    fieldnames = [
        "Record_ID", "Description", "Length", "A_count", "T_count",
        "G_count", "C_count", "N_count", "GC_percent", "AT_percent",
        "GC_skew", "AT_skew", "Valid_DNA", "Invalid_Bases", "ORF_Count",
        "ORFs",
    ]

    with report_path.open("w", newline="", encoding="utf-8-sig") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            result = analyze_sequence(str(record.seq))
            stats = result["Statistics"]
            orf_summaries = [
                f"{orf['Strand']}:{orf['Frame']}:{orf['Start']}-{orf['End']} ({orf['Length']} bp)"
                for orf in result["ORFs"]
            ]
            writer.writerow({
                "Record_ID": record.id,
                "Description": record.description,
                "Length": stats["Length"],
                "A_count": stats["A_count"],
                "T_count": stats["T_count"],
                "G_count": stats["G_count"],
                "C_count": stats["C_count"],
                "N_count": stats["N_count"],
                "GC_percent": round(stats["GC_percent"], 2),
                "AT_percent": round(stats["AT_percent"], 2),
                "GC_skew": round(result["Skew"]["GC_skew"], 4),
                "AT_skew": round(result["Skew"]["AT_skew"], 4),
                "Valid_DNA": result["Validation"]["Valid_DNA"],
                "Invalid_Bases": ",".join(result["Validation"]["Invalid_Bases"]),
                "ORF_Count": result["ORF_Count"],
                "ORFs": "; ".join(orf_summaries),
            })

    return report_path

def main():
    if not FASTA_FILE.is_file():
        print("Error: FASTA file was not found:")
        print(" ", FASTA_FILE)
        print("Make sure test.fasta is inside the project's data folder.")
        return

    try:
        # fasta-pearson accepts comment lines before the first FASTA record.
        records = list(SeqIO.parse(str(FASTA_FILE), "fasta-pearson"))
    except (OSError, ValueError) as error:
        print("Error reading the FASTA file:", error)
        return

    if not records:
        print("No FASTA sequences were found in:")
        print(" ", FASTA_FILE)
        return

    print("Reading FASTA file:", FASTA_FILE)
    print("Total sequences:", len(records))

    for record in records:
        print_analysis(record)

    report_path = save_csv_report(records)
    print("\nCSV report saved to:")
    print(" ", report_path)


if __name__ == "__main__":
    main()
