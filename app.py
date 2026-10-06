import base64

from flask import Flask, Response, jsonify, render_template_string, request

from genoseq_ai_pipeline import run_analysis_pipeline
from reports import charts_as_zip, result_as_csv, result_as_json, result_as_pdf
from visualization import build_charts

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB prototype upload limit

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Genoseq AI | Sequence Analysis</title>
  <style>
    :root { color-scheme: light; --ink:#17231f; --muted:#62716b; --green:#176b52; --blue:#274e87; --line:#dce6e0; --wash:#f4f8f5; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--wash); color:var(--ink); font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
    main { max-width:1000px; margin:44px auto; padding:0 20px 48px; }
    header { margin-bottom:26px; }
    .eyebrow { color:var(--green); font-weight:750; letter-spacing:.08em; text-transform:uppercase; font-size:.78rem; }
    h1 { margin:.25rem 0; font-size:2.25rem; }
    h2 { margin-top:0; font-size:1.25rem; }
    h3 { margin-bottom:4px; overflow-wrap:anywhere; }
    .intro,.muted { color:var(--muted); }
    .card { background:white; border:1px solid var(--line); border-radius:16px; padding:24px; margin:18px 0; box-shadow:0 8px 24px #1738270a; }
    form { display:flex; flex-wrap:wrap; align-items:end; gap:14px; }
    label { display:block; font-weight:650; margin-bottom:6px; }
    input[type=file] { display:block; max-width:100%; padding:10px; border:1px solid var(--line); border-radius:9px; background:white; }
    button { border:0; border-radius:9px; padding:11px 18px; color:white; background:var(--green); font-weight:700; cursor:pointer; }
    button:hover { background:#10553f; }
    .error { color:#9b2525; background:#fff2f0; border:1px solid #f1c9c4; border-radius:10px; padding:12px 14px; margin-top:16px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:12px; }
    .metric { background:var(--wash); border-radius:11px; padding:14px; overflow-wrap:anywhere; }
    .metric span { display:block; color:var(--muted); font-size:.88rem; }
    .metric strong { font-size:1.2rem; }
    .record { border-top:1px solid var(--line); padding-top:16px; margin-top:18px; }
    .record:first-child { border-top:0; padding-top:0; margin-top:0; }
    .orf { border-left:3px solid var(--green); padding:10px 14px; margin:10px 0; background:var(--wash); }
    .tag { display:inline-block; background:#e6f2ec; color:var(--green); border-radius:999px; padding:3px 10px; font-size:.82rem; font-weight:700; }
    table { width:100%; border-collapse:collapse; margin-top:12px; }
    th,td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }
    @media(max-width:600px) { main { margin-top:28px; } .card { padding:18px; } }
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">Genoseq AI · Analysis prototype</div>
    <h1>Upload · Analyze · Explore</h1>
    <p class="intro">Upload one text-based FASTA, FASTQ, or VCF file for a first-pass analysis. The file is processed in memory and is not saved by this upload page.</p>
  </header>

  <section class="card">
    <h2>Choose a sequence file</h2>
    <p class="muted">Supported: DNA or protein FASTA (.fa, .fasta, .fna, .fas, .faa), FASTQ (.fq, .fastq), VCF (.vcf). Maximum upload: 25 MB.</p>
    <form method="post" enctype="multipart/form-data">
      <div>
        <label for="sequence-file">Sequence file</label>
        <input id="sequence-file" name="sequence_file" type="file" accept=".fa,.fasta,.fna,.fas,.faa,.fq,.fastq,.vcf,.txt" required>
      </div>
      <button type="submit" name="action" value="analyze">Analyze file</button>
      <button type="submit" name="action" value="csv">Download CSV</button>
      <button type="submit" name="action" value="json">Download JSON</button>
      <button type="submit" name="action" value="pdf">Download PDF report</button>
      <button type="submit" name="action" value="charts">Download charts (PNG + SVG)</button>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </section>

  {% if result %}
  <section class="card">
    <span class="tag">{{ result.kind|upper }}</span>
    <h2>Analysis results</h2>
    <p class="muted">File: {{ result.filename }}</p>

    {% if result.kind == "fasta" %}
      <p><strong>Sequences in file:</strong> {{ result.record_count }}</p>
      {% for item in result.records %}
      <article class="record">
        <h3>{{ item.id }}</h3>
        <span class="tag">{{ item.record_type }}</span>
        {% if item.description %}<p class="muted">{{ item.description }}</p>{% endif %}
        {% if item.record_type == "Protein" %}
        <div class="grid">
          <div class="metric"><span>Protein length</span><strong>{{ item.protein_length }} aa</strong></div>
          <div class="metric"><span>Molecular weight</span><strong>{{ item.molecular_weight|round(2) }} Da</strong></div>
          <div class="metric"><span>Theoretical pI</span><strong>{{ item.isoelectric_point|round(2) }}</strong></div>
        </div>
        <h4>Amino-acid composition</h4>
        <p>{% for amino_acid, percentage in item.amino_acid_composition.items() %}<strong>{{ amino_acid }}:</strong> {{ percentage }}%{% if not loop.last %} · {% endif %}{% endfor %}</p>
        {% else %}
        <div class="grid">
          <div class="metric"><span>Sequence length</span><strong>{{ item.stats.Length }} bp</strong></div>
          <div class="metric"><span>GC content</span><strong>{{ item.stats.GC_percent|round(2) }}%</strong></div>
          <div class="metric"><span>AT content</span><strong>{{ item.stats.AT_percent|round(2) }}%</strong></div>
          <div class="metric"><span>ORFs (minimum 90 bp)</span><strong>{{ item.orf_count }}</strong></div>
        </div>
        <p><strong>A / T / G / C / N counts:</strong> {{ item.stats.A_count }} / {{ item.stats.T_count }} / {{ item.stats.G_count }} / {{ item.stats.C_count }} / {{ item.stats.N_count }}</p>
        <p><strong>GC skew:</strong> {{ item.gc_skew|round(4) }} &nbsp; <strong>AT skew:</strong> {{ item.at_skew|round(4) }}</p>
        <p><strong>Valid DNA:</strong> {{ "Yes" if item.valid else "No" }}{% if item.invalid_bases %} · Unexpected letters: {{ item.invalid_bases|join(", ") }}{% endif %}</p>
        {% if item.orfs %}
          <h4>Open reading frames</h4>
          {% for orf in item.orfs %}
          <div class="orf"><strong>ORF {{ loop.index }}</strong> · Strand {{ orf.Strand }} · Frame {{ orf.Frame }} · Positions {{ orf.Start }}–{{ orf.End }} · {{ orf.Length }} bp</div>
          {% endfor %}
        {% else %}
          <p class="muted">No ORF of at least 90 bp was found in this sequence.</p>
        {% endif %}
        {% endif %}
      </article>
      {% endfor %}

    {% elif result.kind == "fastq" %}
      <div class="grid">
        <div class="metric"><span>Total reads</span><strong>{{ result.total_reads }}</strong></div>
        <div class="metric"><span>Total bases</span><strong>{{ result.total_bases }}</strong></div>
        <div class="metric"><span>Mean read length</span><strong>{{ result.mean_read_length|round(2) }} bp</strong></div>
        <div class="metric"><span>GC content</span><strong>{{ result.gc_percent|round(2) }}%</strong></div>
        <div class="metric"><span>Mean base quality</span><strong>{{ result.mean_quality|round(2) }}</strong></div>
        <div class="metric"><span>Q20 / Q30 bases</span><strong>{{ result.q20_percent|round(2) }}% / {{ result.q30_percent|round(2) }}%</strong></div>
        <div class="metric"><span>Read length range</span><strong>{{ result.min_read_length }}–{{ result.max_read_length }} bp</strong></div>
      </div>
      <h3>Read length distribution</h3>
      <table><thead><tr><th>Read length (bp)</th><th>Number of reads</th></tr></thead><tbody>
      {% for length, count in result.read_length_distribution.items() %}<tr><td>{{ length }}</td><td>{{ count }}</td></tr>{% endfor %}
      </tbody></table>
      <p class="muted">Per-position mean quality is calculated for {{ result.quality_by_position|length }} read positions. Adapter analysis and graphical quality plots are future modules.</p>

    {% elif result.kind == "vcf" %}
      <div class="grid">
        <div class="metric"><span>Variant records</span><strong>{{ result.total_variants }}</strong></div>
        <div class="metric"><span>Alternate alleles</span><strong>{{ result.total_alt_alleles }}</strong></div>
        <div class="metric"><span>SNP alleles</span><strong>{{ result.snp_count }}</strong></div>
        <div class="metric"><span>Insertions + deletions</span><strong>{{ result.indel_count }}</strong></div>
        <div class="metric"><span>PASS / unfiltered records</span><strong>{{ result.passing_records }}</strong></div>
        <div class="metric"><span>Samples</span><strong>{{ result.sample_count }}</strong></div>
        {% if result.mean_quality is not none %}<div class="metric"><span>Mean QUAL</span><strong>{{ result.mean_quality|round(2) }}</strong></div>{% endif %}
      </div>
      <p><strong>Multi-base substitutions:</strong> {{ result.mnv_count }} &nbsp; <strong>Other alleles:</strong> {{ result.complex_count }}</p>
      <h3>Variants by chromosome / contig</h3>
      <table><thead><tr><th>Chromosome / contig</th><th>Variant records</th></tr></thead><tbody>
      {% for chromosome, count in result.chromosome_distribution.items() %}<tr><td>{{ chromosome }}</td><td>{{ count }}</td></tr>{% endfor %}
      </tbody></table>
      {% if result.samples %}<p><strong>Sample names:</strong> {{ result.samples|join(", ") }}</p>{% endif %}
      <p class="muted">This is a basic VCF summary. It does not determine pathogenicity or provide clinical interpretation.</p>
    {% endif %}
  </section>
  {% endif %}
  {% if result and result.workflow %}
  <section class="card">
    <h2>Workflow status</h2>
    <ol>
      {% for stage in result.workflow %}
      <li><strong>{{ stage.name }}</strong> — {{ stage.status }}. {{ stage.details }}</li>
      {% endfor %}
    </ol>
  </section>
  {% endif %}
  {% if chart_previews %}
  <section class="card">
    <h2>Visual summaries</h2>
    {% for chart in chart_previews %}
    <figure><img src="data:image/png;base64,{{ chart.image }}" alt="{{ chart.title }}" style="display:block;width:100%;max-width:720px;height:auto"><figcaption class="muted">{{ chart.title }}</figcaption></figure>
    {% endfor %}
  </section>
  {% endif %}
  <p class="muted">Genoseq AI is a learning prototype. Results are descriptive; they are not a diagnosis or clinical interpretation.</p>
</main>
</body>
</html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None
    chart_previews = []

    if request.method == "POST":
        uploaded_file = request.files.get("sequence_file")
        if uploaded_file is None or not uploaded_file.filename:
            error = "Choose a sequence file first."
        else:
            try:
                raw_bytes = uploaded_file.stream.read()
                result = run_analysis_pipeline(uploaded_file.filename, raw_bytes)
                action = request.form.get("action", "analyze")
                if action == "csv":
                    return Response(
                        result_as_csv(result),
                        mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=genoseq_ai_report.csv"},
                    )
                if action == "json":
                    return Response(
                        result_as_json(result),
                        mimetype="application/json",
                        headers={"Content-Disposition": "attachment; filename=genoseq_ai_report.json"},
                    )
                if action in {"pdf", "charts"} or action == "analyze":
                    charts = build_charts(result)
                    if action == "pdf":
                        return Response(
                            result_as_pdf(result, charts),
                            mimetype="application/pdf",
                            headers={"Content-Disposition": "attachment; filename=genoseq_ai_report.pdf"},
                        )
                    if action == "charts":
                        return Response(
                            charts_as_zip(charts),
                            mimetype="application/zip",
                            headers={"Content-Disposition": "attachment; filename=genoseq_ai_charts.zip"},
                        )
                    chart_previews = [
                        {"title": name.replace("_", " ").title(),
                         "image": base64.b64encode(formats["png"]).decode("ascii")}
                        for name, formats in charts.items()
                    ]
            except ValueError as exc:
                error = str(exc)
            except OSError as exc:
                app.logger.exception("Could not read uploaded file %s", uploaded_file.filename)
                error = "Genoseq AI could not read this upload. Please choose the file again and retry."
            except Exception as exc:
                app.logger.exception("Unexpected error while analyzing uploaded file %s", uploaded_file.filename)
                result = None
                chart_previews = []
                error = (
                    "Genoseq AI could not finish analyzing this file. "
                    "Check that it is a valid FASTA, FASTQ, or VCF file and try again. "
                    "If the problem continues, check the server terminal for details."
                )

    return render_template_string(PAGE, error=error, result=result, chart_previews=chart_previews)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    uploaded_file = request.files.get("sequence_file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({"error": "Upload a file using the sequence_file field."}), 400
    try:
        result = run_analysis_pipeline(uploaded_file.filename, uploaded_file.stream.read())
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Unexpected error in /api/analyze for %s", uploaded_file.filename)
        return jsonify({
            "error": "Genoseq AI could not analyze this file. Check the file format and try again."
        }), 500


@app.errorhandler(500)
def internal_server_error(_error):
    app.logger.exception("Unhandled Genoseq AI server error")
    if request.path == "/api/analyze":
        return jsonify({
            "error": "Genoseq AI hit an unexpected server error. Please retry with a valid file."
        }), 500
    return render_template_string(
        PAGE,
        error="Genoseq AI hit an unexpected server error. The traceback was written to the server terminal.",
        result=None,
        chart_previews=[],
    ), 500


@app.errorhandler(413)
def file_too_large(_error):
    message = "That file is larger than the 25 MB upload limit."
    if request.path == "/api/analyze":
        return jsonify({"error": message}), 413
    return render_template_string(
        PAGE,
        error=message,
        result=None,
        chart_previews=[],
    ), 413

if __name__ == "__main__":
    # Local development only. Public hosting will start the app with Gunicorn.
    app.run(host="127.0.0.1", port=5000, debug=False)
