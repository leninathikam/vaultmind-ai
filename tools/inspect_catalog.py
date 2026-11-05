import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
catalog_path = ROOT / "vendor/official/uliya-skill-kit/data/capability-catalog.json"
data = json.loads(catalog_path.read_text(encoding="utf-8"))

lines = []
for cli in data.get("clis", []):
    name = cli.get("name")
    agent = cli.get("agent")
    desc = cli.get("description", "")
    lines.append(f"CLI: {name} (agent: {agent}) - {desc}")
    for act in cli.get("actions", []):
        act_name = act.get("name")
        act_desc = act.get("description", "")
        params = [f"{p.get('name')}{'*' if p.get('required') else ''}:{p.get('type')}" for p in act.get("parameters", [])]
        lines.append(f"  - {act_name} ({', '.join(params)}): {act_desc}")
    lines.append("")

(ROOT / "tools/catalog_summary.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {len(lines)} lines to tools/catalog_summary.txt")
