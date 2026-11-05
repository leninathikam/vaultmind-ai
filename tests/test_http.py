import json
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.process = subprocess.Popen([sys.executable, "-m", "workbench.server", "--port", str(cls.port)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(500):
            try:
                cls.state = cls.get("/api/state")
                return
            except URLError:
                time.sleep(.1)
        cls.process.terminate()
        raise RuntimeError("Server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)

    @classmethod
    def get(cls, path):
        with urlopen(cls.base + path, timeout=3) as response:
            return json.load(response)

    def post(self, path, body, token=True, origin=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-VaultMind-CSRF"] = self.state["csrf"]
        if origin:
            headers["Origin"] = origin
        request = Request(self.base + path, json.dumps(body).encode(), headers)
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_readonly_endpoints_and_static_asset(self):
        self.assertTrue(self.get("/api/search?q=laptop+warranty")["results"])
        with urlopen(self.base + "/") as response:
            self.assertIn("Synthetic data only", response.read().decode())
            self.assertIn("frame-ancestors", response.headers["Content-Security-Policy"])

    def test_csrf_and_cross_origin_rejected(self):
        for token, origin in [(False, None), (True, "https://untrusted.example")]:
            with self.assertRaises(HTTPError) as result:
                self.post("/api/plan", {}, token, origin)
            self.assertEqual(result.exception.code, 403)

    def test_real_file_unchanged_after_simulated_move(self):
        source = ROOT / "samples/documents/laptop-warranty.md"
        before = source.read_bytes()
        plan = self.post("/api/plan", {"source": "documents/laptop-warranty.md", "destination": "archive/laptop-warranty.md"})
        result = self.post("/api/execute", {"fingerprint": plan["fingerprint"], "confirmation": f'APPROVE {plan["version"]}'})
        self.assertTrue(result["simulation"])
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse((ROOT / "samples/archive/laptop-warranty.md").exists())
        inverse = self.post("/api/inverse", {"fingerprint": plan["fingerprint"]})
        self.post("/api/execute", {"fingerprint": inverse["fingerprint"], "confirmation": f'APPROVE {inverse["version"]}'})

    def test_http_compare_and_organize_endpoints(self):
        # Test /api/compare
        diff = self.get("/api/compare?a=documents/insurance-policy-2025.md&b=documents/insurance-policy-2026.md")
        self.assertEqual(diff["baseline"]["effective_date"], "2025-01-01")
        self.assertEqual(diff["latest"]["effective_date"], "2026-01-01")
        self.assertTrue(len(diff["added_or_updated"]) > 0)

        # Test /api/organize
        res = self.post("/api/organize", {"candidates": [
            "documents/research/nlp-transformers.md",
            "documents/research/vision-diffusion.md",
            "documents/research/uncertain-multimodal.md"
        ]})
        self.assertIn("plan", res)
        self.assertIn("uncertain", res)
        self.assertEqual(len(res["uncertain"]), 1)
        self.assertEqual(res["uncertain"][0]["confidence"], "uncertain")

    def test_http_enhanced_features_endpoints(self):
        # 1. Warranty ledger
        warranty = self.get("/api/warranty-ledger")
        self.assertIn("assets", warranty)
        self.assertGreaterEqual(warranty["total_assets"], 3)
        self.assertIn("disclaimer", warranty)

        # 2. Tax dossier
        tax = self.get("/api/tax-dossier")
        self.assertIn("manifest", tax)
        self.assertIn("disclaimer", tax["manifest"])
        self.assertGreaterEqual(tax["manifest"]["total_staged"], 4)

        # 3. Quarantine detection and proposal
        quarantine = self.get("/api/quarantine")
        self.assertIn("sensitive_files", quarantine)
        q_plan = self.post("/api/quarantine", {"paths": ["documents/credentials-backup.md"]})
        self.assertIsNotNone(q_plan["plan"])
        self.assertEqual(q_plan["plan"]["plan_type"], "quarantine")

        # 4. SafeTagging plan
        tag_plan = self.post("/api/tags/plan", {
            "operations": [{"path": "documents/laptop-warranty.md", "tag_name": "Assets", "colour": "#10b981", "operation": "tag_add"}]
        })
        self.assertEqual(tag_plan["plan_type"], "tag")

        # 5. OCR endpoint
        ocr = self.get("/api/ocr?path=documents/scans/receipt-office-supplies.scan.md")
        self.assertEqual(ocr["engine"], "ug-photo:vision-ocr")
        self.assertEqual(ocr["confidence"], 0.94)

        # 6. Adversarial check endpoint
        adv = self.post("/api/adversarial-check", {})
        self.assertEqual(adv["rejection_rate"], 1.0)



if __name__ == "__main__":
    unittest.main()
