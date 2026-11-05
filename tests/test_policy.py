import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from tools.generate_samples import generate
from workbench.core import Index, Planner, UgosAdapter, masked, privacy_hints


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.planner = Planner([
            {"path": "documents/a.md", "sha256": "a" * 64, "size": 7},
            {"path": "documents/b.md", "sha256": "b" * 64, "size": 9},
            {"path": "documents/private/c.md", "sha256": "c" * 64, "size": 1},
        ])

    def plan(self):
        return self.planner.propose([("documents/a.md", "archive/a.md")])

    def approve(self, plan, selected=None):
        return self.planner.approve(plan.fingerprint, [0] if selected is None else selected, f"APPROVE {plan.version}")

    def test_preview_changes_no_files(self):
        before = dict(self.planner.files)
        self.plan()
        self.assertEqual(before, self.planner.files)

    def test_scope_escape_exclusion_and_prefix_lookalike(self):
        for source, dest in [("documents/a.md", "archive/../escape.md"), ("documents/a.md", "archive-lookalike/a.md"), ("documents/private/c.md", "archive/c.md"), ("documents/a.md", "/archive/a.md"), ("documents/a.md", "archive\\a.md")]:
            with self.subTest(source=source, dest=dest), self.assertRaises(ValueError):
                self.planner.propose([(source, dest)])

    def test_conflicts_rejected(self):
        for pairs in [[("documents/a.md", "documents/b.md")], [("documents/a.md", "archive/a.md"), ("documents/b.md", "archive/a.md")], [("documents/a.md", "archive/a.md"), ("documents/a.md", "archive/b.md")]]:
            with self.assertRaises(ValueError):
                self.planner.propose(pairs)

    def test_plan_is_frozen(self):
        plan = self.plan()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.version = 55

    def test_missing_approval(self):
        plan = self.plan()
        with self.assertRaises(ValueError):
            self.planner.execute(plan.fingerprint, "untrusted document approval")

    def test_generic_confirmation_not_authorization(self):
        plan = self.plan()
        with self.assertRaises(ValueError):
            self.planner.approve(plan.fingerprint, [0], "yes clean up")

    def test_wrong_version_and_replay(self):
        first = self.plan()
        token = self.approve(first)
        second = self.plan()
        with self.assertRaises(ValueError):
            self.planner.execute(second.fingerprint, token)
        with self.assertRaises(ValueError):
            self.planner.execute(first.fingerprint, token)

    def test_partial_approval(self):
        plan = self.planner.propose([("documents/a.md", "archive/a.md"), ("documents/b.md", "archive/b.md")])
        result = self.planner.execute(plan.fingerprint, self.approve(plan, [1]))
        self.assertEqual([r["index"] for r in result["outcomes"]], [1])
        self.assertIn("documents/a.md", self.planner.files)
        self.assertNotIn("documents/b.md", self.planner.files)

    def test_source_changed_after_approval(self):
        plan = self.plan()
        token = self.approve(plan)
        self.planner.files["documents/a.md"] = ("new", 7)
        with self.assertRaises(ValueError):
            self.planner.execute(plan.fingerprint, token)
        self.assertNotIn("archive/a.md", self.planner.files)

    def test_destination_created_after_approval(self):
        plan = self.plan()
        token = self.approve(plan)
        self.planner.files["archive/a.md"] = ("existing", 2)
        with self.assertRaises(ValueError):
            self.planner.execute(plan.fingerprint, token)
        self.assertEqual(self.planner.files["archive/a.md"], ("existing", 2))

    def test_scope_change_invalidates_grant(self):
        plan = self.plan()
        token = self.approve(plan)
        self.planner.exclusions = ("documents/a.md",)
        with self.assertRaises(ValueError):
            self.planner.execute(plan.fingerprint, token)

    def test_expiration(self):
        plan = self.plan()
        token = self.approve(plan)
        grant = self.planner.grants[token]
        self.planner.grants[token] = (*grant[:2], 0, *grant[3:])
        with self.assertRaises(ValueError):
            self.planner.execute(plan.fingerprint, token)

    def test_partial_failure_stops(self):
        plan = self.planner.propose([("documents/a.md", "archive/a.md"), ("documents/b.md", "archive/b.md")])
        result = self.planner.execute(plan.fingerprint, self.approve(plan, [0, 1]), fail_at=0)
        self.assertEqual([o["status"] for o in result["outcomes"]], ["failed", "unattempted"])

    def test_inverse_requires_fresh_approval(self):
        plan = self.plan()
        token = self.approve(plan)
        result = self.planner.execute(plan.fingerprint, token)
        inverse = self.planner.inverse(result)
        with self.assertRaises(ValueError):
            self.planner.execute(inverse.fingerprint, token)
        self.planner.execute(inverse.fingerprint, self.approve(inverse))
        self.assertIn("documents/a.md", self.planner.files)

    def test_inverse_rejects_modified_destination_or_record(self):
        plan = self.plan()
        result = self.planner.execute(plan.fingerprint, self.approve(plan))
        result["outcomes"][0]["source"] = "documents/forged.md"
        with self.assertRaises(ValueError):
            self.planner.inverse(result)

    def test_explainable_classification_with_uncertainty(self):
        planner = Planner([
            {"path": "documents/research/nlp-transformers.md", "sha256": "1" * 64, "size": 10},
            {"path": "documents/research/vision-diffusion.md", "sha256": "2" * 64, "size": 12},
            {"path": "documents/research/uncertain-multimodal.md", "sha256": "3" * 64, "size": 15},
        ])
        plan, uncertain = planner.propose_explainable_organization([
            "documents/research/nlp-transformers.md",
            "documents/research/vision-diffusion.md",
            "documents/research/uncertain-multimodal.md"
        ])
        self.assertEqual(len(plan.actions), 2)
        self.assertEqual(len(uncertain), 1)
        self.assertEqual(uncertain[0]["path"], "documents/research/uncertain-multimodal.md")
        self.assertEqual(uncertain[0]["confidence"], "uncertain")
        self.assertIn("Multimodal", uncertain[0]["rationale"])
        self.assertEqual(plan.actions[0].confidence, "high")
        self.assertIn("archive/research/nlp/", plan.actions[0].destination)
        self.assertIn("archive/research/vision/", plan.actions[1].destination)

    def test_tripartite_execution_ledger_and_receipt(self):
        planner = Planner([
            {"path": "documents/a.md", "sha256": "a" * 64, "size": 10},
            {"path": "documents/b.md", "sha256": "b" * 64, "size": 20},
        ])
        plan = planner.propose([("documents/a.md", "archive/a.md"), ("documents/b.md", "archive/b.md")])
        token = planner.approve(plan.fingerprint, [0, 1], f"APPROVE {plan.version}")
        
        # Test partial failure at index 1: item 0 completes, item 1 fails
        result = planner.execute(plan.fingerprint, token, fail_at=1)
        self.assertIn("receipt", result)
        self.assertEqual(len(result["authorized"]), 2)
        self.assertEqual(len(result["actually_changed"]), 1)
        self.assertEqual(result["actually_changed"][0]["source"], "documents/a.md")
        self.assertTrue(result["actually_changed"][0]["destination_verified"])
        self.assertEqual(len(result["unchanged"]), 1)
        self.assertEqual(result["unchanged"][0]["source"], "documents/b.md")

    def test_adversarial_ten_invariants(self):
        """Verify 100% rejection across all ten adversarial attack vectors."""
        p = self.planner
        # 1. Canonical scope escape
        with self.assertRaises(ValueError): p.propose([("documents/a.md", "archive/../escape.md")])
        # 2. Excluded child folder traversal
        with self.assertRaises(ValueError): p.propose([("documents/private/c.md", "archive/c.md")])
        # 3. Prefix lookalike directory
        with self.assertRaises(ValueError): p.propose([("documents/a.md", "archive-lookalike/a.md")])
        # 4. Stale source hash after preview
        plan = self.plan()
        token = self.approve(plan)
        p.files["documents/a.md"] = ("stale_hash", 7)
        with self.assertRaises(ValueError): p.execute(plan.fingerprint, token)
        p.files["documents/a.md"] = ("a" * 64, 7)
        # 5. Destination collision
        plan2 = self.plan()
        token2 = self.approve(plan2)
        p.files["archive/a.md"] = ("colliding", 99)
        with self.assertRaises(ValueError): p.execute(plan2.fingerprint, token2)
        del p.files["archive/a.md"]
        # 6. Generic confirmation phrase rejection
        plan3 = self.plan()
        with self.assertRaises(ValueError): p.approve(plan3.fingerprint, [0], "OK, proceed")
        # 7. Unapproved action execution
        plan4 = p.propose([("documents/a.md", "archive/a.md"), ("documents/b.md", "archive/b.md")])
        token4 = p.approve(plan4.fingerprint, [0], f"APPROVE {plan4.version}")
        res4 = p.execute(plan4.fingerprint, token4)
        self.assertEqual(len(res4["actually_changed"]), 1)
        self.assertIn("documents/b.md", p.files) # Untouched!
        # 8. Token replay prevention
        with self.assertRaises(ValueError): p.execute(plan4.fingerprint, token4)
        # 9. Chained / cyclic move attempt
        with self.assertRaises(ValueError): p.propose([("documents/b.md", "archive/b.md"), ("archive/b.md", "archive/c.md")])
        # 10. Inverse destination tampered
        inverse_input = dict(res4)
        inverse_input["actually_changed"][0]["sha256"] = "tampered"
        with self.assertRaises(ValueError): p.inverse(inverse_input)

    def test_ugos_adapter_cannot_fake_success(self):
        with self.assertRaises(NotImplementedError):
            UgosAdapter().delegate("file-agent", "find")


class IndexTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / "tmp/tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.labels = generate(self.root)
        self.index = Index()
        self.index.scan(self.root)

    def tearDown(self):
        self.index.close()
        assert self.root.resolve().is_relative_to((Path(__file__).resolve().parents[1] / "tmp/tests").resolve())
        self.temp.cleanup()

    def test_exclusion_before_indexing(self):
        self.assertFalse(any(f["path"].startswith("private/") for f in self.index.files()))
        self.assertFalse(any("EXCLUDED_SENTINEL_42" in f["body"] for f in self.index.files()))
        self.assertEqual(self.index.search("SENTINEL"), [])

    def test_incremental_update_and_removal(self):
        self.assertEqual(self.index.scan(self.root)["changed"], 0)
        (self.root / "documents/laptop-warranty.md").write_text("Unique changed content")
        (self.root / "documents/router-manual-v1.md").unlink()
        result = self.index.scan(self.root)
        self.assertEqual((result["changed"], result["removed"]), (1, 1))
        self.assertEqual(self.index.search("Unique changed")[0]["path"], "documents/laptop-warranty.md")

    def test_budget_does_not_replace_existing_index(self):
        before = self.index.files()
        with self.assertRaises(ValueError):
            self.index.scan(self.root, limit=2)
        self.assertEqual(before, self.index.files())

    def test_query_syntax_is_not_executable(self):
        for query in ['" OR * --', "'; DROP TABLE files; --", "<script>alert(1)</script>"]:
            self.index.search(query)
        self.assertGreater(len(self.index.files()), 100)

    def test_duplicate_groups_match_fixture_labels(self):
        self.assertEqual({frozenset(g["paths"]) for g in self.index.duplicates()}, {frozenset(g) for g in self.labels["duplicate_groups"]})

    def test_masked_preview_and_negative_control(self):
        self.assertNotIn("owner@example.test", masked("owner@example.test"))
        self.assertEqual(privacy_hints("This discusses email and phone privacy"), [])

    def test_contextual_version_diff(self):
        diff = self.index.compare_versions("documents/insurance-policy-2025.md", "documents/insurance-policy-2026.md")
        self.assertEqual(diff["baseline"]["effective_date"], "2025-01-01")
        self.assertEqual(diff["latest"]["effective_date"], "2026-01-01")
        self.assertTrue(any("Solar panel" in line for line in diff["added_or_updated"]))
        self.assertTrue(any("Trampoline" in line for line in diff["removed_provisions"]))
        self.assertTrue(any("APX-99201" in line for line in diff["unchanged_core"]))
        self.assertTrue(len(diff["citations"]) > 0)

    def test_clear_only_generated_index(self):
        self.index.clear()
        self.assertEqual(self.index.files(), [])
        self.assertTrue((self.root / "documents/laptop-warranty.md").exists())

    def test_warranty_asset_ledger_extraction(self):
        """Feature 1: Test warranty extraction and missing serial handling without hallucination."""
        ledger_result = self.index.extract_warranty_ledger()
        self.assertGreaterEqual(ledger_result["total_assets"], 3)
        self.assertGreaterEqual(ledger_result["assets_with_missing_serials"], 2)

        # Check Acer Monitor with verified serial
        acer = next((a for a in ledger_result["assets"] if "Acer" in a["product_name"]), None)
        self.assertIsNotNone(acer)
        self.assertEqual(acer["serial_number"], "AC-883920-K")
        self.assertEqual(acer["serial_status"], "verified")
        self.assertEqual(acer["purchase_date"], "2025-06-10")
        self.assertEqual(acer["expiration_date"], "2027-06-10")

        # Check SoundPulse with missing serial
        headphones = next((a for a in ledger_result["assets"] if "SoundPulse" in a["product_name"]), None)
        self.assertIsNotNone(headphones)
        self.assertIsNone(headphones["serial_number"])
        self.assertEqual(headphones["serial_status"], "missing")
        self.assertIn("serial_number_missing_from_documents", headphones["uncertainty_flags"])

    def test_zero_trust_quarantine_and_secret_redaction(self):
        """Feature 2: Test detection of sensitive files and Zero-Trust Quarantine."""
        sensitive = self.index.detect_sensitive_files()
        paths = [s["path"] for s in sensitive]
        self.assertIn("documents/credentials-backup.md", paths)
        self.assertIn("documents/tax/2025-w2-statement.md", paths)

        planner = Planner(self.index.files())
        plan, manifest = planner.propose_quarantine(["documents/credentials-backup.md"])
        self.assertIsNotNone(plan)
        self.assertEqual(plan.plan_type, "quarantine")
        self.assertEqual(plan.actions[0].destination, "archive/quarantine/credentials-backup.md")

        # Approval and execution
        token = planner.approve(plan.fingerprint, [0], f"APPROVE {plan.version}")
        result = planner.execute(plan.fingerprint, token)
        self.assertEqual(len(result["actually_changed"]), 1)
        self.assertIn("archive/quarantine/credentials-backup.md", planner.files)
        self.assertNotIn("documents/credentials-backup.md", planner.files)

        # Verify no secret is exposed in plaintext in execution history
        history_json = json.dumps(planner.history)
        self.assertNotIn("sk-live-vaultmind-secret-994821", history_json)
        self.assertNotIn("db-super-secret-pw-992", history_json)

    def test_safetagging_idempotency_and_preservation(self):
        """Feature 3: Test native SafeTagging without moving files and ensuring idempotency."""
        planner = Planner(self.index.files())
        target_path = "documents/laptop-warranty.md"
        before_hash, before_size = planner.files[target_path]

        # 1. Propose adding tag "Hardware-Asset"
        plan = planner.propose_tags([
            {"path": target_path, "tag_name": "Hardware-Asset", "colour": "#10b981", "operation": "tag_add"}
        ])
        self.assertEqual(plan.plan_type, "tag")
        self.assertFalse(plan.actions[0].extra["is_no_op"])

        # Approve and execute
        token = planner.approve(plan.fingerprint, [0], f"APPROVE {plan.version}")
        result = planner.execute(plan.fingerprint, token)
        self.assertEqual(len(result["actually_changed"]), 1)
        self.assertEqual(len(planner.tag_get_file(target_path)), 1)
        self.assertEqual(planner.tag_get_file(target_path)[0]["name"], "Hardware-Asset")

        # Verify underlying file was NOT moved or altered
        self.assertIn(target_path, planner.files)
        self.assertEqual(planner.files[target_path], (before_hash, before_size))

        # 2. Idempotency test: Re-adding the exact same tag is recognized as a no-op
        plan_idem = planner.propose_tags([
            {"path": target_path, "tag_name": "Hardware-Asset", "colour": "#10b981", "operation": "tag_add"}
        ])
        self.assertTrue(plan_idem.actions[0].extra["is_no_op"])
        token_idem = planner.approve(plan_idem.fingerprint, [0], f"APPROVE {plan_idem.version}")
        result_idem = planner.execute(plan_idem.fingerprint, token_idem)
        self.assertEqual(len(result_idem["actually_changed"]), 0)
        self.assertEqual(len(result_idem["unchanged"]), 1)
        self.assertEqual(result_idem["unchanged"][0]["reason"], "tag already present")
        # Tags remain unchanged and preserved
        self.assertEqual(len(planner.tag_get_file(target_path)), 1)

    def test_tax_dossier_stager_and_duplicate_handling(self):
        """Feature 6: Test financial document organization, duplicate detection, and manifests."""
        planner = Planner(self.index.files())
        plan, manifest = planner.stage_tax_dossier()
        self.assertIsNotNone(plan)
        self.assertEqual(plan.plan_type, "tax_stage")
        self.assertGreaterEqual(manifest["total_staged"], 4)

        # Verify duplicate donation was skipped and flagged
        flagged_dupes = [d["duplicate_path"] for d in manifest["duplicates_flagged"]]
        self.assertIn("documents/tax/2025-charity-donation-copy.md", flagged_dupes)

        # Verify structured destination paths (Year/Quarter/Category)
        destinations = [a.destination for a in plan.actions]
        self.assertTrue(any("archive/tax/2025/Annual/Income/2025-w2-statement.md" in d for d in destinations))
        self.assertTrue(any("archive/tax/2025/Q1/Estimated_Payments/2025-q1-estimated-payment.md" in d for d in destinations))
        self.assertTrue(any("archive/tax/2025/Q2/Healthcare/2025-medical-expenses.md" in d for d in destinations))
        self.assertTrue(any("archive/tax/2025/Q4/Deductions/2025-charity-donation.md" in d for d in destinations))
        self.assertTrue(any("archive/tax/2024/Annual/Income/2024-1099-misc.md" in d for d in destinations))

        # Verify statutory disclaimer is present
        self.assertIn("Tax Dossier Stager provides organizational file staging", manifest["disclaimer"])

    def test_ocr_scanned_documents_provenance_and_uncertainty(self):
        """Feature 7: Test OCR provenance, confidence scoring, and uncertainty flagging."""
        # Clean scan
        clean_res = self.index.process_ocr("documents/scans/receipt-office-supplies.scan.md")
        self.assertIsNotNone(clean_res)
        self.assertEqual(clean_res.engine, "ug-photo:vision-ocr")
        self.assertEqual(clean_res.confidence, 0.94)
        self.assertEqual(clean_res.status, "verified")
        self.assertEqual(clean_res.extracted_fields.get("vendor"), "Office Depot Store #4821")
        self.assertEqual(clean_res.extracted_fields.get("total"), "142.50 USD")

        # Degraded / faded scan with uncertainty
        faded_res = self.index.process_ocr("documents/scans/faded-mechanic-invoice.scan.md")
        self.assertIsNotNone(faded_res)
        self.assertEqual(faded_res.status, "uncertain_characters_flagged")
        self.assertIn("low_confidence_characters_flagged", faded_res.uncertainty_flags)
        self.assertIn("faded_receipt_footer_detected", faded_res.uncertainty_flags)
        self.assertLess(faded_res.confidence, 0.80)

    def test_proofchain_lifecycle_and_tamper_rejection(self):
        """ProofChain: End-to-end proposal -> validation -> approval -> execution -> receipt -> inverse."""
        planner = Planner(self.index.files())
        src = "documents/laptop-warranty.md"
        dst = "archive/laptop-warranty.md"

        # 1. Proposal
        plan = planner.propose([(src, dst)])
        self.assertEqual(plan.version, 1)

        # 2. Strict approval syntax
        with self.assertRaises(ValueError):
            planner.approve(plan.fingerprint, [0], "PROCEED")
        with self.assertRaises(ValueError):
            planner.approve(plan.fingerprint, [0], "APPROVE 99")

        token = planner.approve(plan.fingerprint, [0], "APPROVE 1")

        # 3. Execution & Cryptographic Receipt
        exec_res = planner.execute(plan.fingerprint, token)
        self.assertTrue(exec_res["proofchain"])
        self.assertIn("receipt", exec_res)
        self.assertEqual(len(exec_res["actually_changed"]), 1)
        self.assertEqual(exec_res["actually_changed"][0]["destination"], dst)

        # 4. Anti-replay check
        with self.assertRaises(ValueError):
            planner.execute(plan.fingerprint, token)

        # 5. Inverse rollback proposal
        inv_plan = planner.inverse(exec_res)
        self.assertEqual(inv_plan.actions[0].source, dst)
        self.assertEqual(inv_plan.actions[0].destination, src)

        # Inverse requires its own approval
        inv_token = planner.approve(inv_plan.fingerprint, [0], f"APPROVE {inv_plan.version}")
        inv_exec = planner.execute(inv_plan.fingerprint, inv_token)
        self.assertEqual(len(inv_exec["actually_changed"]), 1)
        self.assertIn(src, planner.files)
        self.assertNotIn(dst, planner.files)


if __name__ == "__main__":
    unittest.main()
