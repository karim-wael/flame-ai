"""Self-contained interactive FLARE AI Dashboard served directly at http://localhost:8000/."""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FLARE AI — Microgravity Combustion & Hybrid Knowledge Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body { background-color: #07090e; color: #f1f5f9; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #0d121d; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
  </style>
</head>
<body class="min-h-screen flex flex-col selection:bg-orange-500/30">
  <!-- Top Scientific Guardrail Banner -->
  <div class="border-b border-orange-500/30 bg-gradient-to-r from-orange-950/70 via-slate-900 to-cyan-950/70 px-6 py-2 text-xs text-orange-200 flex flex-wrap items-center justify-between gap-2">
    <div class="flex items-center gap-2">
      <span class="rounded bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold uppercase text-black">Decision-Support Prototype</span>
      <span><strong>FLARE AI</strong> — NASA Space Apps Challenge 2026 (Flame in Freefall). Research/decision-support prototype, NOT a certified spacecraft fire-safety system.</span>
    </div>
    <div class="flex items-center gap-3 font-mono text-[11px]">
      <a href="/docs" target="_blank" class="text-cyan-300 hover:underline">OpenAPI / Swagger (/docs) ↗</a>
      <span class="text-slate-400">|</span>
      <a href="/api/health" target="_blank" class="text-emerald-300 hover:underline">Health JSON ↗</a>
    </div>
  </div>

  <!-- Header -->
  <header class="border-b border-slate-800/80 bg-[#0a0e17]/95 sticky top-0 z-20 px-6 py-4">
    <div class="mx-auto max-w-7xl flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 font-bold text-black shadow-lg shadow-orange-500/20">FL</div>
        <div>
          <h1 class="text-lg font-bold tracking-tight text-white">FLARE AI — Microgravity Combustion & Hybrid Knowledge Platform</h1>
          <p class="text-xs text-slate-400">NASA PSI (P0/P1) • JAXA DARTS Kibo GCE (P1) • UL FSRI MaP 1g Baseline (P2) • Hybrid RAG + SQL</p>
        </div>
      </div>

      <nav class="flex flex-wrap items-center gap-2" id="nav-tabs">
        <button onclick="switchTab('explorer')" id="tab-btn-explorer" class="rounded-lg px-3.5 py-2 text-xs font-semibold transition bg-orange-500 text-black shadow-md">1. Experiment Explorer</button>
        <button onclick="switchTab('compare')" id="tab-btn-compare" class="rounded-lg px-3.5 py-2 text-xs font-semibold transition bg-slate-900 text-slate-300 border border-slate-800 hover:border-slate-700">2. Domain-Gated Comparison</button>
        <button onclick="switchTab('assistant')" id="tab-btn-assistant" class="rounded-lg px-3.5 py-2 text-xs font-semibold transition bg-slate-900 text-slate-300 border border-slate-800 hover:border-slate-700">3. Hybrid RAG Assistant</button>
        <button onclick="switchTab('ingestion')" id="tab-btn-ingestion" class="rounded-lg px-3.5 py-2 text-xs font-semibold transition bg-slate-900 text-slate-300 border border-slate-800 hover:border-slate-700">4. Ingestion & Provenance Pipeline</button>
      </nav>
    </div>
  </header>

  <main class="mx-auto w-full max-w-7xl flex-1 px-6 py-6">
    <!-- TAB 1: EXPLORER -->
    <section id="tab-explorer" class="space-y-6">
      <div class="grid gap-3 rounded-xl border border-slate-800 bg-[#0d121d] p-4 sm:grid-cols-4">
        <div>
          <label class="block text-[11px] font-semibold uppercase text-slate-400">Publisher / Source</label>
          <select id="exp-source" onchange="loadInvestigations()" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100">
            <option value="">All Registered Publishers (3)</option>
            <option value="NASA PSI">NASA PSI (Primary — P0/P1)</option>
            <option value="JAXA DARTS">JAXA DARTS Kibo GCE (External 0g — P1)</option>
            <option value="UL FSRI">UL FSRI MaP (Earth 1g Baseline — P2)</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase text-slate-400">Combustion Domain</label>
          <select id="exp-domain" onchange="loadInvestigations()" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100">
            <option value="">All Combustion Domains</option>
            <option value="solid">solid (BASS-II, SAFFIRE-I, FSRI)</option>
            <option value="gas">gas (SPICE Co-flow Jets)</option>
            <option value="liquid_droplet">liquid_droplet (FLEX, JAXA Kibo GC)</option>
            <option value="aerosol_smoke">aerosol_smoke (SAME, SAME-R)</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase text-slate-400">Gravity Regime</label>
          <select id="exp-gravity" onchange="loadInvestigations()" class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100">
            <option value="">All Gravity Regimes</option>
            <option value="microgravity">microgravity (ISS / Cygnus / Kibo 0g)</option>
            <option value="normal_gravity">normal_gravity (Earth 1g Baseline)</option>
          </select>
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase text-slate-400">Search Investigations</label>
          <input id="exp-search" oninput="loadInvestigations()" type="text" placeholder="PSI-25, BASS-II, SPICE, n-decane..." class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100" />
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-12">
        <div class="lg:col-span-4 space-y-3" id="inv-list"></div>
        <div class="lg:col-span-8" id="inv-detail"></div>
      </div>
    </section>

    <!-- TAB 2: COMPARE -->
    <section id="tab-compare" class="hidden space-y-6">
      <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 class="text-base font-bold text-white">Domain-Gated Explainable Similarity Ranking Engine</h2>
            <p class="text-xs text-slate-400">Formula: <code class="text-orange-300">D(S, E_i) = √[ w₁(ΔO₂)² + w₂(ΔP)² + w₃(ΔV_air)² ]</code> — Blocks incompatible domains by default & isolates 1g FSRI baselines</p>
          </div>
          <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input type="checkbox" id="cmp-baseline" checked onchange="runComparison()" class="rounded border-slate-700 bg-slate-900" />
            Show Separated Earth-Based 1g Reference Track (FSRI MaP)
          </label>
        </div>

        <div class="mt-4 grid gap-4 sm:grid-cols-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300">1. Target Combustion Domain Gate</label>
            <select id="cmp-domain" onchange="runComparison()" class="mt-1.5 w-full rounded-lg border border-orange-500/50 bg-slate-900 px-3 py-2 text-xs font-semibold text-orange-300">
              <option value="solid">solid (BASS-II, SAFFIRE-I)</option>
              <option value="gas">gas (SPICE Laminar Jets)</option>
              <option value="liquid_droplet">liquid_droplet (FLEX & JAXA Kibo GC)</option>
              <option value="aerosol_smoke">aerosol_smoke (SAME & SAME-R)</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300">2. Target Oxygen: <span id="lbl-o2" class="font-mono text-cyan-300">21.0% O₂</span></label>
            <input id="cmp-o2" type="range" min="0.16" max="0.30" step="0.005" value="0.21" oninput="document.getElementById('lbl-o2').textContent=(this.value*100).toFixed(1)+'% O₂'; runComparison();" class="mt-2 w-full accent-orange-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300">3. Target Pressure: <span id="lbl-p" class="font-mono text-cyan-300">101.3 kPa</span></label>
            <input id="cmp-p" type="range" min="65" max="125" step="0.5" value="101.3" oninput="document.getElementById('lbl-p').textContent=parseFloat(this.value).toFixed(1)+' kPa'; runComparison();" class="mt-2 w-full accent-orange-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300">4. Target Flow V_air: <span id="lbl-v" class="font-mono text-cyan-300">8.0 cm/s</span></label>
            <input id="cmp-v" type="range" min="0.5" max="25" step="0.5" value="8.0" oninput="document.getElementById('lbl-v').textContent=parseFloat(this.value).toFixed(1)+' cm/s'; runComparison();" class="mt-2 w-full accent-orange-500" />
          </div>
        </div>
      </div>

      <!-- Plotly Interactive Chart + Provenance -->
      <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div>
            <h3 class="text-sm font-bold text-white">Interactive Scientific Plot (Flow Velocity vs. Domain Outcome & Closeness)</h3>
            <p class="text-xs text-slate-400">0g ISS/Spacecraft microgravity runs vs. 1g Earth reference track — Missing values are explicitly listed below and never plotted as 0</p>
          </div>
        </div>
        <div id="plotly-chart" class="w-full h-[360px] rounded-lg bg-[#080b12] border border-slate-800"></div>
        <div id="chart-missing-guardrail" class="mt-3"></div>
        <div id="chart-provenance-footer" class="mt-4 border-t border-slate-800 pt-3"></div>
      </div>

      <div id="cmp-results" class="space-y-6"></div>
    </section>

    <!-- TAB 3: HYBRID RAG ASSISTANT -->
    <section id="tab-assistant" class="hidden space-y-6">
      <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
        <h2 class="text-base font-bold text-white">FLARE AI Hybrid Knowledge Research Assistant (Semantic Vector + Keyword + PostgreSQL SQL)</h2>
        <p class="text-xs text-slate-400 mt-0.5">Retrieves published scientific chunks from the Knowledge Base + structured experiments from PostgreSQL, and separates <strong>Published Findings</strong> from <strong>Generated Interpretation</strong>.</p>

        <div class="mt-3 flex flex-wrap gap-2" id="preset-questions"></div>

        <div class="mt-4 flex flex-wrap gap-3">
          <input id="rag-input" type="text" value="Why does flame spread behave differently in microgravity?" class="flex-1 min-w-[260px] rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white" />
          <select id="rag-domain" class="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200">
            <option value="">All Domains</option>
            <option value="solid">solid</option>
            <option value="gas">gas</option>
            <option value="liquid_droplet">liquid_droplet</option>
            <option value="aerosol_smoke">aerosol_smoke</option>
          </select>
          <button onclick="runAssistant()" class="rounded-lg bg-orange-500 px-5 py-2.5 text-xs font-bold text-black hover:bg-orange-400">Run Hybrid RAG + SQL Query</button>
        </div>
      </div>

      <div id="rag-output" class="space-y-6"></div>
    </section>

    <!-- TAB 4: INGESTION & PROVENANCE PIPELINE -->
    <section id="tab-ingestion" class="hidden space-y-6">
      <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 class="text-base font-bold text-white">7-Stage Scientific Ingestion Pipeline & Canonical Field Mappings</h2>
          <p class="text-xs text-slate-400">1. Discover → 2. Acquire (Raw SHA-256) → 3. Parse → 4. Normalize → 5. Validate → 6. Publish → 7. Audit</p>
        </div>
        <button onclick="triggerReingestion()" id="btn-reingest" class="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-bold text-black hover:bg-emerald-400">Trigger Verified Re-Ingestion Job</button>
      </div>
      <div id="ingestion-job-status"></div>
      <div id="sources-list" class="grid gap-4"></div>
    </section>
  </main>

  <!-- Provenance Modal -->
  <div id="prov-modal" class="fixed inset-0 z-50 hidden items-center justify-center bg-black/75 p-4">
    <div class="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-cyan-500/40 bg-[#0d121d] p-6 shadow-2xl">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 class="text-base font-bold text-cyan-300">Record Provenance, SHA-256 Checksum & Transformation Audit Trail</h3>
        <button onclick="closeProvenance()" class="rounded-lg bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200 hover:bg-slate-700">Close ✕</button>
      </div>
      <pre id="prov-json" class="mt-4 overflow-x-auto rounded-lg bg-slate-950 p-4 font-mono text-xs text-slate-200"></pre>
    </div>
  </div>

  <script>
    const PRESETS = [
      "Why does flame spread behave differently in microgravity?",
      "How do liquid droplets burn and extinguish in FLEX (PSI-69) vs JAXA Kibo Group Combustion?",
      "How do smoke aerosol particle sizes in SAME and SAME-R affect spacecraft fire detection?",
      "How do co-flow velocity and burner diameter affect soot smoke points in SPICE (PSI-107)?",
      "Why must Earth-based FSRI 1g cone calorimeter data be kept separate from ISS microgravity rankings?"
    ];

    let selectedExtId = "PSI-25";

    function switchTab(tab) {
      ["explorer", "compare", "assistant", "ingestion"].forEach(t => {
        document.getElementById("tab-" + t).classList.toggle("hidden", t !== tab);
        const btn = document.getElementById("tab-btn-" + t);
        if (t === tab) {
          btn.className = "rounded-lg px-3.5 py-2 text-xs font-semibold transition bg-orange-500 text-black shadow-md";
        } else {
          btn.className = "rounded-lg px-3.5 py-2 text-xs font-semibold transition bg-slate-900 text-slate-300 border border-slate-800 hover:border-slate-700";
        }
      });
      if (tab === "compare") runComparison();
      if (tab === "assistant") runAssistant();
      if (tab === "ingestion") loadSources();
    }

    async function loadInvestigations() {
      const source = document.getElementById("exp-source").value;
      const domain = document.getElementById("exp-domain").value;
      const gravity = document.getElementById("exp-gravity").value;
      const search = document.getElementById("exp-search").value;
      const params = new URLSearchParams();
      if (source) params.set("source", source);
      if (domain) params.set("domain", domain);
      if (gravity) params.set("gravity", gravity);
      if (search) params.set("search", search);

      const res = await fetch("/api/investigations?" + params.toString());
      const list = await res.json();
      const container = document.getElementById("inv-list");
      container.innerHTML = `<div class="flex items-center justify-between text-xs text-slate-400 px-1"><span>Verified Investigations (${list.length})</span><span>Priority P0–P2</span></div>` +
        list.map(inv => `
          <button onclick="selectInvestigation('${inv.external_id}')" class="w-full text-left rounded-xl border p-4 transition ${selectedExtId === inv.external_id ? 'border-orange-500 bg-orange-950/20' : 'border-slate-800 bg-[#0d121d] hover:border-slate-700'}">
            <div class="flex items-center justify-between gap-2">
              <span class="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs font-bold text-orange-300">${inv.external_id}</span>
              <span class="rounded bg-slate-800/90 px-2 py-0.5 text-[11px] font-medium text-slate-300">${inv.publisher} • ${inv.priority}</span>
            </div>
            <h3 class="mt-2 text-sm font-semibold text-white">${inv.title}</h3>
            <div class="mt-2 flex flex-wrap gap-1.5">
              <span class="rounded border border-orange-500/30 bg-orange-500/10 px-2 py-0.5 text-[10px] text-orange-300">domain: ${inv.combustion_domain}</span>
              <span class="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300">gravity: ${inv.gravity_regime}</span>
            </div>
            <div class="mt-2 flex items-center justify-between text-[11px] text-slate-400">
              <span>${inv.doi ? 'DOI: ' + inv.doi : 'External Archive Link'}</span>
              <span>${inv.run_count} runs</span>
            </div>
          </button>
        `).join("");

      if (list.length > 0) {
        if (!list.some(i => i.external_id === selectedExtId)) selectedExtId = list[0].external_id;
        selectInvestigation(selectedExtId, false);
      }
    }

    async function selectInvestigation(extId, reloadList = true) {
      selectedExtId = extId;
      if (reloadList) loadInvestigations();
      const res = await fetch("/api/investigations/" + extId);
      const inv = await res.json();
      const el = document.getElementById("inv-detail");
      el.innerHTML = `
        <div class="space-y-5 rounded-xl border border-slate-800 bg-[#0d121d] p-5">
          <div class="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="rounded bg-orange-500/20 border border-orange-500/40 px-2.5 py-0.5 font-mono text-xs font-bold text-orange-300">${inv.external_id}</span>
                <span class="rounded border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-0.5 text-xs text-cyan-300">${inv.combustion_domain}</span>
                <span class="rounded border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-300">${inv.gravity_regime}</span>
                ${inv.domain_track === 'terrestrial_baseline' ? '<span class="rounded border border-amber-500/50 bg-amber-500/20 px-2.5 py-0.5 text-xs font-semibold text-amber-300">Earth-Based 1g Reference Track</span>' : ''}
              </div>
              <h2 class="mt-2 text-lg font-bold text-white">${inv.title}</h2>
              <p class="mt-1 text-xs text-slate-400">Platform: <strong class="text-slate-200">${inv.platform}</strong> • Version: <span class="font-mono text-slate-300">${inv.version}</span></p>
            </div>
            <div class="flex flex-col items-end gap-1.5">
              <a href="${inv.source_url}" target="_blank" class="rounded-lg border border-orange-500/40 bg-orange-500/10 px-3 py-1.5 text-xs font-semibold text-orange-300 hover:bg-orange-500/20">Official Source Repository ↗</a>
              ${inv.doi ? `<span class="font-mono text-[11px] text-cyan-300">DOI: ${inv.doi}</span>` : ''}
            </div>
          </div>

          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Verified Source Files & SHA-256 Checksums</h4>
            <div class="mt-2 grid gap-2">
              ${inv.source_files.map(sf => `
                <div class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-3.5 py-2 text-xs">
                  <div><span class="font-mono font-semibold text-cyan-300">${sf.file_name}</span> <span class="text-slate-400">(${sf.file_role}, ${sf.file_size} bytes, ${sf.version})</span></div>
                  <div class="font-mono text-[11px] text-emerald-400">SHA-256: ${sf.checksum_sha256.slice(0, 24)}…</div>
                </div>
              `).join("")}
            </div>
          </div>

          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Experiment Runs, Canonical Units & Explicit Missingness (${inv.experiment_runs.length})</h4>
            <div class="mt-2.5 space-y-3">
              ${inv.experiment_runs.map(run => `
                <div class="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded bg-slate-800 px-2.5 py-1 font-mono text-xs font-bold text-white">${run.run_code}</span>
                      <span class="text-sm font-semibold text-orange-300">${run.fuel_material}</span>
                      <span class="text-xs text-slate-400">(${run.burner_or_sample_geometry || ''})</span>
                    </div>
                    <button onclick="openProvenance('${run.run_code}')" class="rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-1 text-xs font-medium text-cyan-300 hover:bg-cyan-500/20">Inspect Provenance & Audit Trail</button>
                  </div>
                  <div class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 text-xs">
                    <div class="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                      <span class="text-[10px] uppercase text-slate-400">Oxygen Fraction</span>
                      <div class="mt-0.5 font-mono text-slate-200">${run.oxygen_fraction !== null ? `${run.oxygen_fraction} (${(run.oxygen_fraction*100).toFixed(1)}%)` : `<span class="text-rose-400">NULL (${run.oxygen_missing_reason})</span>`}</div>
                    </div>
                    <div class="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                      <span class="text-[10px] uppercase text-slate-400">Pressure (Orig → Canonical)</span>
                      <div class="mt-0.5 font-mono text-slate-200">${run.pressure_normalized_kpa !== null ? `${run.pressure_value} ${run.pressure_unit} → ${run.pressure_normalized_kpa} kPa` : `<span class="text-rose-400">NULL (${run.pressure_missing_reason})</span>`}</div>
                    </div>
                    <div class="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                      <span class="text-[10px] uppercase text-slate-400">Flow Velocity (Orig → Canonical)</span>
                      <div class="mt-0.5 font-mono text-slate-200">${run.flow_velocity_normalized_cm_s !== null ? `${run.flow_velocity_value} ${run.flow_velocity_unit} → ${run.flow_velocity_normalized_cm_s} cm/s` : `<span class="text-rose-400">NULL (${run.flow_velocity_missing_reason})</span>`}</div>
                    </div>
                    <div class="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                      <span class="text-[10px] uppercase text-slate-400">Gravity & Orientation</span>
                      <div class="mt-0.5 font-mono text-slate-200">${run.gravity_regime} • ${run.sample_orientation || ''}</div>
                    </div>
                  </div>
                  <div class="mt-3 overflow-x-auto">
                    <table class="w-full text-left text-xs">
                      <thead>
                        <tr class="border-b border-slate-800 text-[11px] text-slate-400">
                          <th class="py-1.5 pr-3">Canonical Field</th>
                          <th class="py-1.5 pr-3">Original Value</th>
                          <th class="py-1.5 pr-3">Canonical Normalized</th>
                          <th class="py-1.5 pr-3">Status / Missing Reason</th>
                          <th class="py-1.5">Method / Notes</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-800/60">
                        ${run.measurements.map(m => `
                          <tr>
                            <td class="py-1.5 pr-3 font-mono font-semibold text-cyan-300">${m.canonical_field}</td>
                            <td class="py-1.5 pr-3 font-mono text-slate-200">${m.value_numeric !== null ? `${m.value_numeric} ${m.unit || ''}` : 'NULL'}</td>
                            <td class="py-1.5 pr-3 font-mono text-emerald-300">${m.normalized_value !== null ? `${m.normalized_value} ${m.normalized_unit || ''}${m.uncertainty ? ` (±${m.uncertainty})` : ''}` : 'NULL'}</td>
                            <td class="py-1.5 pr-3">${m.value_status === 'measured' ? '<span class="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-300">measured</span>' : `<span class="rounded bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 text-[10px] font-semibold text-rose-300">${m.value_status}: ${m.missing_reason}</span>`}</td>
                            <td class="py-1.5 text-slate-400">${m.measurement_method || m.notes || ''}</td>
                          </tr>
                        `).join("")}
                      </tbody>
                    </table>
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        </div>
      `;
    }

    async function runComparison() {
      const target_domain = document.getElementById("cmp-domain").value;
      const oxygen_fraction = parseFloat(document.getElementById("cmp-o2").value);
      const pressure_kpa = parseFloat(document.getElementById("cmp-p").value);
      const flow_velocity_cm_s = parseFloat(document.getElementById("cmp-v").value);
      const include_terrestrial_baseline = document.getElementById("cmp-baseline").checked;

      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_domain,
          target_gravity: "microgravity",
          oxygen_fraction,
          pressure_kpa,
          flow_velocity_cm_s,
          include_terrestrial_baseline
        })
      });
      const data = await res.json();

      // Render Plotly chart
      const outcomeMap = {
        solid: { field: "flame_spread_rate", label: "Flame Spread Rate (mm/s)" },
        gas: { field: "flame_height", label: "Flame Length (mm)" },
        liquid_droplet: { field: "burning_rate", label: "Burning Rate Constant K (mm²/s)" },
        aerosol_smoke: { field: "smoke_particle_size", label: "Smoke Count Median Diameter (µm)" }
      };
      const activeOut = outcomeMap[target_domain] || outcomeMap.solid;

      const mgValid = [];
      const missingList = [];
      data.compatible_microgravity_ranking.forEach(item => {
        const m = item.outcomes.find(o => o.canonical_field === activeOut.field);
        const yVal = m ? m.normalized_value : null;
        if (item.flow_velocity_normalized_cm_s !== null && yVal !== null) {
          mgValid.push({ item, x: item.flow_velocity_normalized_cm_s, y: yVal, unc: m.uncertainty || 0 });
        } else {
          missingList.push({
            code: item.run_code,
            reason: (m && m.missing_reason) || (item.missing_features[0] && item.missing_features[0].missing_reason) || "unavailable_in_source"
          });
        }
      });

      const baseValid = [];
      data.terrestrial_baseline_track.forEach(item => {
        const m = item.outcomes.find(o => o.canonical_field === activeOut.field);
        const yVal = m ? m.normalized_value : null;
        if (item.flow_velocity_normalized_cm_s !== null && yVal !== null) {
          baseValid.push({ item, x: item.flow_velocity_normalized_cm_s, y: yVal, unc: m.uncertainty || 0 });
        }
      });

      const traces = [
        {
          name: "ISS / Spacecraft Microgravity (0g)",
          x: mgValid.map(p => p.x),
          y: mgValid.map(p => p.y),
          text: mgValid.map(p => `${p.item.run_code} (${p.item.investigation_external_id}) • ${p.item.fuel_material} • D=${p.item.distance_d}`),
          mode: "markers+text",
          textposition: "top center",
          marker: { size: 11, color: "#06b6d4", line: { width: 1.5, color: "#cffafe" } },
          error_y: { type: "data", array: mgValid.map(p => p.unc), visible: true, color: "#38bdf8" }
        }
      ];

      if (include_terrestrial_baseline && baseValid.length > 0) {
        traces.push({
          name: "Terrestrial Reference Baseline (1g FSRI / Ground)",
          x: baseValid.map(p => p.x),
          y: baseValid.map(p => p.y),
          text: baseValid.map(p => `${p.item.run_code} (1g Baseline)`),
          mode: "markers+text",
          textposition: "bottom center",
          marker: { symbol: "square", size: 11, color: "#f59e0b", line: { width: 1.5, color: "#fef3c7" } }
        });
      }

      if (window.Plotly) {
        Plotly.newPlot("plotly-chart", traces, {
          paper_bgcolor: "#080b12",
          plot_bgcolor: "#080b12",
          font: { color: "#cbd5e1", size: 11 },
          margin: { t: 25, r: 25, b: 45, l: 55 },
          xaxis: { title: "Forced Oxidizer Flow Velocity V_air (cm/s, Canonical Normalized)", gridcolor: "#1e293b" },
          yaxis: { title: activeOut.label, gridcolor: "#1e293b" },
          legend: { orientation: "h", y: 1.12 }
        }, { responsive: true, displayModeBar: false });
      }

      document.getElementById("chart-missing-guardrail").innerHTML = missingList.length > 0 ? `
        <div class="rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-200">
          <strong>Explicit Missing-Value Guardrail:</strong> ${missingList.map(m => `<span class="font-mono">${m.code}</span> (missing_reason: <span class="underline">${m.reason}</span>)`).join(", ")} omitted from X/Y coordinates — never silently converted to 0.
        </div>
      ` : "";

      const uniqueInvs = {};
      [...data.compatible_microgravity_ranking, ...data.terrestrial_baseline_track].forEach(r => {
        uniqueInvs[r.investigation_external_id] = r;
      });
      document.getElementById("chart-provenance-footer").innerHTML = `
        <div class="text-[11px] font-semibold uppercase text-slate-400 mb-2">Supporting Investigations, DOIs & Source Files for This Plot</div>
        <div class="grid gap-2 sm:grid-cols-2">
          ${Object.values(uniqueInvs).map(u => `
            <div class="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 text-xs">
              <div>
                <span class="font-mono font-bold text-cyan-300">${u.investigation_external_id}</span> (${u.publisher}) • File: <span class="font-mono text-slate-300">${u.source_file_name}</span>
              </div>
              <a href="${u.source_url}" target="_blank" class="text-orange-300 hover:underline">${u.doi ? 'DOI: ' + u.doi : 'Archive ↗'}</a>
            </div>
          `).join("")}
        </div>
      `;

      document.getElementById("cmp-results").innerHTML = `
        <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
          <h3 class="text-sm font-bold text-white">Compatible Microgravity Ranking (${data.compatible_microgravity_ranking.length} runs in <span class="text-orange-400">${target_domain}</span> domain)</h3>
          <div class="mt-3 space-y-2.5">
            ${data.compatible_microgravity_ranking.map(item => `
              <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-3.5 flex flex-wrap items-center justify-between gap-4">
                <div class="space-y-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="rounded bg-orange-500 px-2 py-0.5 font-mono text-xs font-bold text-black">#${item.rank}</span>
                    <span class="font-mono text-sm font-bold text-white">${item.run_code}</span>
                    <span class="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-cyan-300">${item.investigation_external_id} (${item.publisher})</span>
                    <span class="text-xs font-semibold text-orange-300">${item.fuel_material}</span>
                    ${item.missing_features.map(mf => `<span class="rounded border border-rose-500/40 bg-rose-950/40 px-2 py-0.5 text-[10px] text-rose-300">Missing ${mf.feature}: ${mf.missing_reason}</span>`).join("")}
                  </div>
                  <p class="text-xs text-slate-300">${item.explanation}</p>
                </div>
                <div class="flex items-center gap-4">
                  <div class="text-right">
                    <div class="text-[10px] uppercase text-slate-400">Distance D(S, E_i)</div>
                    <div class="font-mono text-base font-bold text-cyan-300">${item.distance_d}</div>
                    <div class="text-[11px] text-emerald-400">Closeness: ${item.condition_closeness_index}/100</div>
                  </div>
                  <button onclick="openProvenance('${item.run_code}')" class="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:border-cyan-500/50">Provenance</button>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="rounded-xl border border-rose-500/30 bg-rose-950/10 p-5">
          <h3 class="text-sm font-bold text-rose-300">Domain Gate Audit: Excluded Incompatible Combustion Domains (${data.excluded_incompatible_domains.length} runs blocked)</h3>
          <div class="mt-3 grid gap-2 sm:grid-cols-3">
            ${data.excluded_incompatible_domains.slice(0, 6).map(ex => `
              <div class="rounded-lg border border-rose-500/20 bg-slate-900/70 p-2.5 text-xs">
                <div class="flex items-center justify-between">
                  <span class="font-mono font-bold text-rose-300">${ex.run_code}</span>
                  <span class="rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-200">${ex.record_domain} ≠ ${ex.target_domain}</span>
                </div>
                <div class="mt-1 text-[11px] text-slate-300">${ex.fuel_material}</div>
                <div class="mt-1 text-[11px] text-slate-400">${ex.rejection_reason}</div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    async function runAssistant(presetQ) {
      if (presetQ) document.getElementById("rag-input").value = presetQ;
      const question = document.getElementById("rag-input").value;
      const combustion_domain = document.getElementById("rag-domain").value || null;

      const res = await fetch("/api/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, combustion_domain, top_k_chunks: 4, top_k_experiments: 5 })
      });
      const data = await res.json();

      document.getElementById("rag-output").innerHTML = `
        <div class="grid gap-3 sm:grid-cols-4">
          ${data.retrieval_pipeline_trace.map(s => `
            <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-3.5">
              <div class="text-xs font-bold text-cyan-300">${s.step}</div>
              <p class="mt-1 text-[11px] text-slate-400">${s.detail}</p>
            </div>
          `).join("")}
        </div>

        <div class="grid gap-6 lg:grid-cols-12">
          <div class="lg:col-span-7 space-y-5">
            <div class="rounded-xl border border-emerald-500/40 bg-[#0d121d] p-5">
              <span class="rounded bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-[11px] font-bold uppercase text-emerald-300">1. Verbatim Published Evidence (Knowledge Base Chunks)</span>
              <div class="mt-3 space-y-3">
                ${data.published_scientific_evidence.map(ch => `
                  <div class="rounded-lg border border-slate-800 bg-slate-900/70 p-3.5 text-xs">
                    <div class="flex flex-wrap items-center justify-between gap-2">
                      <span class="font-bold text-orange-300">[${ch.external_investigation_id}] ${ch.section_title}</span>
                      <span class="font-mono text-[11px] text-emerald-400">Hybrid: ${ch.hybrid_score} (Sem: ${ch.semantic_score})</span>
                    </div>
                    <p class="mt-2 leading-relaxed text-slate-200">${ch.content_text}</p>
                    <div class="mt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800 pt-2">
                      <span>${ch.document_title} (${ch.publication_year})</span>
                      <a href="${ch.source_url}" target="_blank" class="text-cyan-300 hover:underline">${ch.doi ? 'DOI: ' + ch.doi : 'Source Link ↗'}</a>
                    </div>
                  </div>
                `).join("")}
              </div>
            </div>

            <div class="rounded-xl border border-cyan-500/40 bg-[#0d121d] p-5">
              <span class="rounded bg-cyan-500/20 border border-cyan-500/40 px-2.5 py-0.5 text-[11px] font-bold uppercase text-cyan-300">2. Retrieved Structured Experiments (PostgreSQL SQL Query)</span>
              <div class="mt-3 space-y-2.5">
                ${data.structured_sql_experiments.map(exp => `
                  <div class="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-mono font-bold text-white">${exp.run_code} (${exp.external_investigation_id}) — ${exp.fuel_material}</span>
                      <button onclick="openProvenance('${exp.run_code}')" class="text-cyan-300 hover:underline">Provenance ↗</button>
                    </div>
                    <div class="mt-1 text-slate-400">Domain: ${exp.combustion_domain} • Gravity: ${exp.gravity_regime} • O₂=${exp.oxygen_fraction ?? 'NULL'} • P=${exp.pressure_normalized_kpa ?? 'NULL'} kPa • V_air=${exp.flow_velocity_normalized_cm_s ?? 'NULL'} cm/s</div>
                  </div>
                `).join("")}
              </div>
            </div>
          </div>

          <div class="lg:col-span-5">
            <div class="rounded-xl border border-orange-500/50 bg-gradient-to-b from-orange-950/20 to-[#0d121d] p-5">
              <div class="flex items-center justify-between border-b border-orange-500/30 pb-3">
                <span class="rounded bg-orange-500 px-2.5 py-0.5 text-[11px] font-bold uppercase text-black">3. Generated Scientific Interpretation</span>
                <span class="font-mono text-[11px] text-orange-300">${data.generated_interpretation.synthesis_mode}</span>
              </div>
              <div class="mt-2 rounded bg-orange-950/30 p-2 text-[11px] text-orange-200">${data.generated_interpretation.label}</div>
              <div class="mt-4 whitespace-pre-line text-xs leading-relaxed text-slate-200">${data.generated_interpretation.markdown_content}</div>
            </div>
          </div>
        </div>
      `;
    }

    async function loadSources() {
      const res = await fetch("/api/sources");
      const list = await res.json();
      document.getElementById("sources-list").innerHTML = list.map(src => `
        <div class="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
          <div class="flex items-center justify-between">
            <div>
              <span class="rounded bg-orange-500/20 px-2 py-0.5 font-mono text-xs font-bold text-orange-300">${src.publisher} (${src.priority})</span>
              <h3 class="mt-1 text-sm font-bold text-white">${src.source_name}</h3>
              <p class="text-xs text-slate-400">License: ${src.license} • Track: ${src.domain_track}</p>
            </div>
            <a href="${src.source_url}" target="_blank" class="rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-orange-300">Source URL ↗</a>
          </div>
          <div class="mt-3 grid gap-2 sm:grid-cols-2">
            ${src.field_mappings.map(fm => `
              <div class="rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 text-xs">
                <div class="font-mono font-semibold text-cyan-300">${fm.source_field} (${fm.source_unit}) → ${fm.canonical_field} (${fm.canonical_unit})</div>
                <div class="mt-1 text-slate-300">${fm.transform_description}</div>
              </div>
            `).join("")}
          </div>
        </div>
      `).join("");
    }

    async function triggerReingestion() {
      const btn = document.getElementById("btn-reingest");
      btn.textContent = "Running 7-Stage Pipeline...";
      const res = await fetch("/api/ingestion/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_filter: "ALL", force_refresh: true })
      });
      const rep = await res.json();
      btn.textContent = "Trigger Verified Re-Ingestion Job";
      document.getElementById("ingestion-job-status").innerHTML = `
        <div class="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-4 text-xs">
          <div class="font-bold text-emerald-300">7-Stage Ingestion Job Completed</div>
          <pre class="mt-2 overflow-x-auto font-mono text-[11px] text-slate-200">${JSON.stringify(rep, null, 2)}</pre>
        </div>
      `;
    }

    async function openProvenance(id) {
      const res = await fetch("/api/provenance/" + id);
      const data = await res.json();
      document.getElementById("prov-json").textContent = JSON.stringify(data, null, 2);
      const modal = document.getElementById("prov-modal");
      modal.classList.remove("hidden");
      modal.classList.add("flex");
    }

    function closeProvenance() {
      const modal = document.getElementById("prov-modal");
      modal.classList.add("hidden");
      modal.classList.remove("flex");
    }

    // Initialize presets & initial view
    document.getElementById("preset-questions").innerHTML = PRESETS.map(q =>
      `<button onclick="runAssistant('${q.replace(/'/g, "\\'")}')" class="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 hover:border-orange-500/50">${q}</button>`
    ).join("");
    loadInvestigations();
  </script>
</body>
</html>
"""

