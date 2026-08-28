import re

def fix_html():
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Insert sidebar overlay after <div class="app">
    if '<div class="sidebar-overlay"' not in html:
        html = html.replace('<div class="app">', '<div class="app">\n    <div class="sidebar-overlay" id="sidebar-overlay"></div>')

    # Add mobile toggle
    if '<button class="menu-toggle"' not in html:
        header_repl = '<header class="top" style="justify-content: space-between; width: 100%;">\n        <button class="menu-toggle" id="mobile-menu-btn" aria-label="Open menu"><i data-lucide="menu"></i></button>'
        html = re.sub(r'<header class="top"[^>]*>', header_repl, html)

    # General color replacements (Dark mode overrides)
    html = html.replace('background: rgba(255,255,255,0.03)', 'background: var(--panel)')
    html = html.replace('background: rgba(255,255,255,0.01)', 'background: var(--panel)')
    html = html.replace('border: 1px solid rgba(255,255,255,0.08)', 'border: 1px solid var(--panel-border)')
    html = html.replace('border: 1px solid rgba(255,255,255,0.04)', 'border: 1px solid var(--panel-border)')
    html = html.replace('color: #fff;', 'color: var(--text);')
    html = html.replace('color:#fff;', 'color: var(--text);')
    html = html.replace('color: #38bdf8;', 'color: var(--primary);')
    html = html.replace('color:#38bdf8;', 'color: var(--primary);')
    html = html.replace('color: #cbd5e1;', 'color: var(--muted);')
    html = html.replace('color:#cbd5e1;', 'color: var(--muted);')
    html = html.replace('color: #94a3b8;', 'color: var(--muted);')
    html = html.replace('color:#94a3b8;', 'color: var(--muted);')
    html = html.replace('background: #0f172a;', 'background: var(--panel);')
    html = html.replace('background: rgba(0,0,0,0.3);', 'background: var(--panel-hover);')
    html = html.replace('color: #64748b;', 'color: var(--muted);')

    # Fix buttons
    html = re.sub(r'class="quick-btn" id="run-ai-btn"[^>]*Execute Discovery Pipeline</button>', 
                  r'class="btn btn-primary" id="run-ai-btn" style="margin-top: auto;">Execute Discovery Pipeline</button>', html)
    html = re.sub(r'class="quick-btn" id="run-lab-btn"[^>]*Run Adversarial Refuter</button>', 
                  r'class="btn btn-error" id="run-lab-btn" style="margin-top: auto;">Run Adversarial Refuter</button>', html)
    
    html = html.replace('class="quick-btn" id="disease-search-btn"', 'class="btn btn-primary" id="disease-search-btn"')
    html = html.replace('class="quick-btn" id="target-search-btn"', 'class="btn btn-primary" id="target-search-btn"')
    html = html.replace('class="quick-btn" id="compound-search-btn"', 'class="btn btn-primary" id="compound-search-btn"')
    html = html.replace('class="quick-btn" id="lit-search-btn"', 'class="btn btn-primary" id="lit-search-btn"')
    
    # Reports buttons
    html = re.sub(r'class="quick-btn" id="export-report-json"[^>]*JSON</button>', r'class="btn btn-secondary" id="export-report-json"><i data-lucide="file-json" size="14"></i> JSON</button>', html)
    html = re.sub(r'class="quick-btn" id="export-report-csv"[^>]*CSV</button>', r'class="btn btn-secondary" id="export-report-csv"><i data-lucide="file-spreadsheet" size="14"></i> CSV</button>', html)
    html = re.sub(r'class="quick-btn" id="export-report-md"[^>]*Markdown</button>', r'class="btn btn-secondary" id="export-report-md"><i data-lucide="file-text" size="14"></i> Markdown</button>', html)
    html = re.sub(r'class="quick-btn" id="export-report-pdf"[^>]*PDF Report</button>', r'class="btn btn-primary" id="export-report-pdf"><i data-lucide="download" size="14"></i> PDF Report</button>', html)
    
    # Fix Dashboard Table to Semantic Table
    # The dashboard table is currently divs. Let's find `<div class="table">` and rewrite the dashboard table specifically.
    if '<div class="table">' in html:
        # We only want to rewrite the first table in the dashboard, but let's just do it manually with a regex block or string replacement.
        old_table = '''<div class="table">
              <div class="row th">
                <div>#</div>
                <div>Compound</div>
                <div>Target</div>
                <div>Relevance</div>
                <div>Confidence</div>
                <div>Evidence</div>
              </div>
              <div class="row">
                <div class="rank">1</div>
                <div class="compound">
                  <div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Nirmatrelvir</strong>
                </div>
                <div><span class="target-tag">Mpro (3CLpro)</span></div>
                <div class="relevance-col">
                  <div class="score">0.98</div>
                  <div class="bar-wrap"><div class="bar" style="width: 98%; background: var(--success);"></div></div>
                </div>
                <div><span class="pill high">High</span></div>
                <div class="evidence">8.5 pIC50</div>
              </div>
              <div class="row">
                <div class="rank">2</div>
                <div class="compound">
                  <div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Remdesivir</strong>
                </div>
                <div><span class="target-tag">RdRp</span></div>
                <div class="relevance-col">
                  <div class="score">0.94</div>
                  <div class="bar-wrap"><div class="bar" style="width: 94%; background: var(--success);"></div></div>
                </div>
                <div><span class="pill high">High</span></div>
                <div class="evidence">6.1 pIC50</div>
              </div>
              <div class="row">
                <div class="rank">3</div>
                <div class="compound">
                  <div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Molnupiravir</strong>
                </div>
                <div><span class="target-tag">RdRp</span></div>
                <div class="relevance-col">
                  <div class="score">0.89</div>
                  <div class="bar-wrap"><div class="bar" style="width: 89%; background: var(--primary);"></div></div>
                </div>
                <div><span class="pill high">High</span></div>
                <div class="evidence">5.8 pIC50</div>
              </div>
              <div class="row">
                <div class="rank">4</div>
                <div class="compound">
                  <div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Baricitinib</strong>
                </div>
                <div><span class="target-tag">JAK1/2</span></div>
                <div class="relevance-col">
                  <div class="score">0.85</div>
                  <div class="bar-wrap"><div class="bar" style="width: 85%; background: var(--primary);"></div></div>
                </div>
                <div><span class="pill high">High</span></div>
                <div class="evidence">8.2 pIC50</div>
              </div>
              <div class="row">
                <div class="rank">5</div>
                <div class="compound">
                  <div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Favipiravir</strong>
                </div>
                <div><span class="target-tag">RdRp</span></div>
                <div class="relevance-col">
                  <div class="score">0.72</div>
                  <div class="bar-wrap"><div class="bar" style="width: 72%; background: var(--warning);"></div></div>
                </div>
                <div><span class="pill medium">Medium</span></div>
                <div class="evidence">4.2 pIC50</div>
              </div>
            </div>'''
            
        new_table = '''<table class="data-table dashboard-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Compound</th>
                  <th>Target</th>
                  <th>Relevance</th>
                  <th>Confidence</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><div class="rank">1</div></td>
                  <td><div class="compound"><div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Nirmatrelvir</strong></div></td>
                  <td><span class="target-tag">Mpro (3CLpro)</span></td>
                  <td><div class="relevance-col"><div class="score">0.98</div><div class="bar-wrap"><div class="bar" style="width: 98%; background: var(--success);"></div></div></div></td>
                  <td><span class="pill high">High</span></td>
                  <td><div class="evidence">8.5 pIC50</div></td>
                </tr>
                <tr>
                  <td><div class="rank">2</div></td>
                  <td><div class="compound"><div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Remdesivir</strong></div></td>
                  <td><span class="target-tag">RdRp</span></td>
                  <td><div class="relevance-col"><div class="score">0.94</div><div class="bar-wrap"><div class="bar" style="width: 94%; background: var(--success);"></div></div></div></td>
                  <td><span class="pill high">High</span></td>
                  <td><div class="evidence">6.1 pIC50</div></td>
                </tr>
                <tr>
                  <td><div class="rank">3</div></td>
                  <td><div class="compound"><div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Molnupiravir</strong></div></td>
                  <td><span class="target-tag">RdRp</span></td>
                  <td><div class="relevance-col"><div class="score">0.89</div><div class="bar-wrap"><div class="bar" style="width: 89%; background: var(--primary);"></div></div></div></td>
                  <td><span class="pill high">High</span></td>
                  <td><div class="evidence">5.8 pIC50</div></td>
                </tr>
                <tr>
                  <td><div class="rank">4</div></td>
                  <td><div class="compound"><div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Baricitinib</strong></div></td>
                  <td><span class="target-tag">JAK1/2</span></td>
                  <td><div class="relevance-col"><div class="score">0.85</div><div class="bar-wrap"><div class="bar" style="width: 85%; background: var(--primary);"></div></div></div></td>
                  <td><span class="pill high">High</span></td>
                  <td><div class="evidence">8.2 pIC50</div></td>
                </tr>
                <tr>
                  <td><div class="rank">5</div></td>
                  <td><div class="compound"><div class="molecule"><i data-lucide="hexagon" size="18"></i></div><strong>Favipiravir</strong></div></td>
                  <td><span class="target-tag">RdRp</span></td>
                  <td><div class="relevance-col"><div class="score">0.72</div><div class="bar-wrap"><div class="bar" style="width: 72%; background: var(--warning);"></div></div></div></td>
                  <td><span class="pill medium">Medium</span></td>
                  <td><div class="evidence">4.2 pIC50</div></td>
                </tr>
              </tbody>
            </table>'''
        html = html.replace(old_table, new_table)
        
    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Fixed index.html")

fix_html()
