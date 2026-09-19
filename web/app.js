/**
 * ATLAS / Study Sentinel — Frontend Application Logic
 * Pure vanilla ES6, modular, reactive, zero external build dependencies.
 */

// Global App State
const state = {
  currentStudy: "STUDY-042",
  currentCut: 1,
  protocolVersion: "v1",
  activeTab: "dashboard",
  studies: [],
  cuts: [],
  subjects: [],
  findings: [],
  selectedSubject: null,
  activeDocument: null,
};

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", async () => {
  await initApp();
});

async function initApp() {
  await loadStudies();
  await loadCuts();
  await loadSubjects();
  await refreshAll();
}

async function refreshAll() {
  updateCutBadges();
  if (state.activeTab === "dashboard") await loadDashboard();
  if (state.activeTab === "graph") await renderSubjectGraph();
  if (state.activeTab === "patient360") await loadPatient360();
  if (state.activeTab === "findings") await loadFindings();
  if (state.activeTab === "queue") await loadQueue();
  if (state.activeTab === "queries") await loadQueries();
  if (state.activeTab === "decisions") await loadDecisions();
  if (state.activeTab === "documents") await loadDocuments();
  if (state.activeTab === "labexplorer") await loadLabExplorer();
  if (state.activeTab === "cutexplorer") await initCutComparison();
  
  // Stage 2
  if (state.activeTab === "humangate") await loadHumanGate();
  if (state.activeTab === "cyclereport") await loadCycleReport();
  if (state.activeTab === "trace") await loadTrace();
  if (state.activeTab === "queries") await loadQueries2(); // Overriding for Stage 2
}

function updateCutBadges() {
  document.querySelectorAll(".active-cut-label").forEach((el) => {
    el.textContent = state.currentCut;
  });
  const cutMeta = state.cuts.find((c) => c.cut_id === state.currentCut);
  if (cutMeta) {
    state.protocolVersion = cutMeta.protocol_version;
    const badge = document.getElementById("activeProtocolBadge");
    if (badge) badge.textContent = `Protocol ${state.protocolVersion.toUpperCase()}`;
  }
}

// Navigation Tab Switcher
function switchTab(tabId) {
  state.activeTab = tabId;
  const tabs = [
    "dashboard",
    "graph",
    "patient360",
    "findings",
    "ask",
    "queue",
    "queries",
    "decisions",
    "documents",
    "labexplorer",
    "cutexplorer",
    "evidence"
  ];

  tabs.forEach((t) => {
    const btn = document.getElementById(`tab-${t}`);
    const view = document.getElementById(`view-${t}`);
    if (t === tabId) {
      if (btn) {
        btn.classList.remove("text-slate-400", "hover:bg-slate-800", "hover:text-slate-200");
        btn.classList.add("bg-indigo-500/10", "text-indigo-400");
      }
      if (view) view.classList.remove("hidden");
    } else {
      if (btn) {
        if (!btn.classList.contains("text-amber-400")) { // Keep ask styling intact if it's the ask button
            btn.classList.remove("bg-indigo-500/10", "text-indigo-400");
            btn.classList.add("text-slate-400", "hover:bg-slate-800", "hover:text-slate-200");
        }
      }
      if (view) view.classList.add("hidden");
    }
  });

  refreshAll();
}

// Data Fetching: Studies & Cuts
async function loadStudies() {
  try {
    const res = await fetch("/api/studies");
    const data = await res.json();
    state.studies = data.studies || ["STUDY-042"];
    const select = document.getElementById("studySelect");
    if (select) {
      select.innerHTML = state.studies
        .map(
          (s) =>
            `<option value="${s}" ${s === state.currentStudy ? "selected" : ""}>${s}</option>`
        )
        .join("");
    }
  } catch (err) {
    console.error("Error loading studies:", err);
  }
}

async function loadCuts() {
  try {
    const res = await fetch(`/api/cuts?study=${state.currentStudy}`);
    const data = await res.json();
    state.cuts = data.cuts || [];
    const select = document.getElementById("cutSelect");
    if (select && state.cuts.length > 0) {
      select.innerHTML = state.cuts
        .map(
          (c) =>
            `<option value="${c.cut_id}" ${c.cut_id === state.currentCut ? "selected" : ""}>Cut ${c.cut_id} (${c.protocol_version})</option>`
        )
        .join("");
    }
    updateCutBadges();
  } catch (err) {
    console.error("Error loading cuts:", err);
  }
}

async function loadSubjects() {
  try {
    const res = await fetch(
      `/api/subjects?study=${state.currentStudy}&cut=${state.currentCut}`
    );
    const data = await res.json();
    state.subjects = data.subjects || [];

    if (state.subjects.length > 0 && !state.selectedSubject) {
      state.selectedSubject = state.subjects[0].usubjid;
    }

    // Populate graph subject selector
    const graphSelect = document.getElementById("graphSubjectSelect");
    if (graphSelect) {
      graphSelect.innerHTML = state.subjects
        .map(
          (s) =>
            `<option value="${s.usubjid}" ${s.usubjid === state.selectedSubject ? "selected" : ""}>${s.usubjid} (${s.site_id})</option>`
        )
        .join("");
    }

    // Populate Patient 360 subject selector
    const p360Select = document.getElementById("p360SubjectSelect");
    if (p360Select) {
      p360Select.innerHTML = state.subjects
        .map(
          (s) =>
            `<option value="${s.usubjid}" ${s.usubjid === state.selectedSubject ? "selected" : ""}>${s.usubjid}</option>`
        )
        .join("");
    }
  } catch (err) {
    console.error("Error loading subjects:", err);
  }
}

async function onStudyChange() {
  const sel = document.getElementById("studySelect");
  state.currentStudy = sel.value;
  await loadCuts();
  await loadSubjects();
  await refreshAll();
}

async function onCutChange() {
  const sel = document.getElementById("cutSelect");
  state.currentCut = parseInt(sel.value, 10);
  await loadSubjects();
  await refreshAll();
}

// TAB 1: DASHBOARD
async function loadDashboard() {
  try {
    const [statsRes, findingsRes] = await Promise.all([
      fetch(`/api/statistics?study=${state.currentStudy}&cut=${state.currentCut}`),
      fetch(`/api/findings?study=${state.currentStudy}&cut=${state.currentCut}`),
    ]);

    const stats = await statsRes.json();
    const findingsData = await findingsRes.json();
    state.findings = findingsData.findings || [];

    // Update Top Metric Cards
    document.getElementById("metricSubjects").textContent = stats.subject_count || 0;
    document.getElementById("metricSites").textContent = stats.site_count || 0;
    document.getElementById("metricRecords").textContent = stats.total_records || 0;
    document.getElementById("metricProtocol").textContent = stats.protocol_version || "v1";
    document.getElementById("metricCorrections").textContent = stats.correction_count || 0;
    document.getElementById("metricFindings").textContent = state.findings.length;
    document.getElementById("findingsCountBadge").textContent = state.findings.length;
    
    // Add SAE and Dosing Errors
    const saeCount = state.findings.filter(f => f.finding_code.startsWith("SAE")).length;
    const dosingCount = state.findings.filter(f => f.finding_code.startsWith("EX")).length;
    const saeEl = document.getElementById("metricSAEs");
    if (saeEl) saeEl.textContent = saeCount;
    const dosingEl = document.getElementById("metricDosingErrors");
    if (dosingEl) dosingEl.textContent = dosingCount;

    // Visit Window Description
    const visitWin = document.getElementById("metricVisitWindow");
    if (visitWin) {
      visitWin.textContent = (stats.protocol_version || "v1").toLowerCase().includes("v1")
        ? "±7 days window"
        : "±3 days window";
    }

    // Missing values
    const missingEl = document.getElementById("metricMissingValues");
    if (missingEl) {
      missingEl.textContent = `${stats.total_missing_values || 0} fields`;
    }

    // Render Domain Cards
    const domainGrid = document.getElementById("domainBarGrid");
    if (domainGrid && stats.domain_record_counts) {
      const domains = ["DM", "AE", "LB", "VS", "EX", "CM", "DS", "MH", "EG"];
      domainGrid.innerHTML = domains
        .map((d) => {
          const count = stats.domain_record_counts[d] || 0;
          return `
          <div class="bg-slate-950/70 border border-slate-800 rounded-lg p-3 text-center hover:border-indigo-500/40 transition-colors">
            <span class="text-xs font-bold text-indigo-400">${d}</span>
            <div class="text-lg font-extrabold text-white mt-0.5">${count}</div>
            <span class="text-[10px] text-slate-400">records</span>
          </div>
        `;
        })
        .join("");
    }

    // Render Cut Progression Timeline
    const timeline = document.getElementById("cutTimelineList");
    if (timeline && state.cuts) {
      timeline.innerHTML = state.cuts
        .map((c) => {
          const isActive = c.cut_id === state.currentCut;
          const isPassed = c.cut_id <= state.currentCut;
          const recCount = (stats.records_available_by_cut || {})[c.cut_id] || "--";
          return `
          <div class="flex items-center justify-between p-2.5 rounded-lg border ${
            isActive
              ? "bg-indigo-950/40 border-indigo-500/50"
              : isPassed
              ? "bg-slate-950/50 border-slate-800"
              : "bg-slate-950/20 border-slate-900 opacity-60"
          }">
            <div class="flex items-center gap-2.5">
              <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/30"
                  : "bg-slate-800 text-slate-400"
              }">
                ${c.cut_id}
              </span>
              <div>
                <div class="text-xs font-semibold ${isActive ? "text-white" : "text-slate-300"}">
                  Cut ${c.cut_id} &bull; Protocol ${c.protocol_version.toUpperCase()}
                </div>
                <div class="text-[10px] text-slate-400">${c.description || c.cut_date}</div>
              </div>
            </div>
            <span class="text-xs font-mono font-bold ${isActive ? "text-cyan-400" : "text-slate-400"}">
              ${recCount} recs
            </span>
          </div>
        `;
        })
        .join("");
    }
  } catch (err) {
    console.error("Error loading dashboard:", err);
  }
}

// TAB 2: STUDY GRAPH (Interactive SVG Visual Node-Link Explorer)
async function renderSubjectGraph() {
  const select = document.getElementById("graphSubjectSelect");
  const subjectId = select && select.value ? select.value : state.selectedSubject;
  if (!subjectId) return;
  state.selectedSubject = subjectId;

  try {
    const res = await fetch(
      `/api/graph?study=${state.currentStudy}&subject=${subjectId}&cut=${state.currentCut}`
    );
    const data = await res.json();
    const svg = document.getElementById("studyGraphSvg");
    if (!svg) return;

    // Build visual coordinates for Subject Node and Domain Nodes
    const width = 900;
    const height = 400;
    const centerX = width / 2;
    const centerY = height / 2;
    const orbitRadius = 145;

    const domainNodes = (data.nodes || []).filter((n) => n.type === "domain");
    const count = domainNodes.length;

    let svgContent = `
      <!-- Center Glow Defs -->
      <defs>
        <radialGradient id="centerGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#4f46e5" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="#0b0f19" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <circle cx="${centerX}" cy="${centerY}" r="${orbitRadius + 40}" fill="url(#centerGlow)"/>
      <circle cx="${centerX}" cy="${centerY}" r="${orbitRadius}" fill="none" stroke="#1e293b" stroke-dasharray="4 4"/>
    `;

    // Calculate domain coordinates
    domainNodes.forEach((node, idx) => {
      const angle = (idx / count) * 2 * Math.PI - Math.PI / 2;
      const nx = centerX + orbitRadius * Math.cos(angle);
      const ny = centerY + orbitRadius * Math.sin(angle);
      node.x = nx;
      node.y = ny;

      // Connecting lines
      svgContent += `
        <line x1="${centerX}" y1="${centerY}" x2="${nx}" y2="${ny}" stroke="#334155" stroke-width="1.5" stroke-opacity="0.7"/>
      `;
    });

    // Render Domain Nodes
    domainNodes.forEach((node) => {
      const colors = {
        AE: "#f43f5e",
        LB: "#06b6d4",
        EX: "#6366f1",
        CM: "#f59e0b",
        VS: "#10b981",
        DM: "#a855f7",
        DS: "#3b82f6",
        MH: "#8b5cf6",
        EG: "#ec4899",
      };
      const col = colors[node.domain] || "#6366f1";

      svgContent += `
        <g class="node-circle" onclick="inspectDomainRecords('${node.domain}', '${subjectId}')">
          <circle cx="${node.x}" cy="${node.y}" r="22" fill="#0f172a" stroke="${col}" stroke-width="2"/>
          <text x="${node.x}" y="${node.y - 2}" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">${node.domain}</text>
          <text x="${node.x}" y="${node.y + 11}" fill="${col}" font-size="9" font-weight="600" text-anchor="middle">${node.count}</text>
        </g>
      `;
    });

    // Render Central Subject Node
    const siteId = (data.subject && data.subject.site_id) || "SITE";
    svgContent += `
      <g class="node-circle">
        <circle cx="${centerX}" cy="${centerY}" r="34" fill="#1e1b4b" stroke="#6366f1" stroke-width="3"/>
        <circle cx="${centerX}" cy="${centerY}" r="30" fill="#312e81" opacity="0.6"/>
        <text x="${centerX}" y="${centerY - 6}" fill="#ffffff" font-size="11" font-weight="extrabold" text-anchor="middle">${subjectId.split("-").slice(-2).join("-")}</text>
        <text x="${centerX}" y="${centerY + 8}" fill="#a5b4fc" font-size="9" text-anchor="middle">${siteId}</text>
      </g>
    `;

    svg.innerHTML = svgContent;
  } catch (err) {
    console.error("Error rendering graph:", err);
  }
}

// Click Domain Node -> Inspect Records Table Drawer
async function inspectDomainRecords(domain, subjectId) {
  const container = document.getElementById("graphDomainDetail");
  const title = document.getElementById("graphDomainTitle");
  const tbody = document.getElementById("graphRecordsTableBody");
  if (!container || !tbody) return;

  container.classList.remove("hidden");
  title.innerHTML = `<i class="fa-solid fa-folder-open text-indigo-400"></i> Domain: <span class="text-indigo-300 font-bold">${domain}</span> &bull; Subject: ${subjectId} &bull; Cut ${state.currentCut}`;

  try {
    const res = await fetch(
      `/api/patient360?study=${state.currentStudy}&subject=${subjectId}&cut=${state.currentCut}`
    );
    const profile = await res.json();

    let records = [];
    if (domain === "DM" && profile.demographics && profile.demographics.identity) {
      records = [profile.demographics];
    } else if (domain === "AE") records = profile.adverse_events || [];
    else if (domain === "LB") records = profile.laboratory_results || [];
    else if (domain === "EX") records = profile.exposure || [];
    else if (domain === "CM") records = profile.concomitant_medications || [];
    else if (domain === "VS") records = profile.vital_signs || [];
    else if (domain === "DS") records = profile.disposition || [];
    else if (domain === "MH") records = profile.medical_history || [];
    else if (domain === "EG") records = profile.ecg || [];

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-400">No records available at Cut ${state.currentCut} for ${domain}.</td></tr>`;
      return;
    }

    tbody.innerHTML = records
      .map((r) => {
        const ident = r.identity || `${domain}|${subjectId}|${r.seq}`;
        const isCorr = r.is_corrected;
        const corrBadge = isCorr
          ? `<span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-semibold">Corrected at Cut ${r.corrected_at_cut}</span>`
          : `<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">Original</span>`;

        // Extract key summary value
        let valSummary = "";
        const f = r.fields || r;
        if (domain === "AE") valSummary = `${f.AETERM || ""} (AESER: ${f.AESER || "N"}, Hosp: ${f.AESHOSP || "N"})`;
        else if (domain === "LB") valSummary = `${f.LBTEST || f.LBTESTCD || ""}: ${f.LBORRES || ""} ${f.LBORRESU || ""}`;
        else if (domain === "EX") valSummary = `${f.EXTRT || ""}: ${f.EXDOSE || ""} ${f.EXDOSU || "mg"} (${f.EXDOSFRQ || "QD"})`;
        else if (domain === "CM") valSummary = `${f.CMTRT || ""} (Class: ${f.CMCLAS || ""})`;
        else if (domain === "VS") valSummary = `${f.VSTEST || f.VSTESTCD || ""}: ${f.VSORRES || ""} ${f.VSORRESU || ""}`;
        else if (domain === "DM") valSummary = `Age: ${f.AGE || ""}, Arm: ${f.ARM || ""}`;
        else valSummary = Object.entries(f).slice(0, 3).map(([k, v]) => `${k}=${v}`).join(", ");

        return `
        <tr class="hover:bg-slate-900/80 transition-colors">
          <td class="py-2.5 px-3 font-mono text-indigo-300 font-medium">${ident}</td>
          <td class="py-2.5 px-3">Cut ${r.cut_available}</td>
          <td class="py-2.5 px-3">${corrBadge}</td>
          <td class="py-2.5 px-3 text-slate-200 max-w-xs truncate">${valSummary}</td>
          <td class="py-2.5 px-3 text-right">
            <button onclick="openEvidenceModal('${domain}', '${subjectId}', ${r.seq})" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-medium transition-colors">
              <i class="fa-solid fa-magnifying-glass"></i> Inspect
            </button>
          </td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Error inspecting domain records:", err);
  }
}

// TAB 3: PATIENT 360
async function loadPatient360() {
  const select = document.getElementById("p360SubjectSelect");
  const subjectId = select && select.value ? select.value : state.selectedSubject;
  if (!subjectId) return;
  state.selectedSubject = subjectId;

  try {
    const res = await fetch(
      `/api/patient360?study=${state.currentStudy}&subject=${subjectId}&cut=${state.currentCut}`
    );
    const profile = await res.json();

    // Demographics Header
    const demo = profile.demographics.fields || profile.demographics || {};
    document.getElementById("p360ArmBadge").textContent = demo.ARM || "Drug 10mg";
    document.getElementById("p360SiteBadge").textContent = profile.site_id || "SITE-101";
    document.getElementById("p360DemographicsSummary").innerHTML = `
      Age: <span class="text-white font-semibold">${demo.AGE || "--"}</span> &bull; 
      Sex: <span class="text-white font-semibold">${demo.SEX || "--"}</span> &bull; 
      Race: <span class="text-white font-semibold">${demo.RACE || "--"}</span> &bull; 
      Day 1 (RFSTDTC): <span class="text-cyan-300 font-mono">${demo.RFSTDTC || "--"}</span>
    `;
    document.getElementById("p360Protocol").textContent = profile.protocol_version;

    // AEs & SAEs
    const aeList = document.getElementById("p360AeList");
    const aes = profile.adverse_events || [];
    document.getElementById("p360AeCount").textContent = aes.length;
    if (aeList) {
      if (aes.length === 0) {
        aeList.innerHTML = `<div class="p-3 text-xs text-slate-400 bg-slate-950/40 rounded">No adverse events reported.</div>`;
      } else {
        aeList.innerHTML = aes
          .map((ae) => {
            const f = ae.fields || ae;
            const isSerious = ae.is_serious;
            const hasDiscrepancy = ae.discrepancy;
            return `
            <div class="p-3 rounded-lg border ${
              hasDiscrepancy
                ? "bg-rose-950/30 border-rose-500/60 pulse-warning"
                : isSerious
                ? "bg-rose-950/20 border-rose-500/40"
                : "bg-slate-950/60 border-slate-800"
            }">
              <div class="flex items-start justify-between gap-2">
                <span class="text-xs font-bold ${isSerious ? "text-rose-300" : "text-white"}">${f.AETERM}</span>
                <span class="text-[10px] font-mono text-slate-400">Seq ${ae.seq}</span>
              </div>
              <div class="flex items-center flex-wrap gap-1.5 mt-1.5">
                ${
                  hasDiscrepancy
                    ? `<span class="px-1.5 py-0.5 rounded bg-rose-500 text-white font-extrabold text-[9px]">SAE DISCREPANCY (AESHOSP=Y)</span>`
                    : isSerious
                    ? `<span class="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold text-[9px]">SAE</span>`
                    : `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[9px]">Non-serious</span>`
                }
                <span class="text-[10px] text-slate-400">Severity: <b class="text-slate-200">${f.AESEV || "--"}</b></span>
                <span class="text-[10px] text-slate-400">Onset: <b class="text-slate-200">${f.AESTDTC || "--"}</b></span>
              </div>
            </div>
          `;
          })
          .join("");
      }
    }

    // Exposure
    const exList = document.getElementById("p360ExList");
    const exs = profile.exposure || [];
    document.getElementById("p360ExCount").textContent = exs.length;
    if (exList) {
      if (exs.length === 0) {
        exList.innerHTML = `<div class="p-3 text-xs text-slate-400 bg-slate-950/40 rounded">No exposure records reported.</div>`;
      } else {
        exList.innerHTML = exs
          .map((ex) => {
            const f = ex.fields || ex;
            const isDoseErr = f.EXDOSE && parseFloat(f.EXDOSE) !== 10 && !demo.ARM?.includes("Placebo");
            return `
            <div class="p-2.5 rounded-lg border ${
              isDoseErr ? "bg-amber-950/30 border-amber-500/50" : "bg-slate-950/60 border-slate-800"
            } flex items-center justify-between">
              <div>
                <div class="text-xs font-semibold text-white">${f.EXTRT || "Study Drug"}</div>
                <div class="text-[10px] text-slate-400">Dose: <b class="${isDoseErr ? "text-amber-300 font-bold" : "text-indigo-300"}">${f.EXDOSE} ${f.EXDOSU || "mg"}</b> (${f.EXDOSFRQ || "QD"})</div>
              </div>
              <span class="text-[10px] text-slate-400 font-mono">${f.EXSTDTC || ""}</span>
            </div>
          `;
          })
          .join("");
      }
    }

    // Laboratory Table
    const lbTbody = document.getElementById("p360LbTableBody");
    const labs = profile.laboratory_results || [];
    if (lbTbody) {
      if (labs.length === 0) {
        lbTbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400">No laboratory records available.</td></tr>`;
      } else {
        lbTbody.innerHTML = labs
          .map((lb) => {
            const f = lb.fields || lb;
            const interp = lb.interpretation || {};
            const isHigh = interp.interpretation === "HIGH";
            const isLow = interp.interpretation === "LOW";
            const isBelow = interp.special_status === "BELOW_DETECTION";
            const isNd = interp.special_status === "NOT_DONE";

            let statusBadge = `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">Normal</span>`;
            if (isHigh) statusBadge = `<span class="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold text-[10px]">HIGH (${interp.elevation_ratio}x)</span>`;
            if (isLow) statusBadge = `<span class="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 font-bold text-[10px]">LOW</span>`;
            if (isBelow) statusBadge = `<span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-semibold text-[10px]">&lt; Detection</span>`;
            if (isNd) statusBadge = `<span class="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold text-[10px]">Not Done (ND)</span>`;

            // Unit conversion display
            let normDisplay = `<span class="text-slate-400 font-mono">--</span>`;
            if (interp.normalized_value !== null && interp.normalized_value !== undefined) {
              normDisplay = `<span class="font-mono text-slate-200">${interp.normalized_value} ${interp.normalized_unit}</span>`;
              if (interp.unit_conversion_applied) {
                normDisplay += ` <span class="text-[9px] text-cyan-300 bg-cyan-950 px-1 py-0.5 rounded border border-cyan-500/30">converted</span>`;
              }
            }

            const refRangeStr = interp.ref_high
              ? `[${interp.ref_low || 0} - ${interp.ref_high} ${interp.ref_unit || ""}]`
              : "--";

            return `
            <tr class="hover:bg-slate-900/80 transition-colors">
              <td class="py-2 px-2.5 font-bold text-white">${f.LBTESTCD || f.LBTEST}</td>
              <td class="py-2 px-2.5 font-mono text-indigo-300 font-medium">${interp.raw_value} ${interp.reported_unit}</td>
              <td class="py-2 px-2.5">${normDisplay}</td>
              <td class="py-2 px-2.5 text-slate-400 font-mono text-[11px]">${refRangeStr}</td>
              <td class="py-2 px-2.5">${statusBadge}</td>
              <td class="py-2 px-2.5 text-slate-400">${f.VISIT || ""} &bull; ${f.LBDTC || ""}</td>
            </tr>
          `;
          })
          .join("");
      }
    }

    // ConMeds & Vitals
    const cmList = document.getElementById("p360CmList");
    const cms = profile.concomitant_medications || [];
    document.getElementById("p360CmCount").textContent = cms.length;
    if (cmList) {
      cmList.innerHTML = cms.length
        ? cms.map((c) => {
            const f = c.fields || c;
            return `<div class="flex justify-between border-b border-slate-800/60 pb-1"><span>${f.CMTRT}</span><span class="text-slate-400 text-[10px]">${f.CMCLAS || ""}</span></div>`;
          }).join("")
        : `<div class="text-slate-400">No concomitant medications.</div>`;
    }

    const vsList = document.getElementById("p360VsList");
    const vss = profile.vital_signs || [];
    document.getElementById("p360VsCount").textContent = vss.length;
    if (vsList) {
      vsList.innerHTML = vss.length
        ? vss.map((v) => {
            const f = v.fields || v;
            return `<div class="flex justify-between border-b border-slate-800/60 pb-1"><span>${f.VSTEST}: <b>${f.VSORRES} ${f.VSORRESU}</b></span><span class="text-slate-400 text-[10px]">${f.VISIT || ""}</span></div>`;
          }).join("")
        : `<div class="text-slate-400">No vital signs recorded.</div>`;
    }

    // Detected Patient Findings
    const findingsList = document.getElementById("p360FindingsList");
    const pFindings = profile.findings || [];
    if (findingsList) {
      if (pFindings.length === 0) {
        findingsList.innerHTML = `<div class="p-3 text-xs text-emerald-400 bg-emerald-950/20 border border-emerald-500/30 rounded flex items-center gap-2"><i class="fa-solid fa-circle-check"></i> No protocol deviations or safety findings detected for this subject at Cut ${state.currentCut}.</div>`;
      } else {
        findingsList.innerHTML = pFindings
          .map((f) => {
            const isCrit = f.severity === "CRITICAL";
            return `
            <div class="p-3 rounded-lg border ${
              isCrit ? "bg-rose-950/20 border-rose-500/40" : "bg-amber-950/20 border-amber-500/40"
            }">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold ${isCrit ? "text-rose-400" : "text-amber-400"}">${f.finding_code}</span>
                <span class="text-[10px] font-semibold px-2 py-0.5 rounded ${isCrit ? "bg-rose-500 text-white" : "bg-amber-500/20 text-amber-300"}">${f.severity}</span>
              </div>
              <p class="text-xs text-slate-300 mt-1">${f.description}</p>
              <div class="flex items-center justify-between mt-2 pt-2 border-t border-slate-800 text-[10px]">
                <span class="text-slate-400">Evidence: <code class="text-indigo-300 font-mono">${(f.evidence_references || []).join(", ")}</code></span>
                <button onclick="inspectFindingDetail('${f.finding_code}', '${f.subject}')" class="text-indigo-400 hover:text-indigo-300 font-semibold">View Detail &rarr;</button>
              </div>
            </div>
          `;
          })
          .join("");
      }
    }
  } catch (err) {
    console.error("Error loading Patient 360:", err);
  }
}

// TAB 4: FINDINGS REGISTRY
async function loadFindings() {
  const sev = document.getElementById("filterSeverity")?.value || "";
  const dom = document.getElementById("filterDomain")?.value || "";
  const stat = document.getElementById("filterStatus")?.value || "";

  try {
    const res = await fetch(
      `/api/findings?study=${state.currentStudy}&cut=${state.currentCut}&severity=${sev}&domain=${dom}&status=${stat}`
    );
    const data = await res.json();
    state.findings = data.findings || [];

    const tbody = document.getElementById("findingsTableBody");
    if (!tbody) return;

    if (state.findings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="py-6 text-center text-slate-400">No clinical findings matching filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = state.findings
      .map((f) => {
        const isCrit = f.severity === "CRITICAL";
        const isMaj = f.severity === "MAJOR";
        const sevClass = isCrit
          ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
          : isMaj
          ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
          : "bg-blue-500/20 text-blue-300 border-blue-500/30";

        const statClass =
          f.status === "RESOLVED"
            ? "text-emerald-400 bg-emerald-950/40 border-emerald-500/30"
            : f.status === "UNDER_REVIEW"
            ? "text-purple-400 bg-purple-950/40 border-purple-500/30"
            : "text-amber-400 bg-amber-950/40 border-amber-500/30";

        const evStr = (f.evidence_references || []).join(", ");

        return `
        <tr class="hover:bg-slate-900/80 transition-colors">
          <td class="py-2.5 px-3 font-bold text-white font-mono text-[11px]">${f.finding_code}</td>
          <td class="py-2.5 px-3">
            <div class="font-medium text-slate-200">${f.subject}</div>
            <div class="text-[10px] text-slate-400">${f.site}</div>
          </td>
          <td class="py-2.5 px-3 font-semibold text-indigo-400">${f.domain}</td>
          <td class="py-2.5 px-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${sevClass}">${f.severity}</span>
          </td>
          <td class="py-2.5 px-3 text-slate-300 max-w-sm">${f.description}</td>
          <td class="py-2.5 px-3 text-slate-400">
            <div>Prot: <b class="text-white">${f.protocol_version}</b></div>
            <div>Cut: <b class="text-white">${f.data_cut}</b></div>
          </td>
          <td class="py-2.5 px-3 font-mono text-indigo-300 text-[10px]">${evStr}</td>
          <td class="py-2.5 px-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${statClass}">${f.status}</span>
          </td>
          <td class="py-2.5 px-3 text-right">
            <button onclick="inspectFindingDetail('${f.finding_code}', '${f.subject}')" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded text-[10px] font-semibold transition-colors">
              Inspect
            </button>
          </td>
        </tr>
      `;
      })
      .join("");
  } catch (err) {
    console.error("Error loading findings:", err);
  }
}

// Inspect Finding Deep-Dive Modal
function inspectFindingDetail(findingCode, subjectId) {
  const f = state.findings.find(
    (item) => item.finding_code === findingCode && item.subject === subjectId
  );
  if (!f) return;

  const modal = document.getElementById("evidenceModal");
  const title = document.getElementById("modalEvidenceTitle");
  const ident = document.getElementById("modalEvidenceIdentity");
  const body = document.getElementById("modalEvidenceBody");

  title.textContent = `Finding Detail: ${f.finding_code}`;
  ident.textContent = `Subject: ${f.subject} | Site: ${f.site} | Domain: ${f.domain}`;

  let siteReplyHtml = `<p class="text-slate-400">No site reply on file.</p>`;
  if (f.site_reply) {
    siteReplyHtml = `
      <div class="p-3 bg-slate-950 rounded-lg border border-slate-800">
        <div class="flex items-center justify-between text-[11px] text-sky-400 mb-1 font-semibold">
          <span><i class="fa-solid fa-reply"></i> Site Reply (${f.site_reply.is_default ? "Default Response" : "Record-Specific Response"})</span>
          <span class="text-slate-400 text-[10px]">${f.site_reply.timestamp || ""}</span>
        </div>
        <p class="text-slate-200 text-xs">${f.site_reply.reply}</p>
      </div>
    `;
  }

  let monitorDecisionHtml = `<p class="text-slate-400">No monitor decision registered yet.</p>`;
  if (f.monitor_decision) {
    const d = f.monitor_decision;
    const isApp = d.decision === "APPROVED";
    const isRej = d.decision === "REJECTED";
    const decClass = isApp
      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
      : isRej
      ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
      : "bg-amber-500/20 text-amber-300 border-amber-500/30";

    monitorDecisionHtml = `
      <div class="p-3 bg-slate-950 rounded-lg border border-slate-800">
        <div class="flex items-center justify-between mb-1.5">
          <span class="px-2 py-0.5 rounded text-[10px] font-extrabold border ${decClass}">${d.decision}</span>
          <span class="text-slate-400 text-[10px]">${d.monitor_name || "Monitor"}</span>
        </div>
        ${d.comment ? `<p class="text-slate-300 text-xs mb-1"><b>Rationale:</b> ${d.comment}</p>` : ""}
        ${
          d.inquiry
            ? `<div class="mt-2 p-2 bg-amber-950/40 border border-amber-500/40 rounded text-amber-200 text-xs"><b>Clarification Request:</b> ${d.inquiry}</div>`
            : ""
        }
      </div>
    `;
  }

  body.innerHTML = `
    <!-- Description & Rule -->
    <div class="space-y-1.5">
      <div class="flex items-center justify-between">
        <span class="font-semibold text-white text-xs">Rule Evaluation & Finding Description:</span>
        <span class="text-[10px] text-slate-400 font-mono">Cut ${f.data_cut} (${f.protocol_version})</span>
      </div>
      <div class="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-200 leading-relaxed">
        ${f.description}
      </div>
    </div>

    <!-- Traceable Evidence Reference -->
    <div>
      <div class="text-[11px] font-semibold text-slate-300 mb-1">Traceable Evidence Identity:</div>
      <div class="flex gap-2">
        ${(f.evidence_references || [])
          .map(
            (ref) => `
          <button onclick="inspectEvidenceKey('${ref}')" class="px-2.5 py-1 bg-indigo-950 border border-indigo-500/40 text-indigo-300 font-mono rounded hover:bg-indigo-900 transition-colors">
            <i class="fa-solid fa-fingerprint text-[10px]"></i> ${ref}
          </button>
        `
          )
          .join("")}
      </div>
    </div>

    <!-- Site Reply -->
    <div class="space-y-1">
      <div class="text-[11px] font-semibold text-slate-300">Site Query & Reply Workflow:</div>
      ${siteReplyHtml}
    </div>

    <!-- Monitor Decision -->
    <div class="space-y-1">
      <div class="text-[11px] font-semibold text-slate-300">Medical Monitor Adjudication:</div>
      ${monitorDecisionHtml}
    </div>
  `;

  modal.classList.remove("hidden");
}

function inspectEvidenceKey(evidenceKey) {
  const parts = evidenceKey.split("|");
  if (parts.length === 3) {
    openEvidenceModal(parts[0], parts[1], parseInt(parts[2], 10));
  }
}

// Open Single Evidence Record Modal
async function openEvidenceModal(domain, usubjid, seq) {
  const modal = document.getElementById("evidenceModal");
  const title = document.getElementById("modalEvidenceTitle");
  const ident = document.getElementById("modalEvidenceIdentity");
  const body = document.getElementById("modalEvidenceBody");

  title.textContent = `Evidence Inspection: ${domain} Record`;
  ident.textContent = `${domain}|${usubjid}|${seq} (Cut ${state.currentCut})`;

  try {
    const res = await fetch(
      `/api/record?study=${state.currentStudy}&domain=${domain}&usubjid=${usubjid}&seq=${seq}&cut=${state.currentCut}`
    );
    const rec = await res.json();

    let corrHtml = "";
    if (rec.is_corrected) {
      corrHtml = `
        <div class="p-3 bg-amber-950/30 border border-amber-500/40 rounded-lg text-xs space-y-1">
          <div class="font-bold text-amber-400 flex items-center gap-1.5">
            <i class="fa-solid fa-clock-rotate-left"></i> Retrospective Field Correction Applied at Cut ${rec.corrected_at_cut}
          </div>
          ${(rec.correction_history || [])
            .map(
              (h) => `
            <div class="text-[11px] text-slate-300">
              Field <b>${h.field_name}</b> changed from <span class="text-rose-300 line-through font-mono">${h.original_value}</span> to <span class="text-emerald-300 font-mono font-bold">${h.corrected_value}</span>.
              <br><span class="text-slate-400 italic">Audit Reason: ${h.reason}</span>
            </div>
          `
            )
            .join("")}
        </div>
      `;
    }

    // Laboratory Special Interpretation Box
    let labBox = "";
    if (domain.toUpperCase() === "LB" && rec.interpretation) {
      const interp = rec.interpretation;
      labBox = `
        <div class="p-3 bg-cyan-950/30 border border-cyan-500/40 rounded-lg text-xs space-y-1">
          <div class="font-bold text-cyan-400 flex items-center gap-1.5">
            <i class="fa-solid fa-flask"></i> Laboratory Safety Interpretation (LAB + TEST: ${interp.lab} &bull; ${interp.test})
          </div>
          <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-300 mt-1">
            <div>Reported: <b class="text-white font-mono">${interp.raw_value} ${interp.reported_unit}</b></div>
            <div>Normalized: <b class="text-cyan-300 font-mono">${interp.normalized_value ?? "--"} ${interp.normalized_unit}</b></div>
            <div>Reference Range: <b class="text-slate-300 font-mono">[${interp.ref_low ?? 0} - ${interp.ref_high ?? "--"} ${interp.ref_unit}]</b></div>
            <div>Special Status: <b class="text-indigo-300 font-mono">${interp.special_status}</b></div>
          </div>
        </div>
      `;
    }

    // Key-value table of clinical fields
    const fields = rec.fields || {};
    const fieldRows = Object.entries(fields)
      .map(
        ([k, v]) => `
      <tr class="border-b border-slate-800/60">
        <td class="py-1.5 px-3 font-semibold text-slate-400 w-1/3">${k}</td>
        <td class="py-1.5 px-3 font-mono text-slate-200">${v ?? ""}</td>
      </tr>
    `
      )
      .join("");

    body.innerHTML = `
      ${corrHtml}
      ${labBox}
      <div class="border border-slate-800 rounded-lg overflow-hidden">
        <table class="w-full text-left text-xs">
          <tbody class="divide-y divide-slate-800/60">
            ${fieldRows}
          </tbody>
        </table>
      </div>
    `;

    modal.classList.remove("hidden");
  } catch (err) {
    console.error("Error opening evidence modal:", err);
  }
}

function closeEvidenceModal() {
  document.getElementById("evidenceModal")?.classList.add("hidden");
}

// TAB 5: MONITORING QUEUE
async function loadQueue() {
  try {
    const res = await fetch(`/api/findings?study=${state.currentStudy}&cut=${state.currentCut}`);
    const data = await res.json();
    const findings = data.findings || [];

    const clarifyList = document.getElementById("queueClarifyList");
    const openList = document.getElementById("queueOpenList");
    const resolvedList = document.getElementById("queueResolvedList");

    const clarifies = findings.filter(
      (f) => f.monitor_decision?.decision === "CLARIFY" || f.status === "UNDER_REVIEW"
    );
    const opens = findings.filter(
      (f) => f.status === "OPEN" && f.monitor_decision?.decision !== "CLARIFY"
    );
    const resolveds = findings.filter(
      (f) => f.status === "RESOLVED" || f.monitor_decision?.decision === "APPROVED"
    );

    document.getElementById("queueClarifyCount").textContent = clarifies.length;
    document.getElementById("queueOpenCount").textContent = opens.length;
    document.getElementById("queueResolvedCount").textContent = resolveds.length;

    const renderCard = (f, borderCol, btnText) => `
      <div class="p-3 bg-slate-900 border ${borderCol} rounded-lg space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-white">${f.finding_code}</span>
          <span class="text-[10px] font-mono text-indigo-400">${f.subject}</span>
        </div>
        <p class="text-[11px] text-slate-300 leading-tight">${f.description}</p>
        ${f.monitor_decision?.decision === 'CLARIFY' ? `<div class="p-1.5 mt-1 bg-amber-950/50 border border-amber-500/30 rounded text-[10px] text-amber-300"><i class="fa-solid fa-circle-question"></i> ${f.monitor_decision.inquiry || 'Clarification required.'}</div>` : ''}
        <div class="flex items-center justify-between pt-2 border-t border-slate-800 text-[10px]">
          <span class="text-slate-400">Site: ${f.site}</span>
          <button onclick="inspectFindingDetail('${f.finding_code}', '${f.subject}')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-white rounded font-medium">
            ${btnText}
          </button>
        </div>
      </div>
    `;

    if (clarifyList) {
      clarifyList.innerHTML = clarifies.length
        ? clarifies.map((f) => renderCard(f, "border-amber-500/40", "View Query")).join("")
        : `<p class="text-xs text-slate-500">No items requiring clarification.</p>`;
    }
    if (openList) {
      openList.innerHTML = opens.length
        ? opens.map((f) => renderCard(f, "border-indigo-500/40", "Triage")).join("")
        : `<p class="text-xs text-slate-500">Queue is clean.</p>`;
    }
    if (resolvedList) {
      resolvedList.innerHTML = resolveds.length
        ? resolveds.map((f) => renderCard(f, "border-emerald-500/40", "View Audit")).join("")
        : `<p class="text-xs text-slate-500">No resolved items.</p>`;
    }
  } catch (err) {
    console.error("Error loading queue:", err);
  }
}

// TAB 6: SITE QUERIES
async function loadQueries() {
  try {
    const res = await fetch(`/api/responses?study=${state.currentStudy}`);
    const data = await res.json();
    const replies = data.site_replies || {};

    const tbody = document.getElementById("siteQueriesTableBody");
    if (!tbody) return;

    const rows = Object.entries(replies).map(([key, val]) => {
      const isDefault = key === "_default";
      const parts = key.split("|");
      const domain = parts[0] || "--";
      const subj = parts[1] || "--";
      const replyText = typeof val === "object" ? val.reply : String(val);
      const timeStr = typeof val === "object" ? val.timestamp || "--" : "--";

      return `
        <tr class="hover:bg-slate-900/80 transition-colors">
          <td class="py-2.5 px-3 font-mono text-sky-400 font-semibold">${key}</td>
          <td class="py-2.5 px-3">${domain}</td>
          <td class="py-2.5 px-3 font-medium text-white">${subj}</td>
          <td class="py-2.5 px-3 text-slate-300 max-w-md">${replyText}</td>
          <td class="py-2.5 px-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${
              isDefault ? "bg-slate-800 text-slate-400" : "bg-sky-500/20 text-sky-300 border border-sky-500/30"
            }">
              ${isDefault ? "Default Fallback" : "Record Specific"}
            </span>
          </td>
          <td class="py-2.5 px-3 text-slate-400 text-[11px]">${timeStr}</td>
        </tr>
      `;
    });

    tbody.innerHTML = rows.join("");
  } catch (err) {
    console.error("Error loading queries:", err);
  }
}

// TAB 7: MONITOR DECISIONS
async function loadDecisions() {
  try {
    const res = await fetch(`/api/responses?study=${state.currentStudy}`);
    const data = await res.json();
    const decisions = data.monitor_decisions || {};

    const tbody = document.getElementById("monitorDecisionsTableBody");
    if (!tbody) return;

    const rows = Object.entries(decisions).map(([key, val]) => {
      const dec = typeof val === "object" ? val.decision : String(val);
      const monName = typeof val === "object" ? val.monitor_name || "Medical Monitor" : "Medical Monitor";
      const comment = typeof val === "object" ? val.comment || "--" : "--";
      const inquiry = typeof val === "object" ? val.inquiry || "--" : "--";

      const isApp = dec === "APPROVED";
      const isRej = dec === "REJECTED";
      const badgeClass = isApp
        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
        : isRej
        ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
        : "bg-amber-500/20 text-amber-300 border-amber-500/30";

      return `
        <tr class="hover:bg-slate-900/80 transition-colors">
          <td class="py-2.5 px-3 font-mono text-rose-300 font-semibold">${key}</td>
          <td class="py-2.5 px-3">
            <span class="px-2.5 py-0.5 rounded text-[10px] font-extrabold border ${badgeClass}">${dec}</span>
          </td>
          <td class="py-2.5 px-3 font-medium text-white">${monName}</td>
          <td class="py-2.5 px-3 text-slate-300 max-w-sm">${comment}</td>
          <td class="py-2.5 px-3 text-amber-200/90 text-[11px] max-w-sm">${inquiry}</td>
        </tr>
      `;
    });

    tbody.innerHTML = rows.join("");
  } catch (err) {
    console.error("Error loading monitor decisions:", err);
  }
}

// TAB 8: STUDY DOCUMENTS
async function loadDocuments() {
  try {
    const res = await fetch(`/api/documents?study=${state.currentStudy}`);
    const data = await res.json();
    const docs = data.documents || [];

    const btnContainer = document.getElementById("documentSelectorButtons");
    if (!btnContainer) return;

    btnContainer.innerHTML = docs
      .map(
        (d) => `
      <button onclick="viewDocumentContent('${d.name}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors">
        <i class="fa-regular fa-file-lines text-indigo-400"></i> ${d.name}
      </button>
    `
      )
      .join("");

    if (docs.length > 0 && !state.activeDocument) {
      await viewDocumentContent(docs[0].name);
    }
  } catch (err) {
    console.error("Error loading documents:", err);
  }
}

async function viewDocumentContent(docName) {
  state.activeDocument = docName;
  try {
    const res = await fetch(`/api/documents?study=${state.currentStudy}&name=${docName}`);
    const doc = await res.json();
    const area = document.getElementById("documentContentArea");
    if (area) {
      area.textContent = doc.content || "Document content empty.";
    }
  } catch (err) {
    console.error("Error fetching document:", err);
  }
}

// ASK ATLAS / ANSWER ENGINE UI HANDLERS
function setQueryPrompt(promptText) {
  const input = document.getElementById("askAtlasInput");
  if (input) {
    input.value = promptText;
    input.focus();
  }
}

async function submitQuestion(event) {
  if (event) event.preventDefault();
  const input = document.getElementById("askAtlasInput");
  const question = input ? input.value.trim() : "";
  if (!question) return;

  const btn = document.getElementById("btnAskSubmit");
  const originalBtnHtml = btn ? btn.innerHTML : "Ask ATLAS";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Reasoning...</span>`;
  }

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        study: state.currentStudy,
        cut: state.currentCut,
      }),
    });
    const ans = await res.json();

    const container = document.getElementById("answerResultContainer");
    const directText = document.getElementById("answerDirectText");
    const typeBadge = document.getElementById("answerTypeBadge");
    const protBadge = document.getElementById("answerProtocolBadge");
    const rationaleText = document.getElementById("answerRationaleText");
    const evCount = document.getElementById("answerEvidenceCount");
    const evChips = document.getElementById("answerEvidenceChips");
    const respContainer = document.getElementById("answerResponsesContainer");

    if (container) container.classList.remove("hidden");
    if (directText) directText.textContent = ans.answer || "No response generated.";
    if (typeBadge) typeBadge.textContent = ans.question_type || "ANSWER";
    if (protBadge) protBadge.textContent = `Protocol ${ans.protocol_version?.toUpperCase() || "V1"} • Cut ${ans.cut || state.currentCut}`;
    if (rationaleText) rationaleText.textContent = ans.explanation || "";

    // Evidence Chips
    const refs = ans.evidence || [];
    if (evCount) evCount.textContent = refs.length;
    if (evChips) {
      if (refs.length === 0) {
        evChips.innerHTML = `<span class="text-slate-500 text-[11px]">No specific individual records cited.</span>`;
      } else {
        evChips.innerHTML = refs
          .map((ref) => {
            const parts = ref.split("|");
            const d = parts[0] || "";
            const s = parts[1] || "";
            const seq = parseInt(parts[2], 10) || 1;
            return `
            <button onclick="openEvidenceModal('${d}', '${s}', ${seq})" class="px-2.5 py-1 bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-500/40 text-indigo-300 font-mono text-[11px] rounded flex items-center gap-1.5 transition-colors cursor-pointer">
              <i class="fa-solid fa-fingerprint text-[10px] text-indigo-400"></i>
              <span>${ref}</span>
            </button>
          `;
          })
          .join("");
      }
    }

    // Site / Monitor Responses Context
    if (respContainer) {
      let html = "";
      const siteReps = ans.site_reply || [];
      const monDecs = ans.monitor_decision || [];

      if (siteReps.length === 0 && monDecs.length === 0) {
        html = `<p class="text-slate-500 text-[11px]">No external queries or monitor decisions linked to this query topic.</p>`;
      } else {
        if (siteReps.length > 0) {
          html += siteReps.map((sr) => `
            <div class="p-2.5 bg-slate-900 border border-sky-500/30 rounded">
              <div class="flex items-center justify-between text-[10px] text-sky-400 font-semibold mb-1">
                <span><i class="fa-solid fa-reply"></i> Site Reply (${sr.is_default ? "Default" : "Specific"})</span>
                <span>${sr.domain || ""}|${sr.usubjid || ""}|${sr.seq || ""}</span>
              </div>
              <p class="text-slate-200 text-[11px] leading-tight">${sr.reply}</p>
            </div>
          `).join("");
        }

        if (monDecs.length > 0) {
          html += monDecs.map((md) => {
            const isApp = md.decision === "APPROVED";
            const isRej = md.decision === "REJECTED";
            const decColor = isApp ? "text-emerald-400 border-emerald-500/40" : isRej ? "text-rose-400 border-rose-500/40" : "text-amber-400 border-amber-500/40";
            return `
              <div class="p-2.5 bg-slate-900 border ${decColor} rounded">
                <div class="flex items-center justify-between text-[10px] font-bold mb-1">
                  <span class="${decColor}">${md.decision}</span>
                  <span class="text-slate-400">${md.monitor_name || "Medical Monitor"}</span>
                </div>
                ${md.comment ? `<p class="text-slate-200 text-[11px] mb-1"><b>Comment:</b> ${md.comment}</p>` : ""}
                ${md.inquiry ? `<p class="text-amber-300 text-[11px] bg-amber-950/40 p-1.5 rounded border border-amber-500/30"><b>Clarification:</b> ${md.inquiry}</p>` : ""}
              </div>
            `;
          }).join("");
        }
      }
      respContainer.innerHTML = html;
    }
  } catch (err) {
    console.error("Error asking ATLAS:", err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalBtnHtml;
    }
  }
}


// --- NEW APP EXTENSIONS (Lab, Cut Compare, Evidence, Search) ---

async function loadLabExplorer() {
  const subj = document.getElementById("labFilterSubject")?.value || "";
  const test = document.getElementById("labFilterTest")?.value || "";
  try {
    const res = await fetch(`/api/labs?study=${state.currentStudy}&cut=${state.currentCut}&subject=${subj}&test=${test}`);
    const data = await res.json();
    const tbody = document.getElementById("labExplorerTableBody");
    if (!tbody) return;
    
    tbody.innerHTML = data.labs.map(lb => {
      const isNorm = lb.normalized_value !== null;
      return `
        <tr class="hover:bg-slate-900/80">
          <td class="py-2 px-3 font-mono text-indigo-300 font-semibold">${lb.subject}</td>
          <td class="py-2 px-3"><div class="font-bold text-white">${lb.test}</div><div class="text-[10px] text-slate-500">${lb.lab}</div></td>
          <td class="py-2 px-3 text-slate-300 font-mono">${lb.reported_value} ${lb.reported_unit || ""}</td>
          <td class="py-2 px-3 font-mono font-bold ${isNorm ? 'text-cyan-400' : 'text-slate-500'}">${isNorm ? lb.normalized_value + ' ' + (lb.normalized_unit||'') : '--'}</td>
          <td class="py-2 px-3 text-slate-400 text-[10px]">[${lb.ref_low ?? '--'} - ${lb.ref_high ?? '--'}]</td>
          <td class="py-2 px-3 text-slate-400">${lb.date || '--'}</td>
          <td class="py-2 px-3">
            <button onclick="inspectEvidenceKey('${lb.evidence}')" class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded text-[10px]"><i class="fa-solid fa-fingerprint"></i></button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading lab explorer:", err);
  }
}

async function initCutComparison() {
  const selN = document.getElementById("cutCompareN");
  const selM = document.getElementById("cutCompareM");
  if (!selN || !selM) return;
  
  const html = state.cuts.map(c => `<option value="${c.cut_id}">Cut ${c.cut_id}</option>`).join("");
  selN.innerHTML = html;
  selM.innerHTML = html;
  
  if (state.cuts.length > 1) {
    selN.value = state.cuts[state.cuts.length - 2].cut_id;
    selM.value = state.cuts[state.cuts.length - 1].cut_id;
  }
}

async function loadCutComparison() {
  const n = document.getElementById("cutCompareN")?.value;
  const m = document.getElementById("cutCompareM")?.value;
  if (!n || !m) return;
  
  try {
    const res = await fetch(`/api/compare_cuts?study=${state.currentStudy}&cut_n=${n}&cut_m=${m}`);
    const data = await res.json();
    
    let protoHtml = "";
    if (data.protocol_n !== data.protocol_m) {
      protoHtml = `<div class="col-span-1 md:col-span-2 p-3 bg-indigo-950/40 border border-indigo-500/40 rounded-lg text-xs text-indigo-200 mb-4 flex items-center gap-2"><i class="fa-solid fa-code-branch"></i> <b>Protocol Change Detected:</b> ${data.protocol_n.toUpperCase()} &rarr; ${data.protocol_m.toUpperCase()}</div>`;
    } else {
      protoHtml = `<div class="col-span-1 md:col-span-2 p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-400 mb-4 flex items-center gap-2"><i class="fa-solid fa-code-branch"></i> <b>Protocol Version:</b> ${data.protocol_m.toUpperCase()} (Unchanged)</div>`;
    }
    
    const resultsContainer = document.getElementById("cutCompareResults");
    
    // Inject protoHtml before the 4 grid columns
    resultsContainer.innerHTML = protoHtml + `
      <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
        <h3 class="text-sm font-bold text-white mb-2">New Records <span id="cutNewRecordsCount" class="text-xs ml-2 text-slate-400">(${data.new_records.length})</span></h3>
        <div id="cutNewRecordsList" class="space-y-1 text-xs text-slate-300 max-h-64 overflow-y-auto">
          ${data.new_records.map(r => `<div class="cursor-pointer text-indigo-300 hover:text-indigo-200 font-mono" onclick="inspectEvidenceKey('${r}')"><i class="fa-solid fa-plus text-emerald-400 w-4"></i> ${r}</div>`).join("") || "None"}
        </div>
      </div>
      <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
        <h3 class="text-sm font-bold text-white mb-2">Corrected Records <span id="cutCorrectedCount" class="text-xs ml-2 text-slate-400">(${data.corrected_records.length})</span></h3>
        <div id="cutCorrectedList" class="space-y-1 text-xs text-slate-300 max-h-64 overflow-y-auto">
          ${data.corrected_records.map(r => `<div class="cursor-pointer text-amber-300 hover:text-amber-200 font-mono" onclick="inspectEvidenceKey('${r.evidence}')"><i class="fa-solid fa-pen text-amber-400 w-4"></i> ${r.evidence} [${r.field}: ${r.old} &rarr; ${r.new}]</div>`).join("") || "None"}
        </div>
      </div>
      <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
        <h3 class="text-sm font-bold text-white mb-2">New Findings <span id="cutNewFindingsCount" class="text-xs ml-2 text-slate-400">(${data.new_findings.length})</span></h3>
        <div id="cutNewFindingsList" class="space-y-1 text-xs text-slate-300 max-h-64 overflow-y-auto">
          ${data.new_findings.map(f => `<div class="cursor-pointer text-rose-300 hover:text-rose-200 font-mono" onclick="switchTab('findings')"><i class="fa-solid fa-triangle-exclamation text-rose-400 w-4"></i> ${f}</div>`).join("") || "None"}
        </div>
      </div>
      <div class="bg-slate-950 p-4 rounded-lg border border-slate-800">
        <h3 class="text-sm font-bold text-white mb-2">Resolved Findings <span id="cutResolvedFindingsCount" class="text-xs ml-2 text-slate-400">(${data.resolved_findings.length})</span></h3>
        <div id="cutResolvedFindingsList" class="space-y-1 text-xs text-slate-300 max-h-64 overflow-y-auto">
          ${data.resolved_findings.map(f => `<div class="cursor-pointer text-emerald-300 font-mono" onclick="switchTab('findings')"><i class="fa-solid fa-check text-emerald-400 w-4"></i> ${f}</div>`).join("") || "None"}
        </div>
      </div>
    `;
    
  } catch (err) {
    console.error("Error loading cut comparison:", err);
  }
}

async function executeGlobalSearch() {
  const q = document.getElementById("globalSearchInput")?.value?.trim();
  const resDiv = document.getElementById("globalSearchResults");
  if (!q) {
    if (resDiv) resDiv.classList.add("hidden");
    return;
  }
  
  try {
    const res = await fetch(`/api/search?study=${state.currentStudy}&cut=${state.currentCut}&q=${encodeURIComponent(q)}`);
    const data = await res.json();
    
    if (resDiv) {
      resDiv.classList.remove("hidden");
      if (data.results.length === 0) {
        resDiv.innerHTML = `<div class="p-3 text-slate-400 text-center">No results found for "${q}".</div>`;
      } else {
        resDiv.innerHTML = data.results.map(r => {
          if (r.type === "subject") {
            return `<div class="p-2 hover:bg-slate-800 cursor-pointer flex items-center gap-2 rounded text-emerald-300" onclick="window.loadSubjectToPatient360('${r.id}'); document.getElementById('globalSearchResults').classList.add('hidden');"><i class="fa-solid fa-hospital-user w-4"></i> Subject: <b>${r.id}</b> (Site ${r.site})</div>`;
          } else if (r.type === "finding") {
            return `<div class="p-2 hover:bg-slate-800 cursor-pointer flex items-center gap-2 rounded text-amber-300" onclick="inspectFindingDetail('${r.id}', '${r.subject}'); document.getElementById('globalSearchResults').classList.add('hidden');"><i class="fa-solid fa-triangle-exclamation w-4"></i> Finding: <b>${r.id}</b> (${r.subject})</div>`;
          } else if (r.type === "evidence") {
            return `<div class="p-2 hover:bg-slate-800 cursor-pointer flex items-center gap-2 rounded text-indigo-300" onclick="inspectEvidenceKey('${r.id}'); document.getElementById('globalSearchResults').classList.add('hidden');"><i class="fa-solid fa-fingerprint w-4"></i> Record: <span class="font-mono">${r.id}</span></div>`;
          }
          return "";
        }).join("");
      }
    }
  } catch (err) {
    console.error("Error searching:", err);
  }
}
window.loadEvidenceTab = loadEvidenceTab;

// ============================================================================
// STAGE 2 / PROBLEM 2 LOGIC
// ============================================================================

async function updateMemoryState() {
  try {
    const res = await fetch("/api/memory");
    const data = await res.json();
    const mem = data || {};
    document.getElementById("memoryQueries").textContent = `${(mem.query_history || []).length} Queries remembered`;
    document.getElementById("memoryEscalations").textContent = `${(mem.escalation_history || []).length} Escalations remembered`;
    document.getElementById("memorySubjects").textContent = `${Object.keys(mem.subject_flags || {}).length} Subjects with repeated findings`;
    document.getElementById("memorySites").textContent = `${Object.keys(mem.site_flags || {}).length} Sites with recurring problems`;
  } catch (err) {
    console.error("Error loading memory state:", err);
  }
}

async function runReviewCycle() {
  try {
    const btn = document.querySelector("#view-humangate button");
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i> Running...`;
    btn.disabled = true;
    
    await fetch("/api/run_cycle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ study: state.currentStudy, cut: state.currentCut })
    });
    
    btn.innerHTML = `<i class="fa-solid fa-check mr-1"></i> Done`;
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }, 2000);
    
    await refreshAll();
  } catch(err) {
    console.error("Error running cycle:", err);
    alert("Error running cycle");
  }
}

async function loadHumanGate() {
  await updateMemoryState();
  try {
    const res = await fetch("/api/pending_escalations");
    const data = await res.json();
    const pending = data.pending || {};
    
    const tbody = document.getElementById("escalationsTableBody");
    const countBadge = document.getElementById("pendingCount");
    
    const keys = Object.keys(pending);
    countBadge.textContent = `${keys.length} pending`;
    
    if (keys.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500 italic">No pending escalations. Run Review Cycle to generate drafts.</td></tr>`;
      return;
    }
    
    tbody.innerHTML = keys.map(k => {
      const p = pending[k];
      const code = k.split("|")[0];
      const subjOrSite = k.split("|")[1];
      
      const history = p.history || [];
      const latest = history[history.length - 1] || {};
      const summary = latest.summary || "";
      const evidence = latest.evidence || [];
      
      const evButtons = evidence.map(e => `<button onclick="openEvidenceModal2('${e.domain}|${e.usubjid}|${e.seq}')" class="text-indigo-400 hover:text-indigo-300 mr-2 underline">${e.domain}|${e.usubjid}|${e.seq}</button>`).join("");
      
      return `
        <tr class="hover:bg-slate-900/80 transition-colors">
          <td class="py-2.5 px-4 font-medium text-white">${code}</td>
          <td class="py-2.5 px-4 text-slate-300">${subjOrSite}</td>
          <td class="py-2.5 px-4 whitespace-normal min-w-[300px]">
            <div class="text-slate-300 mb-1 leading-relaxed">${summary}</div>
            <div class="text-[10px] font-mono mt-2 p-2 bg-slate-950 rounded">${evButtons || 'No direct evidence linked'}</div>
          </td>
          <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 font-bold">${p.decision || "PENDING"}</span></td>
          <td class="py-2.5 px-4 align-top">
            <div class="flex flex-col gap-2 w-24">
              <button onclick="respondEscalation('${code}', '${subjOrSite}', 'APPROVED')" class="px-2 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded shadow text-[10px] font-semibold w-full">APPROVE</button>
              <button onclick="respondEscalation('${code}', '${subjOrSite}', 'REJECTED')" class="px-2 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded shadow text-[10px] font-semibold w-full">REJECT</button>
              <button onclick="respondEscalation('${code}', '${subjOrSite}', 'CLARIFY')" class="px-2 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded shadow text-[10px] font-semibold w-full">CLARIFY</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading human gate:", err);
  }
}

async function respondEscalation(code, usubjid, manualDecision) {
    const payload = {
        code: code,
        usubjid: usubjid,
        severity: "CRITICAL",
        summary: `Monitor replied: ${manualDecision}.`,
        evidence: []
    };
    
    await fetch("/api/escalations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    await refreshAll();
}

async function loadCycleReport() {
  try {
    const res = await fetch("/api/cycle_report");
    if (!res.ok) {
       document.getElementById("reportSummaryCards").innerHTML = `<div class="col-span-4 text-slate-400 p-4">No cycle report available. Run a cycle first.</div>`;
       return;
    }
    const r = await res.json();
    
    document.getElementById("reportSummaryCards").innerHTML = `
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="text-[11px] font-medium text-slate-400 uppercase">Cut & Protocol</div>
          <div class="text-xl font-bold text-white mt-1">Cut ${r.cut} <span class="text-sm text-indigo-400 ml-2">v${r.protocol_version}</span></div>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="text-[11px] font-medium text-slate-400 uppercase">Total Findings</div>
          <div class="text-xl font-bold text-white mt-1">${r.total_findings || 0}</div>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="text-[11px] font-medium text-slate-400 uppercase">Queries Raised</div>
          <div class="text-xl font-bold text-blue-400 mt-1">${r.queries || 0}</div>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="text-[11px] font-medium text-slate-400 uppercase">Escalations</div>
          <div class="text-xl font-bold text-rose-400 mt-1">${r.medical_escalations || 0}</div>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="text-[11px] font-medium text-slate-400 uppercase">Compliance Deviations</div>
          <div class="text-xl font-bold text-amber-400 mt-1">${r.compliance_deviations || 0}</div>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div class="text-[11px] font-medium text-slate-400 uppercase">Monitoring-only Signals</div>
          <div class="text-xl font-bold text-emerald-400 mt-1">${(r.monitoring_only_findings || []).length}</div>
        </div>
    `;
    
    const actionsList = document.getElementById("reportActionsList");
    actionsList.innerHTML = (r.executed_actions || []).map(a => `<li><i class="fa-solid fa-check text-emerald-400 mr-2"></i> <strong class="text-white">${a.id}</strong>: <span class="text-slate-400">${a.action}</span></li>`).join("");
    if (!actionsList.innerHTML) actionsList.innerHTML = `<li class="text-slate-500 italic">No executed actions.</li>`;
    
  } catch(err) {
    console.error(err);
  }
}

async function loadQueries2() {
  try {
    const res = await fetch("/api/queries_list");
    const data = await res.json();
    const queries = data.queries || [];
    
    const tbody = document.getElementById("queriesTableBody");
    if (queries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="px-4 py-8 text-center text-slate-500 italic">No queries generated.</td></tr>`;
      return;
    }
    
    tbody.innerHTML = queries.map(q => {
      return `
        <tr class="hover:bg-slate-900/80 transition-colors">
          <td class="py-2.5 px-4 font-mono text-sky-400 font-semibold align-top">${q.id}</td>
          <td class="py-2.5 px-4 text-slate-300 align-top">${q.usubjid} <span class="text-slate-500 ml-1">(${q.domain})</span></td>
          <td class="py-2.5 px-4 text-slate-300 whitespace-normal max-w-lg leading-relaxed">${q.text}</td>
          <td class="py-2.5 px-4 align-top"><span class="px-2 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-300 font-bold">${q.status || "OPEN"}</span></td>
        </tr>
      `;
    }).join("");
  } catch(err) {
    console.error(err);
  }
}

async function loadTrace() {
  try {
    const res = await fetch("/api/trace");
    const data = await res.json();
    const trace = data.trace || [];
    
    const list = document.getElementById("traceList");
    if (trace.length === 0) {
      list.innerHTML = `<li class="text-center text-slate-500 italic py-4">No trace available.</li>`;
      return;
    }
    
    const counts = { detect: 0, medical_review: 0, data_manager: 0, compliance: 0, human_gate: 0, execute: 0 };
    trace.forEach(t => { if(counts[t.node] !== undefined) counts[t.node]++; });
    
    ["detect", "medical", "data", "compliance", "human", "execute"].forEach(n => {
        const el = document.getElementById(`tl-${n}`);
        if(el) {
            const mapName = n === "medical" ? "medical_review" : n === "data" ? "data_manager" : n === "human" ? "human_gate" : n;
            if (counts[mapName] > 0) {
                el.classList.remove("bg-slate-800", "text-slate-300");
                el.classList.add("bg-amber-500", "text-slate-900", "shadow-[0_0_10px_rgba(245,158,11,0.5)]");
            } else {
                el.classList.remove("bg-amber-500", "text-slate-900", "shadow-[0_0_10px_rgba(245,158,11,0.5)]");
                el.classList.add("bg-slate-800", "text-slate-300");
            }
        }
    });
    
    list.innerHTML = trace.map(t => {
      const evs = (t.evidence && t.evidence.length > 0) ? `<div class="text-[10px] font-mono text-indigo-400 mt-2 bg-slate-950 p-2 rounded inline-block cursor-pointer" onclick="openEvidenceModal2('${t.evidence[0]}')">Evidence: ${t.evidence.join(', ')}</div>` : "";
      return `
        <li class="pl-4 border-l-2 border-slate-700 pb-4 relative">
            <div class="absolute w-2 h-2 bg-amber-500 rounded-full -left-[5px] top-1"></div>
            <div class="flex items-center gap-2 mb-1">
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 uppercase">${t.node}</span>
                <span class="text-[10px] text-slate-500">${new Date(t.timestamp).toLocaleTimeString()} (Cut ${t.cut}, v${t.protocol_version})</span>
            </div>
            <div class="text-sm text-slate-200 whitespace-normal leading-relaxed">${t.action}</div>
            ${evs}
        </li>
      `;
    }).join("");
    
  } catch(err) {
    console.error(err);
  }
}

function openEvidenceModal2(identity) {
    if(typeof window.inspectEvidenceKey === 'function') {
        window.inspectEvidenceKey(identity);
    } else {
        alert("Evidence: " + identity);
    }
}

function loadEvidenceTab() {
  const key = document.getElementById("evidenceInputKey")?.value?.trim();
  if (!key) return;
  const parts = key.split("|");
  if (parts.length === 3) {
    const d = parts[0];
    const s = parts[1];
    const seq = parseInt(parts[2], 10);
    // Fetch and render in tab
    fetch(`/api/record?study=${state.currentStudy}&domain=${d}&usubjid=${s}&seq=${seq}&cut=${state.currentCut}`)
      .then(res => res.json())
      .then(rec => {
        const area = document.getElementById("evidenceTabContent");
        let html = `<div class="text-white font-bold mb-2">Record: ${d} | ${s} | ${seq}</div>`;
        if (rec.fields) {
          html += `<table class="w-full text-left border border-slate-700"><tbody class="divide-y divide-slate-700">`;
          for (const [k, v] of Object.entries(rec.fields)) {
            html += `<tr><td class="py-1 px-2 font-semibold text-slate-400 w-1/3">${k}</td><td class="py-1 px-2 font-mono">${v??''}</td></tr>`;
          }
          html += `</tbody></table>`;
        }
        area.innerHTML = html;
      })
      .catch(err => {
         const area = document.getElementById("evidenceTabContent");
         area.innerHTML = `<div class="text-rose-400"><i class="fa-solid fa-circle-exclamation"></i> Error loading record: ${err.message || 'Not found'}</div>`;
      });
  }
}

window.loadSubjectToPatient360 = function(subj) {
  const sel = document.getElementById("p360SubjectSelect");
  if (sel) { sel.value = subj; }
  switchTab("patient360");
  loadPatient360();
};
