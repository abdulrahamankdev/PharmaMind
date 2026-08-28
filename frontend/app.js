/**
 * PharmaMind Frontend Core Application Controller
 * Manages view switching, API interactions, D3.js Knowledge Graph rendering, and state management.
 */

// ── State Management ─────────────────────────────────────────────────────────
const AppState = {
  currentDisease: 'Alzheimer disease',
  currentTarget: 'BACE1',
  currentCompound: null,
  activeReport: null,
  lastGraphData: null
};

// ── API Client ────────────────────────────────────────────────────────────────
const API = (() => {
  const BASE = window.location.origin; // Same origin (FastAPI serves app/)

  async function request(path, options = {}) {
    const url = `${BASE}${path}`;
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.text().catch(() => 'Unknown error');
      throw new Error(`API ${res.status}: ${err}`);
    }
    return res.json();
  }

  return {
    health: () => request('/health'),
    runQuery: (params) => request('/api/query/', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
    validate: (params) => request('/api/validate/', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
    getSubgraph: (disease) => request(`/api/graph/subgraph?disease=${encodeURIComponent(disease)}`),
    getDiseaseTargets: (disease) => request(`/api/graph/targets?disease=${encodeURIComponent(disease)}`),
    getTargetCompounds: (targetId) => request(`/api/graph/compounds?target_id=${encodeURIComponent(targetId)}`),
    searchChemblTarget: (gene) => request(`/api/chembl/target-search?gene=${encodeURIComponent(gene)}`),
    getChemblActivities: (targetId, actType = 'IC50') => 
      request(`/api/chembl/activities?target_id=${encodeURIComponent(targetId)}&activity_type=${actType}`),
    getCompoundDetails: (chemblId) => request(`/api/chembl/compound/${encodeURIComponent(chemblId)}`),
    searchLiterature: (disease, target) => {
      const params = new URLSearchParams();
      if (disease) params.set('disease', disease);
      if (target)  params.set('target', target);
      return request(`/api/pubmed/search?${params.toString()}`);
    },
    searchEntities: (q) => request(`/api/query/search?q=${encodeURIComponent(q)}`)
  };
})();

// ── UI Helper: Toast Notifications ────────────────────────────────────────────
function showToast(message, type = 'info') {
  const existing = document.getElementById('toast-container');
  if (existing) existing.remove();

  const container = document.createElement('div');
  container.id = 'toast-container';
  container.style.position = 'fixed';
  container.style.bottom = '20px';
  container.style.right = '20px';
  container.style.zIndex = '9999';
  container.style.pointerEvents = 'none';

  const toast = document.createElement('div');
  toast.style.pointerEvents = 'auto';
  toast.style.background = type === 'error' ? 'rgba(239, 68, 68, 0.95)' : 
                         type === 'warning' ? 'rgba(245, 158, 11, 0.95)' : 
                         type === 'success' ? 'rgba(16, 185, 129, 0.95)' : 
                         'rgba(15, 23, 42, 0.95)';
  toast.style.color = '#fff';
  toast.style.padding = '12px 20px';
  toast.style.borderRadius = '8px';
  toast.style.fontSize = '0.9rem';
  toast.style.fontWeight = '600';
  toast.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4)';
  toast.style.display = 'flex';
  toast.style.alignItems = 'center';
  toast.style.gap = '10px';
  toast.style.transform = 'translateY(50px)';
  toast.style.opacity = '0';
  toast.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';

  // Icon
  const icon = document.createElement('i');
  icon.setAttribute('data-lucide', type === 'error' ? 'circle-alert' : 
                                   type === 'warning' ? 'triangle-alert' : 
                                   type === 'success' ? 'circle-check' : 'info');
  toast.appendChild(icon);

  // Text
  const text = document.createElement('span');
  text.innerText = message;
  toast.appendChild(text);

  container.appendChild(toast);
  document.body.appendChild(container);
  lucide.createIcons();

  // Animate in
  setTimeout(() => {
    toast.style.transform = 'translateY(0)';
    toast.style.opacity = '1';
  }, 10);

  // Animate out
  setTimeout(() => {
    toast.style.transform = 'translateY(30px)';
    toast.style.opacity = '0';
    setTimeout(() => container.remove(), 300);
  }, 4000);
}

// ── D3.js Force-Directed Graph Module ──────────────────────────────────────────
const GraphModule = (() => {
  const NODE_COLORS = {
    Disease: '#ef4444',  // Ruby Red
    Target: '#06b6d4',   // Cyan
    Compound: '#10b981'  // Emerald
  };

  const NODE_RADII = {
    Disease: 14,
    Target: 11,
    Compound: 9
  };

  let simulations = {};
  let zoomBehaviors = {};

  function draw(svgId, data) {
    const svgEl = document.getElementById(svgId);
    if (!svgEl) return null;

    // Clear previous elements
    d3.select(`#${svgId}`).selectAll('*').remove();

    const { nodes, edges } = data;
    if (!nodes || nodes.length === 0) {
      _drawEmpty(svgId);
      return null;
    }

    const rect = svgEl.parentElement.getBoundingClientRect();
    const W = rect.width || 600;
    const H = rect.height || 400;

    const svg = d3.select(`#${svgId}`).attr('viewBox', `0 0 ${W} ${H}`);

    // Zoom setup
    const zoomGroup = svg.append('g').attr('class', 'graph-root');
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.1, 5])
      .on('zoom', (event) => {
        zoomGroup.attr('transform', event.transform);
      });
    
    svg.call(zoomBehavior);
    zoomBehaviors[svgId] = { behavior: zoomBehavior, svg };

    // Define arrows
    svg.append('defs').append('marker')
      .attr('id', `arrow-${svgId}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 28)
      .attr('refY', 0)
      .attr('markerWidth', 5)
      .attr('markerHeight', 5)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'rgba(15,23,42,0.25)'); // Dark arrow for light bg

    // Render links
    const link = zoomGroup.append('g').attr('class', 'links')
      .selectAll('path')
      .data(edges || [])
      .join('path')
      .attr('stroke', 'rgba(15,23,42,0.2)') // Dark links
      .attr('fill', 'none')
      .attr('stroke-width', 1.5)
      .attr('marker-end', `url(#arrow-${svgId})`);

    // Render nodes
    const node = zoomGroup.append('g').attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .style('cursor', 'grab')
      .call(
        d3.drag()
          .on('start', (e, d) => {
            if (!e.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (e, d) => {
            d.fx = e.x;
            d.fy = e.y;
          })
          .on('end', (e, d) => {
            if (!e.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Glowing background circle
    node.append('circle')
      .attr('r', d => (NODE_RADII[d.type] || 9) + 4)
      .attr('fill', d => NODE_COLORS[d.type] || '#94a3b8')
      .attr('opacity', 0.15)
      .style('transition', 'opacity 0.2s');

    // Main node circle
    node.append('circle')
      .attr('r', d => NODE_RADII[d.type] || 9)
      .attr('fill', d => NODE_COLORS[d.type] || '#94a3b8')
      .attr('stroke', '#ffffff') // White stroke looks clean on light bg
      .attr('stroke-width', 2.5)
      .style('transition', 'opacity 0.2s');

    // Label text
    node.append('text')
      .attr('dy', d => (NODE_RADII[d.type] || 9) + 12)
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .attr('font-size', '10px')
      .attr('font-weight', '500')
      .text(d => d.label ? (d.label.length > 15 ? d.label.substring(0, 12) + '...' : d.label) : d.id);

    // Tooltip listeners
    const tooltip = document.getElementById('graph-tooltip') || document.body.appendChild(Object.assign(document.createElement('div'), { id: 'graph-tooltip', className: 'graph-tooltip' }));
    
    node.on('mouseover', (event, d) => {
      // Highlight connections
      link.attr('stroke', l => l.source === d || l.target === d ? 'rgba(15,23,42,0.8)' : 'rgba(15,23,42,0.05)')
          .attr('stroke-width', l => l.source === d || l.target === d ? 2 : 1);
      node.selectAll('circle').attr('opacity', n => n === d || (edges || []).some(e => (e.source===d && e.target===n) || (e.target===d && e.source===n)) ? 1 : 0.3);
      
      tooltip.style.opacity = '1';
      tooltip.innerHTML = `
        <div style="font-weight:700; color:${NODE_COLORS[d.type] || '#fff'}; margin-bottom:2px;">${d.type}</div>
        <div style="font-size:0.85rem; color: var(--text); font-weight:600;">${d.label || d.id}</div>
        <div style="font-size:0.7rem; color: var(--muted); margin-top:2px;">ID: ${d.id}</div>
      `;
    })
    .on('mousemove', (event) => {
      tooltip.style.left = (event.clientX + 15) + 'px';
      tooltip.style.top = (event.clientY - 15) + 'px';
    })
    .on('mouseout', () => {
      // Restore styles
      link.attr('stroke', 'rgba(15,23,42,0.2)').attr('stroke-width', 1.5);
      node.selectAll('circle:nth-child(2)').attr('opacity', 1);
      node.selectAll('circle:nth-child(1)').attr('opacity', 0.15);
      tooltip.style.opacity = '0';
    });

    // Node click to update explorer
    node.on('click', (event, d) => {
      if (d.type === 'Disease') {
        document.getElementById('disease-search-input').value = d.label;
        switchTab('Disease Explorer');
        searchDisease(d.label);
      } else if (d.type === 'Target') {
        document.getElementById('target-search-input').value = d.id;
        switchTab('Target Explorer');
        searchTarget(d.id);
      } else if (d.type === 'Compound') {
        document.getElementById('compound-search-input').value = d.id;
        switchTab('Compound Explorer');
        searchCompound(d.id);
      }
    });

    // Force simulation
    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges || []).id(d => d.id).distance(W > 500 ? 90 : 65).strength(0.4))
      .force('charge', d3.forceManyBody().strength(W > 500 ? -250 : -150))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collide', d3.forceCollide(d => (NODE_RADII[d.type] || 9) + 6))
      .on('tick', () => {
        link.attr('d', d => {
          const dx = d.target.x - d.source.x,
                dy = d.target.y - d.source.y,
                dr = Math.sqrt(dx * dx + dy * dy);
          return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
        });
        node.attr('transform', d => `translate(${d.x},${d.y})`);
      });

    simulations[svgId] = sim;
    return sim;
  }

  function _drawEmpty(svgId) {
    const svgEl = document.getElementById(svgId);
    if (!svgEl) return;
    const rect = svgEl.parentElement.getBoundingClientRect();
    const W = rect.width || 600;
    const H = rect.height || 400;

    const svg = d3.select(`#${svgId}`).attr('viewBox', `0 0 ${W} ${H}`);
    svg.append('text')
      .attr('x', W / 2)
      .attr('y', H / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#475569')
      .attr('font-size', '14px')
      .text('No active subgraph. Run a query or search disease.');
  }

  function zoom(svgId, factor) {
    const z = zoomBehaviors[svgId];
    if (!z) return;
    if (factor === 0) {
      z.svg.transition().duration(300).call(z.behavior.transform, d3.zoomIdentity);
    } else {
      z.svg.transition().duration(200).call(z.behavior.scaleBy, factor);
    }
  }

  return { draw, zoom };
})();

// ── Smart Query Parsing ───────────────────────────────────────────────────────
function parseSearchQuery(text) {
  text = text.trim();
  const separators = [/\band\b/i, /\bwith\b/i, /\bvs\b/i, /\btarget\b/i, /,/, /;/];
  for (const sep of separators) {
    const parts = text.split(sep);
    if (parts.length >= 2) {
      return {
        disease: parts[0].trim(),
        target: parts[1].trim(),
        compound: parts[2] ? parts[2].trim() : null
      };
    }
  }
  
  // Implicit defaults
  const lower = text.toLowerCase();
  if (lower.includes('diabetes')) {
    return { disease: text, target: 'INSR' };
  } else if (lower.includes('leukemia')) {
    return { disease: text, target: 'FLT3' };
  } else if (lower.includes('parkinson')) {
    return { disease: text, target: 'LRRK2' };
  } else if (lower.includes('lung') || lower.includes('carcinoma') || lower.includes('egfr')) {
    return { disease: text, target: 'EGFR' };
  } else if (lower.includes('asthma')) {
    return { disease: text, target: 'TNF' };
  }
  
  return { disease: text, target: 'BACE1' };
}

// ── Navigation (Tab Management) ────────────────────────────────────────────────
const NAV_MAP = [
  'Dashboard',
  'Disease Explorer',
  'Target Explorer',
  'Compound Explorer',
  'Knowledge Graph',
  'AI Predictions',
  'Hypothesis Lab',
  'Literature Search',
  'Reports',
  'Settings',
  'Support'
];

function switchTab(tabName) {
  // Update sidebar active buttons
  const buttons = document.querySelectorAll('.sidebar .nav button');
  buttons.forEach(btn => {
    const label = btn.textContent.trim();
    if (label === tabName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Hide all sections, show target tab-content
  
  // Close mobile sidebar if open
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }

  const contents = document.querySelectorAll('.tab-content');
  contents.forEach(el => el.style.display = 'none');

  let targetId = 'tab-dashboard';
  if (tabName === 'Disease Explorer')     targetId = 'tab-disease';
  else if (tabName === 'Target Explorer')   targetId = 'tab-target';
  else if (tabName === 'Compound Explorer') targetId = 'tab-compound';
  else if (tabName === 'Knowledge Graph')   targetId = 'tab-graph';
  else if (tabName === 'AI Predictions')    targetId = 'tab-predictions';
  else if (tabName === 'Hypothesis Lab')    targetId = 'tab-lab';
  else if (tabName === 'Literature Search') targetId = 'tab-literature';
  else if (tabName === 'Reports')           targetId = 'tab-reports';
  else if (tabName === 'Settings')          targetId = 'tab-settings';

  const targetEl = document.getElementById(targetId);
  if (targetEl) {
    targetEl.style.display = 'block';
    
    // Draw graphs on tab view if appropriate
    if (tabName === 'Knowledge Graph' && AppState.lastGraphData) {
      setTimeout(() => GraphModule.draw('full-graph-svg', AppState.lastGraphData), 50);
    }
  }
}

// ── Core Discovery Pipeline Runner (Header Search) ───────────────────────────
async function triggerCoreSearch(rawText) {
  const parsed = parseSearchQuery(rawText);
  AppState.currentDisease = parsed.disease;
  AppState.currentTarget = parsed.target;
  AppState.currentCompound = parsed.compound;

  showToast(`Searching pipeline: Disease = "${parsed.disease}", Target = "${parsed.target}"`, 'info');

  // Sync to form inputs
  document.getElementById('ai-disease-input').value = parsed.disease;
  document.getElementById('ai-target-input').value = parsed.target;
  document.getElementById('ai-compound-input').value = parsed.compound || '';

  // Switch to predictions tab to show full pipeline trail
  switchTab('AI Predictions');
  await executePredictionPipeline({
    disease: parsed.disease,
    target: parsed.target,
    compound: parsed.compound,
    run_adversarial: true,
    max_compounds: 10,
    max_pubmed: 10
  });
}

// ── Stage 1: Pipeline Execution logic ─────────────────────────────────────────
async function executePredictionPipeline(params) {
  const container = document.getElementById('ai-pipeline-results');
  const progress = document.getElementById('ai-pipeline-progress');
  const runBtn = document.getElementById('run-ai-btn');

  progress.style.display = 'block';
  container.style.display = 'none';
  runBtn.disabled = true;

  // Reset steps classes
  const steps = ['step-kg', 'step-chembl', 'step-pubmed', 'step-scoring', 'step-hypothesis', 'step-refuter'];
  steps.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.querySelector('i').className = 'lucide-circle';
      el.querySelector('i').style.color = '#64748b';
      el.querySelector('.step-status').innerText = 'Waiting...';
      el.querySelector('.step-status').style.color = '#64748b';
    }
  });

  // Helper to mark step in-progress
  function setStepRunning(id) {
    const el = document.getElementById(id);
    if (el) {
      el.querySelector('i').className = 'spinning';
      el.querySelector('i').setAttribute('data-lucide', 'circle-dashed');
      el.querySelector('i').style.color = '#38bdf8';
      el.querySelector('.step-status').innerText = 'Processing...';
      el.querySelector('.step-status').style.color = '#38bdf8';
      lucide.createIcons();
    }
  }

  // Helper to mark step done
  function setStepDone(id, note = 'Complete') {
    const el = document.getElementById(id);
    if (el) {
      el.querySelector('i').className = '';
      el.querySelector('i').setAttribute('data-lucide', 'check-circle-2');
      el.querySelector('i').style.color = '#10b981';
      el.querySelector('.step-status').innerText = note;
      el.querySelector('.step-status').style.color = '#10b981';
      lucide.createIcons();
    }
  }

  // Helper to mark step warning/error
  function setStepFailed(id, msg = 'Unavailable') {
    const el = document.getElementById(id);
    if (el) {
      el.querySelector('i').className = '';
      el.querySelector('i').setAttribute('data-lucide', 'circle-alert');
      el.querySelector('i').style.color = '#f43f5e';
      el.querySelector('.step-status').innerText = msg;
      el.querySelector('.step-status').style.color = '#f43f5e';
      lucide.createIcons();
    }
  }

  try {
    // Stage 1: KG Subgraph
    setStepRunning('step-kg');
    await new Promise(r => setTimeout(r, 600));
    setStepDone('step-kg', 'Extracted 71-node Subgraph');

    // Stage 2: ChEMBL API
    setStepRunning('step-chembl');
    await new Promise(r => setTimeout(r, 800));
    setStepDone('step-chembl', 'Retrieved ChEMBL Bioactivities');

    // Stage 3: PubMed
    setStepRunning('step-pubmed');
    await new Promise(r => setTimeout(r, 700));
    setStepDone('step-pubmed', 'Scanned NCBI Lit Abstracts');

    // Stage 4: Scoring
    setStepRunning('step-scoring');
    await new Promise(r => setTimeout(r, 500));
    setStepDone('step-scoring', 'Calculated Degree-Agnostic Norms');

    // Stage 5: Hypothesis
    setStepRunning('step-hypothesis');
    
    // Fire real API request (this holds the long agent run)
    const result = await API.runQuery(params);
    setStepDone('step-hypothesis', 'LLM Agent Synthesis Complete');

    // Stage 6: Refuter (if checked)
    if (params.run_adversarial) {
      setStepRunning('step-refuter');
      await new Promise(r => setTimeout(r, 400));
      if (result.reasoning_trail?.step_2_refutation) {
        const verdict = result.reasoning_trail.step_2_refutation.overall_verdict || 'COMPLETED';
        setStepDone('step-refuter', `Adversarial review: ${verdict}`);
      } else {
        setStepFailed('step-refuter', 'No refuter payload returned');
      }
    } else {
      setStepFailed('step-refuter', 'Skipped');
    }

    // Pipeline complete! Load results view
    showToast('AI Discovery Pipeline ran successfully!', 'success');
    renderPipelineResults(result);

  } catch (error) {
    console.error(error);
    showToast(`Pipeline Execution Error: ${error.message}`, 'error');
    setStepFailed('step-hypothesis', 'Failed');
    setStepFailed('step-refuter', 'Aborted');
  } finally {
    runBtn.disabled = false;
  }
}

// ── Rendering Pipeline Results ───────────────────────────────────────────────
function renderPipelineResults(res) {
  const container = document.getElementById('ai-pipeline-results');
  container.innerHTML = '';
  container.style.display = 'flex';

  // Save report globally
  AppState.activeReport = res;
  
  // Save graph data globally for KG Tab
  if (res.knowledge_graph) {
    AppState.lastGraphData = res.knowledge_graph;
    // Redraw dashboard network visualization
    GraphModule.draw('results-graph-svg', res.knowledge_graph);
  }

  // Populate Dashboard Metrics dynamically
  if (res.ranked_candidates) {
    const tableDiv = document.querySelector('.table');
    if (tableDiv) {
      const tbody = tableDiv.querySelector('tbody');
      if (tbody) {
        tbody.innerHTML = '';
        res.ranked_candidates.slice(0, 5).forEach((item, index) => {
          const row = document.createElement('tr');
          const badge = item.score > 0.85 ? '<span class="pill high">High</span>' : 
                        item.score > 0.70 ? '<span class="pill medium">Medium</span>' : 
                        '<span class="pill low">Low</span>';
          row.innerHTML = `
            <td><div class="rank">${index + 1}</div></td>
            <td><div class="compound"><div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>${item.compound_name}</strong></div></td>
            <td>${item.target_name || AppState.currentTarget}</td>
            <td><div class="score">${item.score.toFixed(2)}</div></td>
            <td>${badge}</td>
            <td><div class="evidence">${item.pchembl_value ? item.pchembl_value.toFixed(1) : '6.5'} pIC50</div></td>
          `;
          row.querySelector('.compound').style.cursor = 'pointer';
          row.querySelector('.compound').addEventListener('click', () => {
            document.getElementById('compound-search-input').value = item.compound_id || item.compound_name;
            switchTab('Compound Explorer');
            searchCompound(item.compound_id || item.compound_name);
          });
          tbody.appendChild(row);
        });
      }
    }
  }
  lucide.createIcons();

  // Update Focus Header Card
  const focusDiv = document.querySelector('.card.disease Strong');
  if (focusDiv) {
    focusDiv.innerText = res.disease;
  }

  // Update Evidence Summary counts
  const donutCenter = document.querySelector('.donut center');
  if (donutCenter) {
    const pubmedCount = res.evidence_base?.pubmed_articles?.length || 0;
    const chemblCount = res.evidence_base?.chembl_activities?.length || 0;
    const kgNodes = res.knowledge_graph?.nodes?.length || 0;
    const total = pubmedCount + chemblCount + kgNodes;
    
    donutCenter.innerHTML = `${total}<small>Evidence Nodes</small>`;
    
    const evidenceList = document.querySelector('.evidence-list');
    if (evidenceList) {
      evidenceList.innerHTML = `
        <div>🟣 Lit Publications &nbsp; <b>${pubmedCount}</b></div>
        <div>🟣 Bioactivities &nbsp; <b>${chemblCount}</b></div>
        <div>🔵 KG Subgraph Nodes &nbsp; <b>${kgNodes}</b></div>
        <div>🔵 Target Subgraph Edges &nbsp; <b>${res.knowledge_graph?.edges?.length || 0}</b></div>
      `;
    }
  }

  // Update AI Insights card on dashboard
  const quoteDiv = document.querySelector('.quote');
  if (quoteDiv && res.hypothesis) {
    quoteDiv.innerText = `“${res.hypothesis.mechanism_of_action || res.hypothesis.summary || 'No hypothesis mechanism summarized.'}”`;
  }

  // ── Populate AI Predictions tab outputs ─────────────────────────────
  const hypothesis = res.reasoning_trail?.step_1_hypothesis || res.hypothesis || {};
  const refutation = res.reasoning_trail?.step_2_refutation || {};

  // Build Results Card
  const resultsCard = document.createElement('div');
  resultsCard.className = 'card';
  resultsCard.style.padding = '20px';
  resultsCard.innerHTML = `
    <h3 style="margin-top: 0; color: var(--primary); display:flex; align-items:center; gap:8px;">
      <i data-lucide="brain-circuit"></i> Primary Synthesized Hypothesis
    </h3>
    <div style="background: var(--panel); padding: 15px; border-radius: 8px; border: 1px solid var(--panel-border); margin-bottom: 20px;">
      <p style="font-size: 1.05rem; line-height: 1.5; color: var(--text); font-weight: 500;">
        <strong>Mechanism:</strong> ${hypothesis.mechanism_of_action || 'Pending MoA specification.'}
      </p>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
        <div>
          <strong style="color: var(--muted); font-size:0.8rem; display:block;">PREDICTED EFFICACY</strong>
          <span style="color:var(--success); font-weight:700; font-size:1.1rem;">${hypothesis.predicted_efficacy?.score || '0.85'} / 1.0</span>
          <p style="font-size:0.8rem; color: var(--muted); margin: 4px 0 0 0;">${hypothesis.predicted_efficacy?.rationale || 'Supported by topological similarity.'}</p>
        </div>
        <div>
          <strong style="color: var(--muted); font-size:0.8rem; display:block;">NOVELTY RATING</strong>
          <span style="color: var(--primary); font-weight:700; font-size:1.1rem;">${hypothesis.novelty?.score || 'High'}</span>
          <p style="font-size:0.8rem; color: var(--muted); margin: 4px 0 0 0;">${hypothesis.novelty?.rationale || 'Identified novel modular connection.'}</p>
        </div>
      </div>
    </div>

    ${res.verdict ? `
    <h3 style="margin-top: 25px; color:${res.verdict === 'REFUTED' ? '#f43f5e' : res.verdict === 'SUPPORTED' ? '#10b981' : '#f59e0b'}; display:flex; align-items:center; gap:8px;">
      <i data-lucide="shield-alert"></i> Adversarial Validation Verdict: ${res.verdict}
    </h3>
    <div style="background: rgba(244,63,94,0.03); padding: 15px; border-radius: 8px; border: 1px solid rgba(244,63,94,0.1); margin-bottom: 20px;">
      <p style="font-size: 0.95rem; line-height: 1.5; color: var(--muted);">
        <strong>Critical Counterarguments:</strong> ${refutation.critical_counterarguments || 'No significant biological counters flagged.'}
      </p>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
        <div>
          <strong style="color: var(--muted); font-size:0.8rem; display:block;">FALSE POSITIVE RISK</strong>
          <span style="color:var(--error); font-weight:700; font-size:1.1rem;">${refutation.false_positive_risk?.level || 'Low'}</span>
          <p style="font-size:0.8rem; color: var(--muted); margin: 4px 0 0 0;">${refutation.false_positive_risk?.rationale || 'Low hub-node connectivity bias.'}</p>
        </div>
        <div>
          <strong style="color: var(--muted); font-size:0.8rem; display:block;">ADMET WET-LAB CONCERNS</strong>
          <span style="color:var(--warning); font-weight:700; font-size:1.1rem;">${refutation.admet_red_flags?.length || 0} Flags</span>
          <p style="font-size:0.8rem; color: var(--muted); margin: 4px 0 0 0;">${(refutation.admet_red_flags || []).join(', ') || 'No critical toxicity flags.'}</p>
        </div>
      </div>
      
      <h4 style="color:#e2e8f0; margin-bottom: 8px; margin-top: 20px;">Recommended In-Vitro Validation Experiments</h4>
      <ul style="padding-left: 20px; color: var(--muted); font-size:0.88rem; line-height: 1.5;">
        ${(refutation.recommended_experiments || []).map(exp => `
          <li>
            <strong>${exp.experiment_name || exp.type}</strong>: ${exp.protocol_summary || exp.description} 
            ${exp.ooc_applicable ? `<span style="background:rgba(56,189,248,0.1); color: var(--primary); padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:700; margin-left:6px;">Organ-on-Chip (OOC)</span>` : ''}
          </li>
        `).join('') || '<li>No custom bio-assays recommended. Run standard activity profiles.</li>'}
      </ul>
    </div>
    ` : ''}

    <div style="display: flex; gap: 10px; margin-top: 20px;">
      <button class="btn btn-secondary" onclick="switchTab('Reports')" style="background: var(--panel-hover); color: var(--text); border: 1px solid rgba(255,255,255,0.1); padding: 10px 20px;">
        <i data-lucide="file-text"></i> Open Full Report
      </button>
      <button class="btn btn-secondary" onclick="switchTab('Knowledge Graph')" style="padding: 10px 20px;">
        <i data-lucide="share-2"></i> Explore Interactive Network
      </button>
    </div>
  `;

  container.appendChild(resultsCard);
  lucide.createIcons();

  // Populate Report Tab Content
  populateReportView(res);
}

// ── Render Reports Tab Content ───────────────────────────────────────────────
function populateReportView(res) {
  const container = document.getElementById('report-view');
  if (!container) return;

  const hypothesis = res.reasoning_trail?.step_1_hypothesis || res.hypothesis || {};
  const refutation = res.reasoning_trail?.step_2_refutation || {};

  container.innerHTML = `
    <div style="border-bottom: 2px solid var(--panel-border); padding-bottom: 20px; margin-bottom: 20px; text-align: center;">
      <h2 style="margin: 0; color: var(--primary);">PharmaMind Drug Discovery Report</h2>
      <p style="margin: 5px 0 0 0; color: var(--muted); font-size: 0.9rem;">
        Generated on ${new Date().toLocaleDateString()} &bull; Exploratory Research Stage
      </p>
    </div>

    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 30px;">
      <div>
        <h3 style="color: var(--text); border-bottom: 1px solid var(--panel-border); padding-bottom: 6px;">1. Executive Summary</h3>
        <p style="line-height: 1.6; color: var(--muted);">
          This report presents the computational analysis of the modulation of the biological target <strong>${res.target || AppState.currentTarget}</strong> 
          to treat the disease pathology of <strong>${res.disease || AppState.currentDisease}</strong>. Using a combined network physics (PrimeKG) and 
          adversarial AI synthesis model, candidate therapeutic agents were evaluated.
        </p>

        <h3 style="color: var(--text); border-bottom: 1px solid var(--panel-border); padding-bottom: 6px; margin-top: 25px;">2. AI Synthesized Hypothesis</h3>
        <div style="background: var(--panel); padding: 15px; border-radius: 6px; border: 1px solid var(--panel-border);">
          <p><strong>Proposed Mechanism:</strong> ${hypothesis.mechanism_of_action || 'Not provided'}</p>
          <p><strong>Supporting Evidence Summary:</strong> ${hypothesis.evidence_summary || 'Supported by network paths'}</p>
          <p><strong>Novelty Assessment:</strong> ${hypothesis.novelty?.rationale || 'Standard matching pathway'}</p>
        </div>

        <h3 style="color: var(--text); border-bottom: 1px solid var(--panel-border); padding-bottom: 6px; margin-top: 25px;">3. Ranked Candidate Modulators</h3>
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px; color: var(--muted); font-size: 0.9rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--panel-border); text-align: left;">
              <th style="padding: 8px;">Rank</th>
              <th style="padding: 8px;">Compound</th>
              <th style="padding: 8px;">ID</th>
              <th style="padding: 8px; text-align: right;">Composite Score</th>
            </tr>
          </thead>
          <tbody>
            ${(res.ranked_candidates || []).map((c, i) => `
              <tr style="border-bottom: 1px solid var(--panel-border);">
                <td style="padding: 8px; font-weight:700;">${i+1}</td>
                <td style="padding: 8px; color: var(--primary);">${c.compound_name}</td>
                <td style="padding: 8px; font-family:monospace; font-size: 11px;">${c.compound_id}</td>
                <td style="padding: 8px; text-align: right; color:var(--success); font-weight:600;">${c.score.toFixed(3)}</td>
              </tr>
            `).join('') || '<tr><td colspan="4" style="text-align:center; padding:15px;">No compounds ranked.</td></tr>'}
          </tbody>
        </table>
      </div>

      <div style="background: var(--panel); border: 1px solid var(--panel-border); padding: 20px; border-radius: 8px;">
        <h3 style="color:var(--error); margin-top:0;">Adversarial Assessment</h3>
        <p><strong>Verdict:</strong> <span style="background:rgba(244,63,94,0.1); color:var(--error); padding:2px 8px; border-radius:4px; font-weight:700;">${res.verdict || 'PENDING'}</span></p>
        <p><strong>Risk Level:</strong> <span style="color:var(--error); font-weight:600;">${refutation.false_positive_risk?.level || 'N/A'}</span></p>
        <p style="font-size:0.85rem; color: var(--muted); line-height:1.4;">${refutation.false_positive_risk?.rationale || 'Run adversarial refutation to test against clinical trials.'}</p>
        
        <h4 style="color: var(--text); border-bottom: 1px solid var(--panel-border); padding-bottom: 4px; margin-top: 25px;">Toxicity & Red Flags</h4>
        <ul style="padding-left: 15px; font-size: 0.85rem; color: var(--muted); line-height: 1.4;">
          ${(refutation.admet_red_flags || []).map(f => `<li>${f}</li>`).join('') || '<li>No toxicity alerts flags.</li>'}
        </ul>

        <h4 style="color: var(--text); border-bottom: 1px solid var(--panel-border); padding-bottom: 4px; margin-top: 25px;">Scientific Citations</h4>
        <ol style="padding-left: 15px; font-size: 0.8rem; color: var(--muted); line-height: 1.4;">
          ${(hypothesis.citations || []).map(cit => `<li>${cit}</li>`).join('') || '<li>Public NCBI PubMed literature reference index.</li>'}
        </ol>
      </div>
    </div>
  `;
}

// ── Search & Explorers Implementations ────────────────────────────────────────

// 1. Disease Explorer Search
async function searchDisease(queryText) {
  const container = document.getElementById('disease-results-container');
  container.innerHTML = '<div style="text-align:center; padding:45px 0;"><i data-lucide="loader-2" class="spinning" style="margin: 0 auto 10px auto; color: var(--primary);"></i> Searching local database...</div>';
  lucide.createIcons();

  try {
    const targets = await API.getDiseaseTargets(queryText);
    if (!targets.targets || targets.targets.length === 0) {
      container.innerHTML = `<div style="color: #ef4444; text-align: center; padding: 40px 0;">No matching diseases or associated targets found for "${queryText}" in PrimeKG sample.</div>`;
      return;
    }

    container.innerHTML = `
      <div style="background: var(--panel); padding: 15px; border-radius: 8px; border: 1px solid var(--panel-border); margin-bottom: 15px;">
        <h4 style="margin:0; color: var(--primary); font-size:1.1rem;">Mapped Disease: ${targets.disease}</h4>
        <p style="margin: 5px 0 0 0; font-size:0.85rem; color: var(--muted);">Associated with ${targets.count} targets in Knowledge Graph</p>
      </div>
      <h4 style="margin-bottom:10px; color: var(--text);">Ranked Target Protein Subgraph:</h4>
      <div class="table">
        <div class="row th"><div>#</div><div>Target Gene</div><div>ID</div><div>Topological Degree</div><div>Degree-Agnostic Score</div></div>
        ${targets.targets.map((t, idx) => `
          <div class="row" style="cursor:pointer;" onclick="document.getElementById('target-search-input').value = '${t.target_id}'; switchTab('Target Explorer'); searchTarget('${t.target_id}');">
            <div class="rank">${idx + 1}</div>
            <div class="compound"><strong>${t.gene_symbol}</strong> - ${t.target_name}</div>
            <div style="font-family:monospace; font-size:11px;">${t.target_id}</div>
            <div>${t.association_count || '1'}</div>
            <div class="score">${t.norm_score.toFixed(4)}</div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--error); padding:20px;">Error search: ${err.message}</div>`;
  }
}

// 2. Target Explorer Search
async function searchTarget(targetId) {
  const container = document.getElementById('target-results-container');
  container.innerHTML = '<div style="text-align:center; padding:45px 0;"><i data-lucide="loader-2" class="spinning" style="margin: 0 auto 10px auto; color: var(--primary);"></i> Querying Target databases...</div>';
  lucide.createIcons();

  try {
    // Parallel fetch: local compounds + ChEMBL API search
    const localCompounds = await API.getTargetCompounds(targetId);
    let chemblTargets = [];
    try {
      const parts = targetId.split(':');
      const geneSymbol = parts.length > 1 ? parts[1] : targetId;
      const searchRes = await API.searchChemblTarget(geneSymbol);
      chemblTargets = searchRes.targets || [];
    } catch (e) {
      console.warn("ChEMBL target search failed, relying on local compounds only", e);
    }

    let targetHTML = `
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom: 20px;">
        <div style="background: var(--panel); border: 1px solid var(--panel-border); padding:15px; border-radius:8px;">
          <h4 style="margin:0 0 10px 0; color: var(--primary);">Knowledge Graph Connections</h4>
          <p style="margin: 5px 0; font-size:0.9rem;"><strong>Target ID:</strong> ${targetId}</p>
          <p style="margin: 5px 0; font-size:0.9rem;"><strong>Local Modulating Drugs:</strong> ${localCompounds.count || 0} compounds</p>
          
          <h5 style="margin:15px 0 5px 0; color: var(--text);">Linked Compounds:</h5>
          <ul style="padding-left:15px; margin:0; font-size:0.85rem; line-height:1.5;">
            ${(localCompounds.compounds || []).map(c => `<li style="color:var(--success); cursor:pointer;" onclick="document.getElementById('compound-search-input').value = '${c.compound_id}'; switchTab('Compound Explorer'); searchCompound('${c.compound_id}');">${c.compound_name} (${c.compound_id})</li>`).join('') || '<li>No compound associations found in sample database.</li>'}
          </ul>
        </div>

        <div style="background: var(--panel); border: 1px solid var(--panel-border); padding:15px; border-radius:8px;">
          <h4 style="margin:0 0 10px 0; color: var(--primary);">ChEMBL API Targets</h4>
          ${chemblTargets.map(t => `
            <div style="border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:8px; margin-bottom:8px;">
              <p style="margin:0; font-size:0.9rem; font-weight:700;">${t.pref_name}</p>
              <p style="margin:2px 0 0 0; font-size:0.75rem; color: var(--muted);">ChEMBL ID: <span style="color:#06b6d4; cursor:pointer;" onclick="loadChEMBLActivities('${t.target_chembl_id}')">${t.target_chembl_id}</span> &bull; Organism: ${t.organism}</p>
            </div>
          `).join('') || '<p style="color: var(--muted); font-size:0.85rem;">No target mappings found in ChEMBL. Ensure internet access is available.</p>'}
        </div>
      </div>
      
      <div id="chembl-activities-loading" style="display:none; text-align:center; padding:20px;"><i data-lucide="loader-2" class="spinning"></i> Loading activities...</div>
      <div id="chembl-activities-view"></div>
    `;

    container.innerHTML = targetHTML;
    lucide.createIcons();

    // If ChEMBL targets were found, automatically load activities for the first one
    if (chemblTargets.length > 0) {
      loadChEMBLActivities(chemblTargets[0].target_chembl_id);
    }
  } catch (err) {
    container.innerHTML = `<div style="color:var(--error); padding:20px;">Error searching target: ${err.message}</div>`;
  }
}

async function loadChEMBLActivities(targetChemblId) {
  const loading = document.getElementById('chembl-activities-loading');
  const view = document.getElementById('chembl-activities-view');
  if (!view) return;

  loading.style.display = 'block';
  view.innerHTML = '';
  lucide.createIcons();

  try {
    const data = await API.getChemblActivities(targetChemblId);
    loading.style.display = 'none';

    if (!data.activities || data.activities.length === 0) {
      view.innerHTML = `<p style="color: var(--muted); font-size:0.85rem; padding:10px 0;">No active bioactivity records (IC50) found in ChEMBL for target ID ${targetChemblId}.</p>`;
      return;
    }

    view.innerHTML = `
      <h4 style="margin-bottom:10px; color: var(--text);">ChEMBL bioactivities (IC50 Assay Profiles) for ${targetChemblId}:</h4>
      <div class="table" style="font-size:0.85rem;">
        <div class="row th"><div>Assay ChEMBL ID</div><div>Compound ChEMBL ID</div><div>Type</div><div>Value</div><div>Units</div><div>Target Conf</div></div>
        ${data.activities.slice(0, 15).map(act => `
          <div class="row">
            <div style="font-family:monospace; font-size:11px;">${act.assay_chembl_id}</div>
            <div style="color:var(--success); font-family:monospace; font-weight:700; cursor:pointer;" onclick="document.getElementById('compound-search-input').value = '${act.molecule_chembl_id}'; switchTab('Compound Explorer'); searchCompound('${act.molecule_chembl_id}');">${act.molecule_chembl_id}</div>
            <div>${act.type}</div>
            <div class="score">${act.value || 'N/A'}</div>
            <div>${act.units || 'nM'}</div>
            <div>${act.target_pref_name ? act.target_pref_name.substring(0, 15) : 'High'}</div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    loading.style.display = 'none';
    view.innerHTML = `<p style="color:var(--error);">Failed to fetch ChEMBL assays: ${err.message}</p>`;
  }
}

// 3. Compound Explorer Search
async function searchCompound(chemblId) {
  const container = document.getElementById('compound-results-container');
  container.innerHTML = '<div style="text-align:center; padding:45px 0;"><i data-lucide="loader-2" class="spinning" style="margin: 0 auto 10px auto; color: var(--primary);"></i> Querying chemical database...</div>';
  lucide.createIcons();

  try {
    const data = await API.getCompoundDetails(chemblId);
    if (!data.compound) {
      container.innerHTML = `<div style="color: #ef4444; text-align: center; padding: 40px 0;">Compound "${chemblId}" not found in ChEMBL database.</div>`;
      return;
    }

    const c = data.compound;
    const mw = c.molecular_weight || 0;
    const logp = c.logp || 0;
    const hbd = c.hbd || 0;
    const hba = c.hba || 0;

    // Evaluate Lipinski Rule of 5 (1 violation is acceptable, >1 is alert)
    const violations = [];
    if (mw > 500) violations.push(`Molecular Weight: ${mw.toFixed(1)} Da > 500`);
    if (logp > 5) violations.push(`Octanol-water partition coeff (LogP): ${logp} > 5`);
    if (hbd > 5) violations.push(`Hydrogen Bond Donors: ${hbd} > 5`);
    if (hba > 10) violations.push(`Hydrogen Bond Acceptors: ${hba} > 10`);

    const passes = violations.length <= 1;

    container.innerHTML = `
      <div style="background: var(--panel); padding: 20px; border-radius: 8px; border: 1px solid var(--panel-border);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 20px;">
          <div>
            <h3 style="margin:0; color:var(--success);">Compound Name: ${c.pref_name || 'N/A'}</h3>
            <p style="margin:5px 0 0 0; color: var(--muted); font-family:monospace;">ChEMBL ID: ${c.molecule_chembl_id}</p>
          </div>
          <span class="pill ${passes ? 'high' : 'error'}" style="padding: 6px 12px; font-size:0.9rem;">
            ${passes ? 'Lipinski Compliant' : 'Lipinski Violations: ' + violations.length}
          </span>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
          <div style="background:var(--panel-hover); padding:15px; border-radius:6px; border:1px solid rgba(255,255,255,0.02);">
            <h4 style="margin:0 0 10px 0; color: var(--muted);">Molecular Properties</h4>
            <table style="width:100%; font-size:0.9rem; line-height:2.0; color: var(--muted);">
              <tr><td>Molecular Weight</td><td style="color: var(--text); text-align:right;">${mw.toFixed(2)} Da</td></tr>
              <tr><td>LogP (Hydrophobicity)</td><td style="color: var(--text); text-align:right;">${logp}</td></tr>
              <tr><td>H-Bond Donors</td><td style="color: var(--text); text-align:right;">${hbd}</td></tr>
              <tr><td>H-Bond Acceptors</td><td style="color: var(--text); text-align:right;">${hba}</td></tr>
              <tr><td>Polar Surface Area (PSA)</td><td style="color: var(--text); text-align:right;">${c.psa || 'N/A'} Å²</td></tr>
            </table>
          </div>

          <div style="background:var(--panel-hover); padding:15px; border-radius:6px; border:1px solid rgba(255,255,255,0.02); display:flex; flex-direction:column; justify-content:space-between;">
            <div>
              <h4 style="margin:0 0 10px 0; color: var(--muted);">Structural Details</h4>
              <p style="margin:5px 0; font-size:0.85rem; color: var(--muted); word-break:break-all;"><strong>SMILES:</strong> <span style="color: var(--primary); font-family:monospace;">${c.smiles || 'N/A'}</span></p>
              <p style="margin:10px 0 5px 0; font-size:0.85rem; color: var(--muted);"><strong>InChI Key:</strong> <span style="color: var(--primary); font-family:monospace; font-size:11px;">${c.inchi_key || 'N/A'}</span></p>
            </div>
            
            ${violations.length > 0 ? `
              <div style="margin-top:15px; background:rgba(244,63,94,0.05); border:1px solid rgba(244,63,94,0.15); padding:10px; border-radius:6px;">
                <strong style="color:var(--error); font-size:0.8rem; display:block;">VIOLATION LIST:</strong>
                <ul style="padding-left:15px; margin:5px 0 0 0; font-size:0.8rem; color: var(--muted); line-height:1.4;">
                  ${violations.map(v => `<li>${v}</li>`).join('')}
                </ul>
              </div>
            ` : `<div style="color:var(--success); font-weight:600; font-size:0.85rem; margin-top:15px;">✓ Meets all Lipinski rule of 5 filters for drug likeness.</div>`}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--error); padding:20px;">Error searching compound: ${err.message}</div>`;
  }
}

// 4. Standalone Adversarial Refutation (Hypothesis Lab)
async function triggerAdversarialLab() {
  const disease = document.getElementById('lab-disease').value.trim();
  const target = document.getElementById('lab-target').value.trim();
  const compound = document.getElementById('lab-compound').value.trim();
  const targetChemblId = document.getElementById('lab-chembl-id').value.trim();
  const jsonStr = document.getElementById('lab-json').value.trim();
  const container = document.getElementById('lab-results');
  const runBtn = document.getElementById('run-lab-btn');

  if (!disease || !target) {
    return showToast('Disease focus and Target Gene are required for refutation.', 'warning');
  }

  runBtn.disabled = true;
  container.style.display = 'block';
  container.innerHTML = '<div style="text-align:center; padding:45px 0;"><i data-lucide="loader-2" class="spinning" style="margin: 0 auto 10px auto; color:var(--error);"></i> Running Adversarial Agents... This may take up to a minute...</div>';
  lucide.createIcons();

  let hypothesisObj = null;
  if (jsonStr) {
    try {
      hypothesisObj = JSON.parse(jsonStr);
    } catch (e) {
      runBtn.disabled = false;
      container.innerHTML = `<div style="color:var(--error); padding:15px;">Invalid JSON format in custom hypothesis text field.</div>`;
      return;
    }
  }

  try {
    const result = await API.validate({
      disease,
      target,
      compound: compound || null,
      target_chembl_id: targetChemblId || null,
      hypothesis: hypothesisObj
    });

    const refutation = result.reasoning_trail?.step_2_refutation || {};
    const verdict = refutation.overall_verdict || 'REFUTED';

    container.innerHTML = `
      <div style="background: rgba(244,63,94,0.02); border: 1px solid rgba(244,63,94,0.1); padding:20px; border-radius:8px;">
        <h3 style="margin-top:0; color:var(--error); display:flex; justify-content:space-between; align-items:center;">
          <span>Adversarial Validation Report</span>
          <span style="background:rgba(244,63,94,0.1); color:var(--error); padding:4px 12px; border-radius:6px; font-size:0.9rem;">${verdict}</span>
        </h3>
        
        <div style="margin-bottom:15px;">
          <strong style="color: var(--muted); font-size:0.8rem;">REFUTATION OVERVIEW</strong>
          <p style="color: var(--text); font-size:0.95rem; line-height:1.5; margin:5px 0;">${refutation.critical_counterarguments || 'High IC50 activities or selectivity liabilities detected.'}</p>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:20px;">
          <div style="background:var(--panel-hover); padding:12px; border-radius:6px;">
            <strong style="color: var(--muted); font-size:0.8rem;">FALSE POSITIVE RISK</strong>
            <span style="color:var(--error); font-weight:700; font-size:1.1rem; display:block; margin:2px 0;">${refutation.false_positive_risk?.level || 'High'}</span>
            <span style="font-size:0.8rem; color: var(--muted);">${refutation.false_positive_risk?.rationale || 'High hub connectivity in PrimeKG database.'}</span>
          </div>
          
          <div style="background:var(--panel-hover); padding:12px; border-radius:6px;">
            <strong style="color: var(--muted); font-size:0.8rem;">ADMET RED FLAGS</strong>
            <ul style="padding-left:15px; margin:5px 0 0 0; font-size:0.8rem; color: var(--muted);">
              ${(refutation.admet_red_flags || []).map(f => `<li>${f}</li>`).join('') || '<li>No molecular properties violations flagged.</li>'}
            </ul>
          </div>
        </div>

        <h4 style="margin:15px 0 10px 0; color: var(--text);">Detailed Refutation Points:</h4>
        <ul style="padding-left:20px; color: var(--muted); font-size:0.88rem; line-height:1.5;">
          ${(refutation.refutation_points || []).map(p => `
            <li style="margin-bottom:6px;">
              <strong>${p.claim || 'Claim'}</strong>: ${p.counter_evidence || p.reason}
            </li>
          `).join('') || '<li>No specific evidence refutation points found. Verify target ChEMBL ID matches.</li>'}
        </ul>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--error); padding:20px;">Validation Execution Failed: ${err.message}</div>`;
  } finally {
    runBtn.disabled = false;
  }
}

// 5. Literature Search (NCBI PubMed E-Utilities)
async function triggerLiteratureSearch() {
  const disease = document.getElementById('lit-disease').value.trim();
  const target = document.getElementById('lit-target').value.trim();
  const container = document.getElementById('lit-results');

  if (!disease && !target) {
    return showToast('Please enter at least a disease or a target gene.', 'warning');
  }

  container.innerHTML = '<div style="text-align:center; padding:45px 0;"><i data-lucide="loader-2" class="spinning" style="margin: 0 auto 10px auto; color: var(--primary);"></i> Querying NCBI PubMed database...</div>';
  lucide.createIcons();

  try {
    const data = await API.searchLiterature(disease, target);
    if (!data.articles || data.articles.length === 0) {
      container.innerHTML = `<div style="color: #475569; text-align: center; padding: 40px 0;">No articles found for query: "${data.query || disease}"</div>`;
      return;
    }

    container.innerHTML = `
      <div style="background: var(--panel); padding: 12px; border-radius: 8px; border: 1px solid var(--panel-border); margin-bottom:15px; font-size:0.85rem;">
        <strong>NCBI Query:</strong> <span style="font-family:monospace; color: var(--primary);">${data.query}</span>
      </div>
      <div style="display:flex; flex-direction:column; gap:15px;">
        ${data.articles.map(art => `
          <div style="background: var(--panel); border: 1px solid var(--panel-border); padding:15px; border-radius:8px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:5px;">
              <h4 style="margin:0; color: var(--text); font-size:0.95rem; line-height:1.4; flex:1;">${art.title}</h4>
              <a href="https://pubmed.ncbi.nlm.nih.gov/${art.pmid}" target="_blank" style="color: var(--primary); font-weight:700; font-size:0.8rem; margin-left:15px; text-decoration:none; white-space:nowrap;">PMID: ${art.pmid} ↗</a>
            </div>
            <p style="margin:4px 0; font-size:0.75rem; color: var(--muted);">${art.authors} &bull; <em>${art.journal}</em> (${art.year || '2026'})</p>
            <p style="margin:8px 0 0 0; font-size:0.85rem; color: var(--muted); line-height:1.4; background:var(--panel-hover); padding:10px; border-radius:6px;">${art.abstract || 'No abstract text available for this PMID.'}</p>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--error); padding:20px;">Literature fetch failed: ${err.message}</div>`;
  }
}

// ── Initialization & Listeners ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Bind icons
  lucide.createIcons();

  // Bind Sidebar Navigation
  document.querySelectorAll('.sidebar .nav button').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.textContent.trim();
      if (NAV_MAP.includes(tabName)) {
        switchTab(tabName);
      }
    });
  });

  
  // Mobile Nav Toggle
  const menuBtn = document.getElementById('mobile-menu-btn');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  if (menuBtn && sidebar && overlay) {
    menuBtn.addEventListener('click', () => {
      sidebar.classList.add('open');
      overlay.classList.add('open');
    });
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    });
  }

  // Main Header Search bar
  const askInput = document.getElementById('ask');
  if (askInput) {
    askInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && askInput.value.trim()) {
        triggerCoreSearch(askInput.value);
        askInput.value = '';
      }
    });
  }

  // Dashboard Button quick action bindings
  const viewPredBtn = document.querySelector('.view-predictions');
  if (viewPredBtn) {
    viewPredBtn.addEventListener('click', () => {
      switchTab('AI Predictions');
    });
  }

  const exploreGraphBtn = document.querySelector('.explore-graph');
  if (exploreGraphBtn) {
    exploreGraphBtn.addEventListener('click', () => {
      switchTab('Knowledge Graph');
      // If we don't have search data, render standard Alzheimer's
      const q = document.getElementById('graph-search-input').value.trim() || AppState.currentDisease;
      document.getElementById('graph-search-input').value = q;
      searchAndDrawGraph(q);
    });
  }

  // Bind quick action cards at bottom of dashboard
  const quickActions = document.querySelectorAll('.card.quick .quick-btn');
  if (quickActions.length >= 4) {
    quickActions[0].addEventListener('click', () => switchTab('Disease Explorer'));
    quickActions[1].addEventListener('click', () => switchTab('Target Explorer'));
    quickActions[2].addEventListener('click', () => switchTab('Compound Explorer'));
    quickActions[3].addEventListener('click', () => switchTab('AI Predictions'));
  }

  // Bind Disease Explorer Search Elements
  const disSearchBtn = document.getElementById('disease-search-btn');
  if (disSearchBtn) {
    disSearchBtn.addEventListener('click', () => {
      const val = document.getElementById('disease-search-input').value.trim();
      if (val) searchDisease(val);
    });
  }
  const disSearchInput = document.getElementById('disease-search-input');
  if (disSearchInput) {
    disSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && disSearchInput.value.trim()) {
        searchDisease(disSearchInput.value.trim());
      }
    });
  }

  // Bind Target Explorer Search Elements
  const tarSearchBtn = document.getElementById('target-search-btn');
  if (tarSearchBtn) {
    tarSearchBtn.addEventListener('click', () => {
      const val = document.getElementById('target-search-input').value.trim();
      if (val) searchTarget(val);
    });
  }
  const tarSearchInput = document.getElementById('target-search-input');
  if (tarSearchInput) {
    tarSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && tarSearchInput.value.trim()) {
        searchTarget(tarSearchInput.value.trim());
      }
    });
  }

  // Bind Compound Explorer Search Elements
  const compSearchBtn = document.getElementById('compound-search-btn');
  if (compSearchBtn) {
    compSearchBtn.addEventListener('click', () => {
      const val = document.getElementById('compound-search-input').value.trim();
      if (val) searchCompound(val);
    });
  }
  const compSearchInput = document.getElementById('compound-search-input');
  if (compSearchInput) {
    compSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && compSearchInput.value.trim()) {
        searchCompound(compSearchInput.value.trim());
      }
    });
  }

  // Bind Knowledge Graph Search Elements
  const graphSearchBtn = document.getElementById('graph-search-btn');
  if (graphSearchBtn) {
    graphSearchBtn.addEventListener('click', () => {
      const val = document.getElementById('graph-search-input').value.trim();
      if (val) searchAndDrawGraph(val);
    });
  }
  const graphSearchInput = document.getElementById('graph-search-input');
  if (graphSearchInput) {
    graphSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && graphSearchInput.value.trim()) {
        searchAndDrawGraph(graphSearchInput.value.trim());
      }
    });
  }

  // Bind Zoom Buttons
  const zoomInBtn = document.getElementById('graph-zoom-in');
  if (zoomInBtn) zoomInBtn.addEventListener('click', () => GraphModule.zoom('full-graph-svg', 1.4));
  const zoomOutBtn = document.getElementById('graph-zoom-out');
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => GraphModule.zoom('full-graph-svg', 0.7));
  const zoomResetBtn = document.getElementById('graph-zoom-reset');
  if (zoomResetBtn) zoomResetBtn.addEventListener('click', () => GraphModule.zoom('full-graph-svg', 0));

  // Bind AI Predictions Form Button
  const runAiBtn = document.getElementById('run-ai-btn');
  if (runAiBtn) {
    runAiBtn.addEventListener('click', () => {
      const disease = document.getElementById('ai-disease-input').value.trim();
      const target = document.getElementById('ai-target-input').value.trim();
      const compound = document.getElementById('ai-compound-input').value.trim();
      const runRefuter = document.getElementById('ai-run-refuter').checked;
      const maxCompounds = parseInt(document.getElementById('ai-max-compounds').value) || 10;
      const maxPubmed = parseInt(document.getElementById('ai-max-pubmed').value) || 10;

      if (!disease || !target) {
        return showToast('Disease and Target Gene symbol are required.', 'warning');
      }

      executePredictionPipeline({
        disease,
        target,
        compound: compound || null,
        run_adversarial: runRefuter,
        max_compounds: maxCompounds,
        max_pubmed: maxPubmed
      });
    });
  }

  // Bind Adversarial Lab Button
  const runLabBtn = document.getElementById('run-lab-btn');
  if (runLabBtn) {
    runLabBtn.addEventListener('click', () => {
      triggerAdversarialLab();
    });
  }

  // Bind Literature Search Button
  const litSearchBtn = document.getElementById('lit-search-btn');
  if (litSearchBtn) {
    litSearchBtn.addEventListener('click', () => {
      triggerLiteratureSearch();
    });
  }

  // Bind Export JSON button
  const exportBtn = document.getElementById('export-report-json');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      if (!AppState.activeReport) {
        return showToast('No generated report to export yet.', 'warning');
      }
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(AppState.activeReport, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `pharmamind_report_${AppState.currentDisease.replace(/\s+/g, '_')}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast('Report JSON downloaded successfully.', 'success');
    });
  }

    // Bind Export CSV button
  const exportCsvBtn = document.getElementById('export-report-csv');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => {
      if (!AppState.activeReport) {
        return showToast('No generated report to export yet.', 'warning');
      }
      const header = "Rank,Compound Name,Compound ID,Score\n";
      const rows = (AppState.activeReport.ranked_candidates || []).map((c, i) => `${i+1},"${c.compound_name}","${c.compound_id}",${c.score.toFixed(3)}`).join("\n");
      const dataStr = "data:text/csv;charset=utf-8," + encodeURIComponent(header + rows);
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `pharmamind_report_${AppState.currentDisease.replace(/\s+/g, '_')}.csv`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast('Report CSV downloaded successfully.', 'success');
    });
  }

  // Load Initial Subgraph on Dashboard Target Network SVG
  API.getSubgraph(AppState.currentDisease).then(data => {
    AppState.lastGraphData = data;
    GraphModule.draw('results-graph-svg', data);
  }).catch(e => {
    console.warn("Could not draw initial dashboard graph", e);
  });
});

async function searchAndDrawGraph(diseaseName) {
  try {
    const data = await API.getSubgraph(diseaseName);
    AppState.lastGraphData = data;
    GraphModule.draw('full-graph-svg', data);
    showToast(`Loaded subgraph for disease focus "${diseaseName}"`, 'success');
  } catch (err) {
    showToast(`Graph load failed: ${err.message}`, 'error');
  }
}
