import re

html = open('frontend/index.html', encoding='utf8').read()

html = re.sub(r'<button class="quick-btn" id="export-report-json"[^>]*>.*?JSON</button>', r'<button class="btn btn-secondary" id="export-report-json"><i data-lucide="file-json" size="14"></i> JSON</button>', html, flags=re.DOTALL)
html = re.sub(r'<button class="quick-btn" id="export-report-csv"[^>]*>.*?CSV</button>', r'<button class="btn btn-secondary" id="export-report-csv"><i data-lucide="file-spreadsheet" size="14"></i> CSV</button>', html, flags=re.DOTALL)
html = re.sub(r'<button class="quick-btn" id="export-report-md"[^>]*>.*?Markdown</button>', r'<button class="btn btn-secondary" id="export-report-md"><i data-lucide="file-text" size="14"></i> Markdown</button>', html, flags=re.DOTALL)
html = re.sub(r'<button class="quick-btn" id="export-report-pdf"[^>]*>.*?PDF Report</button>', r'<button class="btn btn-primary" id="export-report-pdf"><i data-lucide="download" size="14"></i> PDF Report</button>', html, flags=re.DOTALL)

# Let's also check if there are other "#ffffff" that need to be var(--panel)
html = html.replace('background-color: #ffffff;', 'background-color: var(--panel);')
html = html.replace('background: #ffffff;', 'background: var(--panel);')
html = html.replace('background: #ffffff ', 'background: var(--panel) ')

open('frontend/index.html', 'w', encoding='utf8').write(html)
