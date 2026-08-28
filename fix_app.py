import re

def fix_app():
    with open('frontend/app.js', 'r', encoding='utf-8') as f:
        js = f.read()

    # 1. General color replacements
    js = js.replace('background: rgba(255,255,255,0.02)', 'background: var(--panel)')
    js = js.replace('background: rgba(255,255,255,0.01)', 'background: var(--panel)')
    js = js.replace('background: rgba(255,255,255,0.015)', 'background: var(--panel)')
    js = js.replace('border: 1px solid rgba(255,255,255,0.04)', 'border: 1px solid var(--panel-border)')
    js = js.replace('border: 1px solid rgba(255,255,255,0.05)', 'border: 1px solid var(--panel-border)')
    js = js.replace('border-bottom: 2px solid rgba(255,255,255,0.05)', 'border-bottom: 2px solid var(--panel-border)')
    js = js.replace('border-bottom: 1px solid rgba(255,255,255,0.05)', 'border-bottom: 1px solid var(--panel-border)')
    js = js.replace('border-bottom: 1px solid rgba(255,255,255,0.03)', 'border-bottom: 1px solid var(--panel-border)')
    js = js.replace('border-bottom: 1px solid rgba(255,255,255,0.1)', 'border-bottom: 1px solid var(--panel-border)')
    
    js = js.replace('color: #fff;', 'color: var(--text);')
    js = js.replace('color:#fff;', 'color: var(--text);')
    js = js.replace('color: #38bdf8;', 'color: var(--primary);')
    js = js.replace('color:#38bdf8;', 'color: var(--primary);')
    js = js.replace('color:#0284c7;', 'color: var(--primary);')
    js = js.replace('color: #cbd5e1;', 'color: var(--muted);')
    js = js.replace('color:#cbd5e1;', 'color: var(--muted);')
    js = js.replace('color: #94a3b8;', 'color: var(--muted);')
    js = js.replace('color:#94a3b8;', 'color: var(--muted);')
    js = js.replace('color: #64748b;', 'color: var(--muted);')
    js = js.replace('color:#64748b;', 'color: var(--muted);')
    
    js = js.replace('color:#f43f5e', 'color:var(--error)')
    js = js.replace('color:#ef4444', 'color:var(--error)')
    js = js.replace('color:#10b981', 'color:var(--success)')
    js = js.replace('color:#f59e0b', 'color:var(--warning)')
    
    js = js.replace('background:rgba(0,0,0,0.2)', 'background:var(--panel-hover)')
    js = js.replace('background:rgba(0,0,0,0.15)', 'background:var(--panel-hover)')
    js = js.replace('background: rgba(255,255,255,0.06)', 'background: var(--panel-hover)')
    
    # 2. Add Mobile nav close logic in switchTab
    mobile_nav_logic = """
  // Close mobile sidebar if open
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }
"""
    js = js.replace('const contents = document.querySelectorAll(\'.tab-content\');', mobile_nav_logic + '\n  const contents = document.querySelectorAll(\'.tab-content\');')

    # 3. Add mobile toggle event listener in DOMContentLoaded
    mobile_toggle_js = """
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
"""
    js = js.replace('// Main Header Search bar', mobile_toggle_js + '\n  // Main Header Search bar')

    # 4. Fix table rewrite logic in renderPipelineResults
    old_table_js = """      // Clear rows except header
      const rows = tableDiv.querySelectorAll('.row');
      rows.forEach((r, idx) => { if (idx > 0) r.remove(); });

      // Add actual data
      res.ranked_candidates.slice(0, 5).forEach((item, index) => {
        const row = document.createElement('div');
        row.className = 'row';
        
        const badge = item.score > 0.85 ? '<span class="pill high">High</span>' : 
                      item.score > 0.70 ? '<span class="pill medium">Medium</span>' : 
                      '<span class="pill low">Low</span>';
                      
        row.innerHTML = `
          <div class="rank">${index + 1}</div>
          <div class="compound"><div class="molecule">⌬</div><strong>${item.compound_name}</strong></div>
          <div>${item.target_name || AppState.currentTarget}</div>
          <div class="score">${item.score.toFixed(2)}</div>
          <div>${badge}</div>
          <div class="evidence">${item.pchembl_value ? item.pchembl_value.toFixed(1) : '6.5'} pIC50</div>
        `;
        // Make compound click fetch compound explorer
        row.querySelector('.compound').style.cursor = 'pointer';
        row.querySelector('.compound').addEventListener('click', () => {
          document.getElementById('compound-search-input').value = item.compound_id || item.compound_name;
          switchTab('Compound Explorer');
          searchCompound(item.compound_id || item.compound_name);
        });

        tableDiv.appendChild(row);
      });"""

    new_table_js = """      const tbody = tableDiv.querySelector('tbody');
      if (tbody) {
        tbody.innerHTML = '';
        res.ranked_candidates.slice(0, 5).forEach((item, index) => {
          const row = document.createElement('tr');
          const badge = item.score > 0.85 ? '<span class="pill high">High</span>' : 
                        item.score > 0.70 ? '<span class="pill medium">Medium</span>' : 
                        '<span class="pill low">Low</span>';
          row.innerHTML = `
            <td><div class="rank">${index + 1}</div></td>
            <td><div class="compound"><div class="molecule">⌬</div><strong>${item.compound_name}</strong></div></td>
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
      }"""
    
    js = js.replace(old_table_js, new_table_js)
    
    # 5. Fix Quick Actions button classes in DOM rendering
    js = js.replace('class="quick-btn"', 'class="btn btn-secondary"')
    
    # 6. Wire up CSV export
    csv_js = """  // Bind Export CSV button
  const exportCsvBtn = document.getElementById('export-report-csv');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => {
      if (!AppState.activeReport) {
        return showToast('No generated report to export yet.', 'warning');
      }
      const header = "Rank,Compound Name,Compound ID,Score\\n";
      const rows = (AppState.activeReport.ranked_candidates || []).map((c, i) => `${i+1},"${c.compound_name}","${c.compound_id}",${c.score.toFixed(3)}`).join("\\n");
      const dataStr = "data:text/csv;charset=utf-8," + encodeURIComponent(header + rows);
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `pharmamind_report_${AppState.currentDisease.replace(/\\s+/g, '_')}.csv`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast('Report CSV downloaded successfully.', 'success');
    });
  }"""
    js = js.replace('// Load Initial Subgraph', csv_js + '\\n\\n  // Load Initial Subgraph')
    
    with open('frontend/app.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("Fixed app.js")

fix_app()
