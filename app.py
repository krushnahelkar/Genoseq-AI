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
  <title>GenoSeq AI | Genomic Sequence Analysis</title>
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
    :root { color-scheme:dark; --ink:#eef5fb; --muted:#95a5b8; --green:#42d6bd; --green-dark:#16a993; --blue:#55a9ff; --line:#1e2e43; --wash:#0a1422; --mint:#112c36; --shadow:0 18px 48px #02071060; }
    body { background:radial-gradient(ellipse at 78% -10%,#152b40 0,transparent 34rem),#080f1a; color:#eef5fb; }
    main { max-width:1260px; }
    header { background:linear-gradient(120deg,#0d1725f2,#0c1724d9); border-color:#1e2c40; }
    .brand-mark { color:#06131b; background:linear-gradient(145deg,#5ce3c7,#2c9eaa); box-shadow:0 7px 22px #2bc5aa33; }
    .nav-status,.hero-meta span,.format-chip { background:#101c2b; border-color:#24354a; color:#aab9c9; }
    .status-dot { background:#4de0b5; box-shadow:0 0 0 3px #15362f; }
    .eyebrow { color:#61dcc4; }
    .intro,.muted,.section-heading p { color:#95a5b8; }
    .card { background:linear-gradient(145deg,#111d2b,#0d1724); border-color:#203047; box-shadow:var(--shadow); }
    .dropzone { background:#0b1623; border-color:#2c4853; }
    .dropzone:hover,.dropzone.is-dragging { background:#10262b; border-color:#42d6bd; }
    .upload-icon,.step b { background:#14312f; color:#68e2c9; }
    .upload-copy strong,h1,h2,h3 { color:#f1f6fc; }
    input[type=file] { color:#a4b2c0; }
    input[type=file]::file-selector-button { background:#172538; border-color:#2a3b51; color:#d0dfed; }
    button { color:#041b1b; background:linear-gradient(135deg,#57e0c2,#27b9af); }
    button:hover { background:linear-gradient(135deg,#7aecd3,#42d0c4); box-shadow:0 8px 22px #27cbb635; }
    .export-actions { border-color:#1e2e43; }
    .export-actions button { background:#111e2d; color:#bbcad9; border-color:#2a3a4f; }
    .export-actions button:hover { background:#152738; border-color:#38786f; color:#70e2ce; }
    .metric { background:linear-gradient(135deg,#142235,#101b2a); border-color:#24354a; }
    .metric strong { color:#eaf6fb; }
    .metric span { color:#9eafc0; }
    .tag { background:#15342f; color:#64e2c8; }
    th { background:#142133; color:#a6b6c7; }
    td,th { border-color:#233247; }
    .orf { background:#101f2d; border-color:#42d6bd; }
    figure { background:#0d1826; border-color:#223249; }
    figure img { border-radius:7px; }
    footer { border-color:#1e2c40; color:#8ea0b3; }
    .dashboard-nav { display:flex; gap:19px; align-items:center; color:#8092a7; font-size:12px; }
    .dashboard-nav span:last-child { color:#5ce0c2; border-bottom:2px solid #5ce0c2; padding:10px 0; }
    .subhead { color:#b3c2d0; font-size:15px; letter-spacing:.01em; }
    .base-grid,.chart-grid,.protein-summary { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }
    .base-tile,.chart-card,.aa-summary { padding:15px; border:1px solid #24354a; border-radius:12px; background:#0c1724; }
    .base-tile { display:flex; align-items:center; gap:12px; }
    .base-symbol { display:grid; place-items:center; width:35px; height:35px; flex:0 0 35px; border-radius:10px; font:800 15px 'Manrope',sans-serif; }
    .base-a { background:#3b2e1e; color:#ffc166; } .base-g { background:#172e43; color:#6dbbff; } .base-t { background:#352443; color:#d49aff; } .base-c { background:#173629; color:#6fe1a9; } .base-n { background:#27313c; color:#b2c0cd; }
    .base-tile strong { display:block; font-size:12px; color:#eaf1f7; }
    .base-tile small { color:#8ea0b3; font-size:11px; }
    .bar-row { display:grid; grid-template-columns:105px minmax(60px,1fr) 110px; align-items:center; gap:12px; width:100%; min-height:42px; padding:5px 8px; border:1px solid transparent; border-radius:8px; background:transparent; color:#d5e0ea; text-align:left; }
    .bar-row:hover,.bar-row[aria-pressed=true] { background:#16263a; border-color:#2b4259; }
    .bar-track { display:block; width:100%; height:9px; overflow:hidden; border-radius:8px; background:#1d2b3c; }
    .bar-fill { display:block; height:100%; width:var(--bar-width); border-radius:8px; background:linear-gradient(90deg,#278f99,#60e0c1); }
    .bar-value { color:#b5c3d0; text-align:right; font:11px 'DM Mono',monospace; }
    .chart-detail,.chart-note { min-height:23px; color:#89a0b1; font-size:12px; }
    .frame-tabs,.aa-filters { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }
    .frame-tabs button,.aa-filters button { width:auto; min-height:32px; padding:7px 12px; border:1px solid #2a3d54; background:#132134; color:#b8c7d5; font:600 11px 'DM Mono',monospace; }
    .frame-tabs button[aria-selected=true],.aa-filters button[aria-pressed=true] { background:#16443f; color:#6ce4cc; border-color:#2c8177; }
    .translation-panel { padding:14px; border:1px solid #24354a; border-radius:10px; background:#09131f; }
    .translation-panel[hidden] { display:none; }
    .translation-sequence { display:block; max-height:200px; overflow:auto; overflow-wrap:anywhere; color:#80dfc6; font:12px/1.8 'DM Mono',monospace; white-space:pre-wrap; }
    .aa-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(115px,1fr)); gap:8px; }
    .aa-card { padding:10px; border:1px solid #28394d; border-radius:9px; background:#0b1623; color:#dfe8f1; text-align:left; }
    .aa-card:hover,.aa-card[aria-pressed=true] { border-color:#49cdb5; background:#132c30; }
    .aa-card[hidden] { display:none; }
    .aa-head { display:flex; justify-content:space-between; gap:6px; font-weight:700; }
    .aa-name { display:block; margin:3px 0 7px; color:#90a2b4; font-size:10px; }
    .aa-card .bar-track { height:5px; margin-top:4px; }
    .class-hydrophobic .bar-fill { background:linear-gradient(90deg,#d59335,#ffd27a); }
    .class-acidic .bar-fill { background:linear-gradient(90deg,#d85d74,#ff98a5); }
    .class-basic .bar-fill { background:linear-gradient(90deg,#8a72ed,#c7a4ff); }
    .class-polar .bar-fill { background:linear-gradient(90deg,#278f99,#60e0c1); }
    .subsection { margin-top:22px; }
    .section-title { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:18px 0 11px; }
    .section-title h3 { margin:0; }
    .small-label { color:#8ea0b3; font:10px 'DM Mono',monospace; letter-spacing:.08em; text-transform:uppercase; }
    .clinical-note { margin-top:12px; padding:10px 12px; border-left:3px solid #e6a84b; border-radius:5px; background:#261e18; color:#d8be97; font-size:12px; }
    select { min-height:36px; margin:8px 0; padding:7px 11px; border:1px solid #2a3d54; border-radius:8px; background:#132134; color:#d8e3ed; font:12px 'DM Sans',sans-serif; }
    .error { color:#ffc3c6; background:#301b24; border-color:#70404b; }
    .orf[hidden] { display:none; }
    @media(max-width:680px) { .dashboard-nav { display:none; } .bar-row { grid-template-columns:92px minmax(40px,1fr) 90px; gap:8px; padding-inline:4px; } }
  </style>
</head>
<body>
<main>
  <header>
    <div class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 3c0 6 10 6 10 12s-10 3-10 6M17 3c0 6-10 6-10 12s10 3 10 6M8 7h8M7 12h10M8 17h8"/></svg></span>GenoSeq AI</div>
      <nav class="dashboard-nav" aria-label="Workspace navigation"><span>Workspace</span><span>Analysis</span><span>Documentation</span></nav>
      <div class="nav-status"><span class="status-dot"></span>Analysis workspace</div>
    </div>
    <div class="hero">
      <div class="eyebrow"><span class="status-dot"></span>GENOMIC ANALYSIS WORKSPACE</div>
      <h1>GenoSeq AI</h1>
      <p class="intro subhead">Intelligent Genomic Sequence Analysis and Disease Prediction</p>
      <p class="intro" style="margin-top:8px">Explore sequence quality, composition, translation, and variant summaries in one workspace.</p>
      <div class="clinical-note">Disease prediction is not active in this prototype. A labeled training set and validated model are required before it can report disease predictions.</div>
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
    {% if error %}<div class="error" role="alert">{{ error }}</div>{% endif %}
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
          <div class="metric"><span>Theoretical isoelectric point</span><strong>{{ item.isoelectric_point|round(2) }} pI</strong></div>
          <div class="metric"><span>GRAVY hydropathy score</span><strong>{{ item.gravy|round(3) }}</strong></div>
          <div class="metric"><span>Acidic residues (D + E)</span><strong>{{ item.acidic_percent|round(2) }}%</strong></div>
          <div class="metric"><span>Basic residues (K + R + H)</span><strong>{{ item.basic_percent|round(2) }}%</strong></div>
          <div class="metric"><span>Hydrophobic residues</span><strong>{{ item.hydrophobic_percent|round(2) }}%</strong></div>
          <div class="metric"><span>Protein melting temperature (Tm)</span><strong>{% if item.melting_temperature_c is not none %}{{ item.melting_temperature_c|round(2) }} °C{% else %}Predictor unavailable{% endif %}</strong></div>
        </div>
        {% if item.melting_temperature_c is none %}<p class="clinical-note">{{ item.melting_temperature_note }} Protein Tm is not the same measurement as DNA-primer Tm.</p>{% endif %}
        <div class="subsection">
          <div class="section-title"><h3>Amino-acid composition</h3><span class="small-label">Select a residue or filter by property</span></div>
          <div class="aa-filters" role="group" aria-label="Filter amino acids by property">
            <button type="button" data-aa-filter="all" aria-pressed="true">All residues</button>
            <button type="button" data-aa-filter="hydrophobic" aria-pressed="false">Hydrophobic</button>
            <button type="button" data-aa-filter="acidic" aria-pressed="false">Acidic</button>
            <button type="button" data-aa-filter="basic" aria-pressed="false">Basic</button>
            <button type="button" data-aa-filter="polar" aria-pressed="false">Other polar</button>
          </div>
          <div class="aa-grid" aria-label="Interactive amino-acid composition chart">
            {% for aa in item.amino_acid_detail %}
            <button type="button" class="aa-card class-{{ aa.group }}" data-aa-class="{{ aa.group }}" data-aa-code="{{ aa.code }}" data-aa-name="{{ aa.name }}" data-aa-count="{{ aa.count }}" data-aa-percent="{{ aa.percent }}" aria-pressed="false">
              <span class="aa-head"><span>{{ aa.code }}</span><span>{{ aa.percent }}%</span></span><span class="aa-name">{{ aa.name }} · {{ aa.count }} residues</span>
              <span class="bar-track"><span class="bar-fill" style="--bar-width:{{ [aa.percent, 100]|min }}%"></span></span>
            </button>
            {% endfor %}
          </div>
          <p class="chart-detail" data-aa-detail>Choose an amino acid to inspect its count and share.</p>
          <p class="chart-note">Hydrophobic group: A, C, F, I, L, M, V, W, Y. GRAVY is the mean Kyte–Doolittle hydropathy score across the protein.</p>
        </div>
        {% else %}
        <div class="grid">
          <div class="metric"><span>Sequence length</span><strong>{{ item.stats.Length }} bp</strong></div>
          <div class="metric"><span>GC content</span><strong>{{ item.stats.GC_percent|round(2) }}%</strong></div>
          <div class="metric"><span>AT content</span><strong>{{ item.stats.AT_percent|round(2) }}%</strong></div>
          <div class="metric"><span>Complete ORFs · all six frames</span><strong>{{ item.orf_count }}</strong></div>
          <div class="metric"><span>DNA melting temperature (Tm)</span><strong>{% if item.melting_temperature_c is not none %}{{ item.melting_temperature_c|round(2) }} °C{% else %}Not estimated{% endif %}</strong></div>
        </div>
        <div class="subsection">
          <div class="section-title"><h3>Nucleotide composition</h3><span class="small-label">Count and share of sequence</span></div>
          <div class="base-grid">
            <div class="base-tile"><span class="base-symbol base-a">A</span><div><strong>Adenine [A] = {{ item.stats.A_count }}</strong><small>{{ item.stats.A_percent|round(2) }}% of bases</small></div></div>
            <div class="base-tile"><span class="base-symbol base-g">G</span><div><strong>Guanine [G] = {{ item.stats.G_count }}</strong><small>{{ item.stats.G_percent|round(2) }}% of bases</small></div></div>
            <div class="base-tile"><span class="base-symbol base-t">T</span><div><strong>Thymine [T] = {{ item.stats.T_count }}</strong><small>{{ item.stats.T_percent|round(2) }}% of bases</small></div></div>
            <div class="base-tile"><span class="base-symbol base-c">C</span><div><strong>Cytosine [C] = {{ item.stats.C_count }}</strong><small>{{ item.stats.C_percent|round(2) }}% of bases</small></div></div>
            <div class="base-tile"><span class="base-symbol base-n">N</span><div><strong>Unknown [N] = {{ item.stats.N_count }}</strong><small>{{ item.stats.N_percent|round(2) }}% of bases</small></div></div>
          </div>
          <div class="chart-card" style="margin-top:12px">
            <div class="small-label">Interactive base composition</div>
            <div class="bar-row" role="button" tabindex="0" data-label="Adenine [A]" data-count="{{ item.stats.A_count }}" data-percent="{{ item.stats.A_percent|round(2) }}" data-percent-context="of all bases"><span>Adenine [A]</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ item.stats.A_percent }}%"></span></span><span class="bar-value">{{ item.stats.A_count }} · {{ item.stats.A_percent|round(2) }}%</span></div>
            <div class="bar-row" role="button" tabindex="0" data-label="Guanine [G]" data-count="{{ item.stats.G_count }}" data-percent="{{ item.stats.G_percent|round(2) }}" data-percent-context="of all bases"><span>Guanine [G]</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ item.stats.G_percent }}%"></span></span><span class="bar-value">{{ item.stats.G_count }} · {{ item.stats.G_percent|round(2) }}%</span></div>
            <div class="bar-row" role="button" tabindex="0" data-label="Thymine [T]" data-count="{{ item.stats.T_count }}" data-percent="{{ item.stats.T_percent|round(2) }}" data-percent-context="of all bases"><span>Thymine [T]</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ item.stats.T_percent }}%"></span></span><span class="bar-value">{{ item.stats.T_count }} · {{ item.stats.T_percent|round(2) }}%</span></div>
            <div class="bar-row" role="button" tabindex="0" data-label="Cytosine [C]" data-count="{{ item.stats.C_count }}" data-percent="{{ item.stats.C_percent|round(2) }}" data-percent-context="of all bases"><span>Cytosine [C]</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ item.stats.C_percent }}%"></span></span><span class="bar-value">{{ item.stats.C_count }} · {{ item.stats.C_percent|round(2) }}%</span></div>
            <div class="bar-row" role="button" tabindex="0" data-label="Unknown [N]" data-count="{{ item.stats.N_count }}" data-percent="{{ item.stats.N_percent|round(2) }}" data-percent-context="of all bases"><span>Unknown [N]</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ item.stats.N_percent }}%"></span></span><span class="bar-value">{{ item.stats.N_count }} · {{ item.stats.N_percent|round(2) }}%</span></div>
            <p class="chart-detail" data-chart-detail>Choose a bar to inspect its count and percentage.</p>
          </div>
          <p class="muted"><strong>GC skew:</strong> {{ item.gc_skew|round(4) }} &nbsp; <strong>AT skew:</strong> {{ item.at_skew|round(4) }} &nbsp; <strong>Valid DNA/RNA:</strong> {{ "Yes" if item.valid else "No" }}{% if item.invalid_bases %} · Unexpected letters: {{ item.invalid_bases|join(", ") }}{% endif %}</p>
          <p class="chart-note">RNA U bases are counted as T in the requested A/T/G/C/N summary. DNA Tm is a nearest-neighbor estimate at 50 mM Na⁺, shown for unambiguous sequences 8–1,000 bases long; other lengths or ambiguous bases are labeled “Not estimated”.</p>
        </div>
        <div class="subsection">
          <div class="section-title"><h3>DNA → protein translation</h3><span class="small-label">Three frames on each strand</span></div>
          {% set record_index = loop.index %}
          <div class="frame-tabs" role="tablist" aria-label="Select a translation reading frame">
            {% for frame, translated in item.translation_frames.items() %}
            <button type="button" class="frame-tab" data-record="{{ record_index }}" data-frame="{{ frame }}" aria-selected="{{ 'true' if loop.first else 'false' }}">{{ frame }}</button>
            {% endfor %}
          </div>
          {% for frame, translated in item.translation_frames.items() %}
          {% set frame_dom_id = frame|replace('+','p')|replace('-','m') %}
          <div class="translation-panel" data-record="{{ record_index }}" data-frame="{{ frame }}" {% if not loop.first %}hidden{% endif %}>
            <div class="small-label">Frame {{ frame }} · amino acids ( * = stop )</div>
            <code class="translation-sequence">{{ translated if translated else 'No translatable sequence in this frame.' }}</code>
          </div>
          {% endfor %}
          {% if item.translation_truncated %}<p class="chart-note">Translation is shown for the first 30,000 nucleotides per strand to keep large files responsive.</p>{% endif %}
        </div>
        <div class="subsection">
          <div class="section-title"><h3>Six-frame ORF scan</h3><span class="small-label">Complete ATG → in-frame stop · minimum 90 bp</span></div>
          <div class="frame-tabs" aria-label="ORFs detected per reading frame">
            {% for frame in ['+1', '+2', '+3', '-1', '-2', '-3'] %}
            {% set frame_orf_count = item.orfs|selectattr('Frame', 'equalto', frame)|list|length %}
            <span class="tag">{{ frame }} · {{ frame_orf_count }}</span>
            {% endfor %}
          </div>
          {% if item.orfs %}
            <label class="small-label" for="orf-filter-{{ record_index }}">Filter ORFs by frame</label>
            <select id="orf-filter-{{ record_index }}" class="orf-filter"><option value="all">All six frames</option>{% for frame in ['+1', '+2', '+3', '-1', '-2', '-3'] %}<option value="{{ frame }}">Frame {{ frame }}</option>{% endfor %}</select>
            {% for orf in item.orfs %}
            <details class="orf" data-orf-frame="{{ orf.Frame }}"><summary><strong>ORF {{ loop.index }}</strong> · Frame {{ orf.Frame }} · Forward coordinates {{ orf.Start }}–{{ orf.End }} · {{ orf.Length }} bp</summary><div class="grid" style="margin-top:12px"><div class="metric"><span>Translated peptide length</span><strong>{{ orf.Protein_Length }} aa</strong></div>{% if orf.Molecular_Weight is not none %}<div class="metric"><span>Peptide molecular weight</span><strong>{{ orf.Molecular_Weight|round(2) }} Da</strong></div><div class="metric"><span>Peptide isoelectric point</span><strong>{{ orf.Isoelectric_Point|round(2) }} pI</strong></div><div class="metric"><span>Peptide GRAVY</span><strong>{{ orf.GRAVY|round(3) }}</strong></div>{% else %}<div class="metric"><span>Peptide properties</span><strong>Ambiguous codon</strong></div>{% endif %}</div><p class="chart-note">Translated peptide: <code class="translation-sequence">{{ orf.Protein }}</code></p></details>
            {% endfor %}
          {% else %}
            <p class="muted">All six reading frames were scanned. No complete ATG-to-stop ORF of at least 90 bp was found.</p>
          {% endif %}
        </div>
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
      <div class="chart-card interactive-bars" aria-label="Interactive read-length chart">
      {% set max_reads = result.read_length_distribution.values()|max %}
      {% for length, count in result.read_length_distribution.items() %}
        <div class="bar-row" role="button" tabindex="0" data-label="Read length {{ length }} bp" data-count="{{ count }}" data-percent="{{ (count / max_reads * 100)|round(2) }}" data-percent-context="of the largest length bin"><span>{{ length }} bp</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ (count / max_reads * 100)|round(2) }}%"></span></span><span class="bar-value">{{ count }} reads</span></div>
      {% endfor %}
      <p class="chart-detail" data-chart-detail>Choose a bar to inspect the read count.</p>
      </div>
      <table><thead><tr><th>Read length (bp)</th><th>Number of reads</th></tr></thead><tbody>
      {% for length, count in result.read_length_distribution.items() %}<tr><td>{{ length }}</td><td>{{ count }}</td></tr>{% endfor %}
      </tbody></table>
      <div class="chart-card subsection">
        <div class="section-title"><h3>Mean quality by read position</h3><span class="small-label">Interactive Phred score curve</span></div>
        <svg class="quality-chart" data-values='{{ result.quality_by_position|tojson }}' viewBox="0 0 900 180" role="img" aria-label="Mean base quality at each read position"></svg>
        <p class="chart-detail" data-quality-detail>Hover or focus a point to inspect mean quality by position.</p>
      </div>
      <p class="muted">Per-position mean quality is calculated for {{ result.quality_by_position|length }} read positions. Adapter detection is a future module.</p>

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
      <div class="chart-grid subsection">
        <div class="chart-card interactive-bars"><div class="section-title"><h3>Variant classes</h3><span class="small-label">Alternate alleles</span></div>
          {% set variant_classes = [('SNP', result.snp_count), ('Insertions', result.insertion_count), ('Deletions', result.deletion_count), ('MNV', result.mnv_count), ('Other', result.complex_count)] %}
          {% set max_class = [result.snp_count, result.insertion_count, result.deletion_count, result.mnv_count, result.complex_count]|max %}
          {% for label, count in variant_classes %}<div class="bar-row" role="button" tabindex="0" data-label="{{ label }}" data-count="{{ count }}" data-percent="{{ (count / max_class * 100 if max_class else 0)|round(2) }}" data-percent-context="of the largest variant class"><span>{{ label }}</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ (count / max_class * 100 if max_class else 0)|round(2) }}%"></span></span><span class="bar-value">{{ count }}</span></div>{% endfor %}
          <p class="chart-detail" data-chart-detail>Select a class to inspect its alternate-allele count.</p>
        </div>
        <div class="chart-card interactive-bars"><div class="section-title"><h3>Variants by contig</h3><span class="small-label">Variant records</span></div>
          {% set max_contig = result.chromosome_distribution.values()|max %}
          {% for contig, count in result.chromosome_distribution.items() %}<div class="bar-row" role="button" tabindex="0" data-label="{{ contig }}" data-count="{{ count }}" data-percent="{{ (count / max_contig * 100)|round(2) }}" data-percent-context="of the most variant-rich contig"><span>{{ contig }}</span><span class="bar-track"><span class="bar-fill" style="--bar-width:{{ (count / max_contig * 100)|round(2) }}%"></span></span><span class="bar-value">{{ count }} records</span></div>{% endfor %}
          <p class="chart-detail" data-chart-detail>Select a contig to inspect its variant-record count.</p>
        </div>
      </div>
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

    document.querySelectorAll('.frame-tab').forEach((button) => {
      button.addEventListener('click', () => {
        const { record, frame } = button.dataset;
        document.querySelectorAll(`.frame-tab[data-record="${record}"]`).forEach((tab) => tab.setAttribute('aria-selected', String(tab === button)));
        document.querySelectorAll(`.translation-panel[data-record="${record}"]`).forEach((panel) => {
          panel.hidden = panel.dataset.frame !== frame;
        });
      });
    });

    document.querySelectorAll('.aa-filters').forEach((filters) => {
      const record = filters.closest('.record');
      filters.querySelectorAll('[data-aa-filter]').forEach((button) => button.addEventListener('click', () => {
        filters.querySelectorAll('[data-aa-filter]').forEach((filter) => filter.setAttribute('aria-pressed', String(filter === button)));
        record.querySelectorAll('.aa-card').forEach((card) => {
          card.hidden = button.dataset.aaFilter !== 'all' && card.dataset.aaClass !== button.dataset.aaFilter;
        });
      }));
    });

    document.querySelectorAll('.aa-card').forEach((card) => card.addEventListener('click', () => {
      card.closest('.record').querySelectorAll('.aa-card').forEach((item) => item.setAttribute('aria-pressed', String(item === card)));
      const detail = card.closest('.record').querySelector('[data-aa-detail]');
      detail.textContent = `${card.dataset.aaName} [${card.dataset.aaCode}]: ${card.dataset.aaCount} residues (${card.dataset.aaPercent}% of this protein). Group: ${card.dataset.aaClass}.`;
    }));

    const inspectBar = (bar) => {
      const chart = bar.closest('.chart-card');
      if (!chart) return;
      chart.querySelectorAll('.bar-row').forEach((row) => row.setAttribute('aria-pressed', String(row === bar)));
      const detail = chart.querySelector('[data-chart-detail]');
      if (detail) detail.textContent = `${bar.dataset.label}: ${bar.dataset.count} (${bar.dataset.percent}% ${bar.dataset.percentContext || 'relative to the largest bar'}).`;
    };
    document.querySelectorAll('.bar-row[role="button"]').forEach((bar) => {
      bar.addEventListener('click', () => inspectBar(bar));
      bar.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inspectBar(bar); }
      });
    });

    document.querySelectorAll('.orf-filter').forEach((filter) => filter.addEventListener('change', () => {
      const record = filter.closest('.record');
      record.querySelectorAll('[data-orf-frame]').forEach((orf) => {
        orf.hidden = filter.value !== 'all' && orf.dataset.orfFrame !== filter.value;
      });
    }));

    document.querySelectorAll('.quality-chart').forEach((svg) => {
      const values = JSON.parse(svg.dataset.values || '[]');
      if (!values.length) return;
      const ns = 'http://www.w3.org/2000/svg';
      const make = (name, attributes) => {
        const node = document.createElementNS(ns, name);
        Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
        return node;
      };
      const width = 900, height = 180, left = 42, right = 12, top = 12, bottom = 27;
      const x = (index) => left + index * (width - left - right) / Math.max(values.length - 1, 1);
      const y = (value) => height - bottom - Math.min(Math.max(value, 0), 45) / 45 * (height - top - bottom);
      [20, 30].forEach((score) => {
        svg.appendChild(make('line', {x1:left, x2:width-right, y1:y(score), y2:y(score), stroke:score === 20 ? '#efae57' : '#45c69d', 'stroke-dasharray':'5 6', opacity:'.7'}));
        const labelNode = make('text', {x:4, y:y(score)+4, fill:'#91a5b8', 'font-size':'11'});
        labelNode.textContent = `Q${score}`; svg.appendChild(labelNode);
      });
      const points = values.map((value, index) => `${x(index)},${y(value)}`).join(' ');
      svg.appendChild(make('polyline', {points, fill:'none', stroke:'#55cdbb', 'stroke-width':'3', 'stroke-linejoin':'round', 'stroke-linecap':'round'}));
      const detail = svg.parentElement.querySelector('[data-quality-detail]');
      values.forEach((value, index) => {
        const point = make('circle', {cx:x(index), cy:y(value), r:values.length > 150 ? '2.5' : '4', fill:'#8ae7d6', tabindex:'0', 'aria-label':`Position ${index+1}: mean quality ${value}`});
        const title = make('title', {}); title.textContent = `Position ${index+1} · mean Phred ${value}`; point.appendChild(title);
        const show = () => { detail.textContent = `Position ${index+1}: mean Phred score ${value}.`; };
        point.addEventListener('mouseenter', show); point.addEventListener('focus', show); point.addEventListener('click', show);
        svg.appendChild(point);
      });
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
