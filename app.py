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
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { color-scheme: light; --ink:#142b2a; --muted:#70817d; --green:#087f70; --green-dark:#06695d; --blue:#3f69e8; --line:#e2eae6; --wash:#f5f8f6; --mint:#e8f5ef; --shadow:0 14px 40px #163b2b0b; }
    * { box-sizing:border-box; }
    body { margin:0; background:radial-gradient(ellipse at 84% 2%,#e5f5ed 0,transparent 29rem),var(--wash); color:var(--ink); font:15px/1.6 'DM Sans',system-ui,sans-serif; }
    main { max-width:1160px; margin:0 auto; padding:0 30px 64px; }
    header { position:relative; margin:0 -30px 30px; padding:23px 30px 30px; border-bottom:1px solid #e5ece8; background:#ffffffcf; }
    .topbar { display:flex; align-items:center; justify-content:space-between; max-width:1100px; margin:auto auto 45px; }
    .brand { display:flex; align-items:center; gap:11px; font:800 17px 'Manrope',sans-serif; letter-spacing:-.5px; }
    .brand-mark { display:grid; place-items:center; width:36px; height:36px; color:white; border-radius:12px; background:linear-gradient(145deg,#0a9a80,#06695d); box-shadow:0 6px 14px #087f7030; }
    .brand-mark svg { width:20px; height:20px; }
    .nav-status { display:flex; align-items:center; gap:8px; padding:7px 12px; border:1px solid var(--line); border-radius:999px; background:white; color:#637571; font-size:12px; font-weight:600; }
    .status-dot { width:7px; height:7px; border-radius:50%; background:#35a879; box-shadow:0 0 0 3px #e8f5ef; }
    .hero { max-width:1100px; margin:0 auto; }
    .eyebrow { display:flex; align-items:center; gap:8px; color:var(--green); font:700 11px 'DM Mono',monospace; letter-spacing:.13em; text-transform:uppercase; }
    h1 { margin:12px 0 9px; font:800 clamp(32px,5vw,48px)/1.12 'Manrope',sans-serif; letter-spacing:-2px; }
    h2 { margin:0; font:700 19px 'Manrope',sans-serif; letter-spacing:-.4px; }
    h3 { margin-bottom:4px; overflow-wrap:anywhere; font:700 16px 'Manrope',sans-serif; }
    .intro,.muted { color:var(--muted); }
    .intro { max-width:640px; margin:0; font-size:15px; }
    .hero-meta { display:flex; gap:9px; margin-top:20px; flex-wrap:wrap; }
    .hero-meta span,.format-chip { padding:5px 10px; border:1px solid var(--line); border-radius:7px; background:#ffffffba; color:#536b65; font:500 11px 'DM Mono',monospace; }
    .card { background:#fff; border:1px solid var(--line); border-radius:17px; padding:26px; margin:18px 0; box-shadow:var(--shadow); }
    .upload-card { padding:26px; }
    .section-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:19px; }
    .section-heading p { margin:5px 0 0; color:var(--muted); font-size:13px; }
    .step { display:inline-flex; align-items:center; gap:7px; white-space:nowrap; color:#83928e; font:500 11px 'DM Mono',monospace; }
    .step b { display:grid; place-items:center; width:22px; height:22px; border-radius:50%; background:var(--mint); color:var(--green); }
    form { display:flex; flex-wrap:wrap; align-items:stretch; gap:12px; }
    .dropzone { position:relative; display:flex; flex:1 1 520px; align-items:center; gap:15px; min-width:240px; min-height:102px; padding:18px; border:1.5px dashed #bad4cb; border-radius:12px; background:#f9fcfa; transition:.18s ease; }
    .dropzone:hover,.dropzone.is-dragging { border-color:var(--green); background:#f0faf5; }
    .upload-icon { flex:0 0 42px; display:grid; place-items:center; width:42px; height:42px; border-radius:12px; background:var(--mint); color:var(--green); font-size:20px; }
    .upload-copy { min-width:0; flex:1; }
    .upload-copy strong { display:block; color:var(--ink); font-size:14px; }
    .upload-copy span { display:block; color:var(--muted); font-size:12px; }
    label { display:block; margin-bottom:5px; font-weight:650; }
    input[type=file] { display:block; width:100%; max-width:100%; margin-top:8px; color:#657771; font:12px 'DM Sans',sans-serif; }
    input[type=file]::file-selector-button { margin-right:9px; padding:6px 10px; border:1px solid #dce8e2; border-radius:6px; background:white; color:#31564c; font:600 11px 'DM Sans',sans-serif; cursor:pointer; }
    .submit-wrap { display:flex; flex:0 0 190px; flex-direction:column; justify-content:center; gap:8px; }
    button { width:100%; min-height:43px; border:0; border-radius:9px; padding:11px 16px; color:white; background:var(--green); font:700 13px 'DM Sans',sans-serif; cursor:pointer; transition:.16s ease; }
    button:hover { background:var(--green-dark); transform:translateY(-1px); box-shadow:0 6px 14px #087f7027; }
    .formats { display:flex; align-items:center; flex-wrap:wrap; gap:7px; margin-top:14px; }
    .formats-label { margin-right:2px; color:var(--muted); font-size:11px; }
    .format-chip { padding:3px 8px; background:#f7faf8; font-size:10px; }
    .export-actions { display:flex; flex-wrap:wrap; gap:7px; width:100%; margin-top:4px; padding-top:13px; border-top:1px solid #edf1ee; }
    .export-actions button { width:auto; min-height:33px; padding:7px 11px; border:1px solid var(--line); background:#fff; color:#4b625c; font-size:11px; }
    .export-actions button:hover { border-color:#a7cbc0; background:#f6fbf8; color:var(--green-dark); box-shadow:none; }
    .error { color:#9b3430; background:#fff4f2; border:1px solid #f2d1cc; border-radius:10px; padding:12px 14px; margin-top:16px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:12px; }
    .metric { background:#f7faf8; border:1px solid #edf2ef; border-radius:11px; padding:15px; overflow-wrap:anywhere; }
    .metric span { display:block; color:var(--muted); font-size:11px; }
    .metric strong { display:block; margin-top:3px; color:#173d36; font:700 20px 'Manrope',sans-serif; }
    .record { border-top:1px solid var(--line); padding-top:16px; margin-top:18px; }
    .record:first-child { border-top:0; padding-top:0; margin-top:0; }
    .orf { border-left:3px solid var(--green); padding:10px 14px; margin:10px 0; background:var(--wash); }
    .tag { display:inline-block; background:#e8f5ef; color:var(--green-dark); border-radius:999px; padding:3px 10px; font:600 10px 'DM Mono',monospace; letter-spacing:.04em; }
    table { width:100%; border-collapse:collapse; margin-top:12px; font-size:13px; }
    th,td { text-align:left; padding:10px; border-bottom:1px solid var(--line); }
    th { color:#60736c; background:#f7faf8; font-size:11px; text-transform:uppercase; letter-spacing:.05em; }
    .results-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:15px 0 17px; }
    .results-heading h2 { margin:0; }
    figure { margin:18px 0; padding:14px; border:1px solid var(--line); border-radius:12px; background:#fbfdfb; }
    figcaption { margin-top:8px; font-size:12px; }
    footer { padding-top:18px; border-top:1px solid #e5ece8; color:var(--muted); font-size:12px; }
    @media(max-width:680px) { main { padding:0 16px 40px; } header { margin:0 -16px 20px; padding:17px 16px 24px; } .topbar { margin-bottom:34px; } .card { padding:19px; } .section-heading { flex-direction:column; } .dropzone { flex-basis:100%; } .submit-wrap { flex:1 1 100%; } h1 { letter-spacing:-1.3px; } }
  </style>
</head>
<body>
<main>
  <header>
    <div class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 3c0 6 10 6 10 12s-10 3-10 6M17 3c0 6-10 6-10 12s10 3 10 6M8 7h8M7 12h10M8 17h8"/></svg></span>Genoseq AI</div>
      <div class="nav-status"><span class="status-dot"></span>Analysis workspace</div>
    </div>
    <div class="hero">
      <div class="eyebrow"><span class="status-dot"></span>Sequence intelligence · Workspace</div>
      <h1>Explore your sequence data.</h1>
      <p class="intro">A clear first look at your genomic files. Upload a sequence to surface quality, composition, and variant summaries in seconds.</p>
      <div class="hero-meta"><span>01 &nbsp; UPLOAD</span><span>02 &nbsp; ANALYZE</span><span>03 &nbsp; EXPLORE RESULTS</span></div>
    </div>
  </header>

  <section class="card upload-card">
    <div class="section-heading"><div><h2>Start an analysis</h2><p>Choose a file to generate a structured sequence report.</p></div><span class="step"><b>1</b> INPUT DATA</span></div>
    <form method="post" enctype="multipart/form-data">
      <div class="dropzone" id="dropzone">
        <span class="upload-icon" aria-hidden="true">↥</span>
        <div class="upload-copy"><strong id="file-label">Choose a sequence file</strong><span id="file-hint">Browse your computer or drag and drop here · up to 25 MB</span>
          <input id="sequence-file" name="sequence_file" type="file" accept=".fa,.fasta,.fna,.fas,.faa,.fq,.fastq,.vcf,.txt" required aria-label="Choose a FASTA, FASTQ, or VCF sequence file">
        </div>
      </div>
      <div class="submit-wrap"><button type="submit" name="action" value="analyze">Analyze sequence &nbsp; →</button><span class="muted" style="text-align:center;font-size:11px">Results appear below</span></div>
      <div class="formats"><span class="formats-label">SUPPORTED FORMATS</span><span class="format-chip">FASTA</span><span class="format-chip">FASTQ</span><span class="format-chip">VCF</span><span class="formats-label">· DNA, RNA &amp; protein</span></div>
      <div class="export-actions" aria-label="Analysis report downloads"><button type="submit" name="action" value="csv">↓ &nbsp; CSV report</button><button type="submit" name="action" value="json">↓ &nbsp; JSON data</button><button type="submit" name="action" value="pdf">↓ &nbsp; PDF report</button><button type="submit" name="action" value="charts">↓ &nbsp; Charts bundle</button></div>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </section>

  {% if result %}
  <section class="card">
    <div class="results-heading"><h2>Analysis results</h2><span class="tag">{{ result.kind|upper }} · COMPLETE</span></div>
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
  <footer>Genoseq AI is a learning prototype. Results are descriptive and are not a diagnosis or clinical interpretation. Uploaded files are processed in memory and are not saved by this page.</footer>
</main>
<script>
  (() => {
    const input = document.getElementById('sequence-file');
    const dropzone = document.getElementById('dropzone');
    const label = document.getElementById('file-label');
    const hint = document.getElementById('file-hint');
    const showFile = (file) => {
      if (!file) return;
      label.textContent = file.name;
      hint.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to analyze`;
    };
    input.addEventListener('change', () => showFile(input.files[0]));
    ['dragenter', 'dragover'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
      event.preventDefault(); dropzone.classList.add('is-dragging');
    }));
    ['dragleave', 'drop'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
      event.preventDefault(); dropzone.classList.remove('is-dragging');
    }));
    dropzone.addEventListener('drop', (event) => {
      const file = event.dataTransfer.files[0];
      if (!file) return;
      const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; showFile(file);
    });
  })();
</script>
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
