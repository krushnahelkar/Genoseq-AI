"""Numeric feature extraction for future Genoseq AI model training.

This module does not make predictions. A trained model and labeled data are
required before any class or risk score can be reported.
"""


def extract_features(result):
    """Return numeric, format-specific rows suitable for later model training."""
    kind = result["kind"]

    if kind == "fasta":
        rows = []
        for record in result["records"]:
            if record.get("record_type") == "Protein":
                rows.append({
                    "record_id": record["id"],
                    "protein_length": record["protein_length"],
                    "molecular_weight": record["molecular_weight"],
                    "isoelectric_point": record["isoelectric_point"],
                    "gravy": record["gravy"],
                    "acidic_percent": record["acidic_percent"],
                    "basic_percent": record["basic_percent"],
                    "hydrophobic_percent": record["hydrophobic_percent"],
                    **{
                        f"aa_{amino_acid.lower()}_percent": percent
                        for amino_acid, percent in record["amino_acid_composition"].items()
                    },
                })
                continue
            stats = record["stats"]
            rows.append({
                "record_id": record["id"],
                "sequence_length": stats["Length"],
                "a_percent": stats["A_percent"],
                "t_percent": stats["T_percent"],
                "g_percent": stats["G_percent"],
                "c_percent": stats["C_percent"],
                "n_percent": stats["N_percent"],
                "gc_percent": stats["GC_percent"],
                "at_percent": stats["AT_percent"],
                "gc_skew": record["gc_skew"],
                "at_skew": record["at_skew"],
                "orf_count": record["orf_count"],
                "tm_estimate_c": record["melting_temperature_c"],
                "valid_dna": int(record["valid"]),
            })
        return rows

    if kind == "fastq":
        return [{
            "total_reads": result["total_reads"],
            "total_bases": result["total_bases"],
            "mean_read_length": result["mean_read_length"],
            "min_read_length": result["min_read_length"],
            "max_read_length": result["max_read_length"],
            "gc_percent": result["gc_percent"],
            "mean_quality": result["mean_quality"],
            "q20_percent": result["q20_percent"],
            "q30_percent": result["q30_percent"],
        }]

    if kind == "vcf":
        return [{
            "total_variants": result["total_variants"],
            "total_alt_alleles": result["total_alt_alleles"],
            "snp_count": result["snp_count"],
            "indel_count": result["indel_count"],
            "insertion_count": result["insertion_count"],
            "deletion_count": result["deletion_count"],
            "mnv_count": result["mnv_count"],
            "passing_records": result["passing_records"],
            "mean_quality": result["mean_quality"] or 0.0,
            "sample_count": result["sample_count"],
            "contig_count": len(result["chromosome_distribution"]),
        }]

    return []


def model_readiness():
    return {
        "available": False,
        "status": "not_trained",
        "message": (
            "Feature extraction is available. Predictions are disabled until "
            "a labeled training dataset and prediction target are selected, "
            "then a model is trained and evaluated."
        ),
    }
