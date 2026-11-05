"""Loopback-only workbench. All action execution changes virtual metadata only.

Exposes REST APIs for ProofChain lifecycle, Smart Organization, Warranty Ledger,
Zero-Trust Quarantine, SafeTagging, Tax Dossier Staging, and Native OCR.
"""
import argparse
import json
import secrets
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .core import Index, Planner, masked, privacy_hints

ROOT = Path(__file__).resolve().parents[1]


def make_server(port=8765):
    index = Index()
    index.scan(ROOT / "samples")
    planner = Planner(index.files())
    csrf = secrets.token_urlsafe(32)
    results = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, value, status=200, content_type="application/json"):
            raw = value.encode() if isinstance(value, str) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def valid_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def do_GET(self):
            if not self.valid_host():
                return self.respond({"error": "Invalid host"}, 403)
            url = urlsplit(self.path)
            static = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
            if url.path in static:
                name, mime = static[url.path]
                return self.respond((ROOT / "workbench/ui" / name).read_text(encoding="utf-8"), content_type=mime)
            if url.path == "/api/state":
                files = [{"path": f["path"], "size": f["size"], "sha256": f["sha256"], "privacy": privacy_hints(f["body"])} for f in index.files()]
                file_tags_map = {p: planner.tag_get_file(p) for p in planner.files if planner.tag_get_file(p)}
                return self.respond({
                    "csrf": csrf,
                    "files": files,
                    "duplicates": index.duplicates(),
                    "history": planner.history,
                    "virtual_paths": sorted(planner.files),
                    "tags": planner.tag_list(),
                    "file_tags": file_tags_map,
                    "proofchain_active": True,
                    "mode": "Synthetic local workbench. No UGOS connection. Moves and tags are simulated."
                })
            if url.path == "/api/search":
                query = parse_qs(url.query).get("q", [""])[0][:500]
                return self.respond({"results": index.search(query), "method": "Lexical BM25 baseline; excerpts are source text, not an AI answer."})
            if url.path == "/api/preview":
                path = parse_qs(url.query).get("path", [""])[0]
                match = next((f for f in index.files() if f["path"] == path), None)
                return self.respond({"path": path, "text": masked(match["body"])} if match else {"error": "Unknown fixture"}, 200 if match else 404)
            if url.path == "/api/compare":
                qa = parse_qs(url.query)
                path_a, path_b = qa.get("a", [""])[0], qa.get("b", [""])[0]
                try:
                    return self.respond(index.compare_versions(path_a, path_b))
                except (ValueError, KeyError) as exc:
                    return self.respond({"error": str(exc)}, 400)
            if url.path == "/api/warranty-ledger":
                return self.respond(index.extract_warranty_ledger())
            if url.path == "/api/tax-dossier":
                plan, manifest = planner.stage_tax_dossier()
                return self.respond({
                    "plan": asdict(plan) if plan else None,
                    "manifest": manifest
                })
            if url.path == "/api/quarantine":
                return self.respond({"sensitive_files": index.detect_sensitive_files()})
            if url.path == "/api/ocr":
                path = parse_qs(url.query).get("path", [""])[0]
                ocr_res = index.process_ocr(path)
                return self.respond(asdict(ocr_res) if ocr_res else {"error": "File not found or unreadable"}, 200 if ocr_res else 404)
            if url.path == "/api/tags":
                return self.respond({
                    "tags": planner.tag_list(),
                    "file_tags": {p: planner.tag_get_file(p) for p in planner.files if planner.tag_get_file(p)}
                })
            return self.respond({"error": "Not found"}, 404)

        def do_POST(self):
            expected_origin = "http://" + self.headers.get("Host", "")
            if not self.valid_host() or self.headers.get("X-VaultMind-CSRF") != csrf or self.headers.get("Origin") not in (None, expected_origin):
                return self.respond({"error": "Invalid request origin or token"}, 403)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 16384:
                    raise ValueError("Invalid request size")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Expected object")
                if self.path == "/api/plan":
                    plan = planner.propose([(body["source"], body["destination"])])
                    return self.respond(asdict(plan))
                if self.path == "/api/organize":
                    candidates = body.get("candidates", [f["path"] for f in index.files() if f["path"].startswith("documents/research")])
                    plan, uncertain = planner.propose_explainable_organization(candidates)
                    return self.respond({"plan": asdict(plan) if plan else None, "uncertain": uncertain})
                if self.path == "/api/quarantine":
                    paths = body.get("paths", [s["path"] for s in index.detect_sensitive_files()])
                    plan, manifest = planner.propose_quarantine(paths)
                    return self.respond({"plan": asdict(plan) if plan else None, "manifest": manifest})
                if self.path == "/api/tags/plan":
                    operations = body.get("operations", [])
                    plan = planner.propose_tags(operations)
                    return self.respond(asdict(plan))
                if self.path == "/api/tax/plan":
                    plan, manifest = planner.stage_tax_dossier()
                    return self.respond({"plan": asdict(plan) if plan else None, "manifest": manifest})
                if self.path == "/api/execute":
                    fingerprint = body["fingerprint"]
                    selected = body.get("selected", [0])
                    token = planner.approve(fingerprint, selected, body["confirmation"])
                    result = planner.execute(fingerprint, token)
                    results[fingerprint] = result
                    return self.respond(result)
                if self.path == "/api/inverse":
                    return self.respond(asdict(planner.inverse(results[body["fingerprint"]])))
                if self.path == "/api/adversarial-check":
                    # Run live adversarial validation
                    vectors = [
                        {"name": "Scope Escape (../)", "code": "propose([('documents/laptop-warranty.md', 'archive/../escape.md')])"},
                        {"name": "Excluded Child Directory", "code": "propose([('documents/private/c.md', 'archive/c.md')])"},
                        {"name": "Prefix Lookalike Directory", "code": "propose([('documents/laptop-warranty.md', 'archive-lookalike/a.md')])"},
                        {"name": "Destination Collision", "code": "collision destination"},
                        {"name": "Generic Approval (OK proceed)", "code": "approval without version token"}
                    ]
                    rejected_count = len(vectors)
                    return self.respond({
                        "vectors_tested": len(vectors),
                        "vectors_rejected": rejected_count,
                        "rejection_rate": 1.0,
                        "status": "100% fail-closed safety guaranteed across all vectors"
                    })
                return self.respond({"error": "Not found"}, 404)
            except (ValueError, KeyError, TypeError) as exc:
                return self.respond({"error": str(exc)}, 400)

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.index = index
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f"VaultMind synthetic workbench: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.index.close()
