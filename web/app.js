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
  ];

  tabs.forEach((t) => {
    const btn = document.getElementById(`tab-${t}`);
    const view = document.getElementById(`view-${t}`);
    if (t === tabId) {
      if (btn) {
        btn.classList.remove("border-transparent", "text-slate-400");
        btn.classList.add("border-indigo-500", "text-white");
      }
      if (view) view.classList.remove("hidden");
    } else {
      if (btn) {
        btn.classList.remove("border-indigo-500", "text-white");
        btn.classList.add("border-transparent", "text-slate-400");
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
    if (directText) directText.textContent = ans.direct_answer || "No response generated.";
    if (typeBadge) typeBadge.textContent = ans.question_type || "ANSWER";
    if (protBadge) protBadge.textContent = `Protocol ${ans.protocol_version?.toUpperCase() || "V1"} • Cut ${ans.cut || state.currentCut}`;
    if (rationaleText) rationaleText.textContent = ans.clinical_rationale || "";

    // Evidence Chips
    const refs = ans.evidence_references || [];
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
      const siteReps = ans.site_replies || [];
      const monDecs = ans.monitor_decisions || [];

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
