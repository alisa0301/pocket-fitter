"""Render START_HERE.md (+ validation figures) into a self-contained START_HERE.html."""
import base64, re, sys
from pathlib import Path
import markdown

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
md = (root / "START_HERE.md").read_text(encoding="utf-8")
md += """

## Validation at a glance

The ball-flight model against TrackMan tour averages, the simulated population against published distances, how far self-reported carry is off, and the two baselines. Details in `docs/SIMULATOR.md`.

![](docs/figures/fig1_physics_calibration.png) ![](docs/figures/fig2_population_vs_shotscope.png)
![](docs/figures/fig3_selfreport_error.png) ![](docs/figures/fig4_baselines_dev.png)
"""
body = markdown.markdown(md, extensions=["tables", "fenced_code"])


def inline(m):
    p = root / m.group(1)
    return f'<img alt="" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"'


body = re.sub(r'<img alt="" src="([^"]+\.png)"', inline, body)
css = """
:root{--ink:#0b0b0b;--ink2:#52514e;--line:#e6e5e0;--bg:#fcfcfb;--accent:#2a78d6;--code:#f3f2ee}
@media (prefers-color-scheme:dark){:root{--ink:#f0efec;--ink2:#c3c2b7;--line:#3a3a37;--bg:#1a1a19;--code:#262624}img{background:#fff;border-radius:6px}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:920px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:30px;line-height:1.2;margin:0 0 12px}h2{font-size:21px;margin:40px 0 10px;padding-top:12px;border-top:1px solid var(--line)}
p,li{color:var(--ink)}strong{font-weight:600}a{color:var(--accent)}
table{border-collapse:collapse;width:100%;margin:12px 0 20px;font-size:14.5px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}th{color:var(--ink2);font-weight:600}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:13.5px}
pre{background:var(--code);padding:14px 16px;border-radius:8px;overflow:auto}pre code{padding:0;background:none}
img{max-width:49%;height:auto;vertical-align:top}
@media (max-width:700px){img{max-width:100%}}
"""
html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Takomo Fitting Lab · start here</title><style>{css}</style></head><body><main>{body}</main></body></html>"""
(root / "START_HERE.html").write_text(html, encoding="utf-8")
print("wrote", root / "START_HERE.html", len(html) // 1024, "KB")
