import re
import os

def fix_css():
    with open('frontend/style.css', 'r', encoding='utf-8') as f:
        css = f.read()

    # Replace root variables
    new_root = """:root {
  --primary: #0369A1;
  --secondary: #E0F2FE;
  --accent: #0EA5E9;
  --bg: #F8FAFC;
  --panel: #FFFFFF;
  --text: #0F172A;
  --muted: #64748B;
  --panel-border: #E2E8F0;
  --panel-hover: #F1F5F9;
  --primary-glow: rgba(3, 105, 161, 0.15);
  --success: #059669;
  --warning: #D97706;
  --danger: #DC2626;
  --error: #DC2626;
  --font-main: 'Outfit', sans-serif;
}"""
    css = re.sub(r':root\s*\{[^}]+\}', new_root, css)

    # Add new button and mobile classes
    button_css = """
/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: var(--font-main);
  border: 1px solid transparent;
}
.btn-primary {
  background: var(--primary);
  color: #ffffff;
}
.btn-primary:hover {
  background: #0284c7;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
.btn-secondary {
  background: var(--panel);
  color: var(--primary);
  border-color: var(--primary);
}
.btn-secondary:hover {
  background: var(--secondary);
}
.btn-tertiary {
  background: transparent;
  color: var(--muted);
  border-color: transparent;
}
.btn-tertiary:hover {
  color: var(--primary);
  background: var(--panel-hover);
}
.btn-error {
  background: var(--error);
  color: #ffffff;
}
.btn-error:hover {
  background: #b91c1c;
}

/* Mobile Nav */
.menu-toggle {
  display: none;
  background: transparent;
  border: none;
  color: var(--text);
  cursor: pointer;
  padding: 8px;
}
.sidebar-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 999;
}
@media (max-width: 768px) {
  .menu-toggle {
    display: flex;
  }
  .sidebar {
    position: fixed;
    top: 0;
    left: -300px;
    height: 100vh;
    z-index: 1000;
    transition: left 0.3s ease;
    display: flex;
    margin: 0;
    border-radius: 0;
  }
  .sidebar.open {
    left: 0;
  }
  .sidebar-overlay.open {
    display: block;
  }
}

/* Semantic Table Overrides */
table.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
table.data-table th {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  border-bottom: 1px solid var(--panel-border);
  padding: 12px 8px;
  text-align: left;
}
table.data-table td {
  padding: 12px 8px;
  border-bottom: 1px solid var(--panel-border);
  color: var(--text);
}
table.data-table tbody tr:hover {
  background: var(--panel-hover);
}
"""
    css += button_css
    
    with open('frontend/style.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("Fixed style.css")

fix_css()
