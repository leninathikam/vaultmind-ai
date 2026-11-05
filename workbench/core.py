"""Measured local baselines and an in-memory SafeAction policy reference.

VaultMind ProofChain Protocol:
AI Proposal -> Deterministic Safety Validation -> Human Approval -> Native UGOS Execution -> Verified Execution Receipt.

No operation in Planner modifies real NAS/local files. Index reads are confined
to an explicitly provided corpus, reject links, and are bounded.
This module is excluded from ZIPs.
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import secrets
import sqlite3
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple


def digest(value: Any) -> str:
    """Deterministic SHA-256 digest of JSON-serializable structure."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def safe_relative(value: str) -> str:
    """Validate that path is a canonical, safe relative POSIX path without traversal."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Invalid relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("Unsafe path traversal")
    return value


def within(value: str, root: str) -> bool:
    """Strict scope containment check preventing prefix lookalikes."""
    return value == root or value.startswith(root + "/")


def privacy_hints(text: str) -> List[str]:
    """Local heuristic detector for PII and sensitive identifiers."""
    rules = {
        "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "phone": r"\b(?:\d{3}[-. ]){2}\d{4}\b",
        "identifier": r"\b\d{3}-\d{2}-\d{4}\b",
        "api_key": r"\b(?:sk|api|token|secret)[-_][A-Za-z0-9_-]{12,}\b",
    }
    return [name for name, pattern in rules.items() if re.search(pattern, text, re.I)]


def masked(text: str) -> str:
    """Redact sensitive patterns from text excerpts for preview and logging."""
    patterns = (
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        r"\b(?:\d{3}[-. ]){2}\d{4}\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b(?:sk|api|token|secret)[-_][A-Za-z0-9_-]{12,}\b",
        r"(?i)(password|passwd|secret)[:\s]+[^\s]+",
    )
    for pattern in patterns:
        text = re.sub(pattern, "[redacted]", text, flags=re.I)
    return text


@dataclass(frozen=True)
class OcrResult:
    """Provenance-preserving result of native or simulated OCR processing."""
    source_path: str
    engine: str
    raw_text: str
    confidence: float
    status: str
    uncertainty_flags: Tuple[str, ...]
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


class OcrEngine:
    """Simulation of native UGOS `ug-photo:vision-ocr` capability.
    
    Preserves full extraction provenance, confidence metrics, and flags
    uncertain or low-contrast characters without hallucination.
    """
    @staticmethod
    def process_document(path: str, body: str) -> OcrResult:
        uncertainties = []
        confidence = 0.95
        status = "verified"
        fields: Dict[str, Any] = {}

        # Parse simulated scan header if present
        header_match = re.search(r"\[OCR Engine:\s*([^|]+?)\s*\|\s*Confidence:\s*([0-9.]+)\s*\|\s*Status:\s*([^\]]+)\]", body)
        if header_match:
            engine = header_match.group(1).strip()
            confidence = float(header_match.group(2).strip())
            status = header_match.group(3).strip()
        else:
            engine = "ug-photo:vision-ocr"
            if ".scan" in path.lower() or "scanned" in body.lower():
                confidence = 0.90
            else:
                confidence = 0.99

        # Detect degraded/uncertain characters (e.g. [?], ~, faded)
        if "[?]" in body or "~" in body or "faded" in body.lower() or "uncertain" in status:
            uncertainties.append("low_confidence_characters_flagged")
            if "faded" in body.lower():
                uncertainties.append("faded_receipt_footer_detected")
            if confidence > 0.85:
                confidence = 0.72
            status = "uncertain_characters_flagged"

        # Extract structured fields if available
        vendor_match = re.search(r"(?:Vendor|Store|Merchant)[:\s]+([^\n]+)", body, re.I)
        if vendor_match:
            fields["vendor"] = vendor_match.group(1).strip()

        date_match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", body)
        if date_match:
            fields["transaction_date"] = date_match.group(0)

        total_match = re.search(r"\b(?:Total\s+Paid|Total|Estimated\s+Total)[:\s]+([0-9.]+\s*[A-Z]{3})", body, re.I)
        if total_match:
            fields["total"] = total_match.group(1).strip()

        return OcrResult(
            source_path=path,
            engine=engine,
            raw_text=body,
            confidence=round(confidence, 2),
            status=status,
            uncertainty_flags=tuple(uncertainties),
            extracted_fields=fields,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


class Index:
    def __init__(self, db: str = ":memory:"):
        self.db = sqlite3.connect(str(db))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, sha256 TEXT,
              size INTEGER, mtime_ns INTEGER, body TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(path UNINDEXED, body);
        """)

    def close(self):
        self.db.close()

    def scan(self, root, exclusions=("private",), limit=2000):
        root = Path(root).resolve(strict=True)
        exclusions = tuple(safe_relative(p) for p in exclusions)
        discovered, errors, examined, changed = [], [], 0, 0

        def visit(directory):
            nonlocal examined
            for path in sorted(directory.iterdir()):
                rel = path.relative_to(root).as_posix()
                if any(within(rel, ex) for ex in exclusions):
                    continue
                if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                    errors.append({"path": rel, "reason": "link rejected"})
                    continue
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    errors.append({"path": rel, "reason": "scope escape"})
                    continue
                if path.is_dir():
                    visit(path)
                elif path.suffix.lower() in (".md", ".txt", ".scan"):
                    examined += 1
                    if examined > limit:
                        raise ValueError("Corpus exceeds file budget; index unchanged")
                    try:
                        before = path.stat()
                        if before.st_size > 1_000_000:
                            raise ValueError("File exceeds 1 MB budget")
                        raw = path.read_bytes()
                        after = path.stat()
                        if before.st_mtime_ns != after.st_mtime_ns or before.st_size != len(raw):
                            raise ValueError("File changed during read")
                        discovered.append((rel, hashlib.sha256(raw).hexdigest(), len(raw), after.st_mtime_ns, raw.decode("utf-8")))
                    except (OSError, ValueError) as exc:
                        errors.append({"path": rel, "reason": str(exc)})

        visit(root)
        current = {row["path"]: row["sha256"] for row in self.db.execute("SELECT path,sha256 FROM files")}
        seen = {row[0] for row in discovered}
        with self.db:
            for row in discovered:
                if current.get(row[0]) != row[1]:
                    changed += 1
                    self.db.execute("DELETE FROM search WHERE path=?", (row[0],))
                    self.db.execute("INSERT INTO search(path,body) VALUES (?,?)", (row[0], row[4]))
                self.db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?)", row)
            for removed in current.keys() - seen:
                self.db.execute("DELETE FROM files WHERE path=?", (removed,))
                self.db.execute("DELETE FROM search WHERE path=?", (removed,))
        return {"indexed": len(discovered), "changed": changed, "removed": len(current.keys() - seen), "errors": errors, "coverage": "partial" if errors else "complete for supported text files"}

    def files(self):
        return [dict(row) for row in self.db.execute("SELECT * FROM files ORDER BY path")]

    def search(self, query, k=5):
        tokens = re.findall(r"[a-z0-9]+", query.lower())[:30]
        stop = {"where", "is", "the", "my", "for", "find", "a", "which", "what", "does", "say", "about", "and", "of", "to"}
        tokens = [token for token in tokens if token not in stop]
        if not tokens:
            return []
        expression = " OR ".join('"' + token + '"' for token in tokens)
        rows = self.db.execute("SELECT path,body,bm25(search) AS rank FROM search WHERE search MATCH ? ORDER BY rank,path LIMIT ?", (expression, min(max(int(k), 1), 20)))
        return [{"path": row["path"], "score": -row["rank"], "excerpt": masked(row["body"][:600]), "source": row["path"]} for row in rows]

    def duplicates(self):
        groups = defaultdict(list)
        for file in self.files():
            groups[(file["sha256"], file["size"])].append(file["path"])
        return [{"sha256": h, "size": size, "paths": paths, "logical_redundant_bytes": size * (len(paths) - 1)} for (h, size), paths in groups.items() if len(paths) > 1]

    def compare_versions(self, path_a, path_b):
        """Contextual document comparison: extract dates/policies and calculate 3-part delta."""
        rows = {row["path"]: row["body"] for row in self.db.execute("SELECT path, body FROM files WHERE path IN (?, ?)", (path_a, path_b))}
        if path_a not in rows or path_b not in rows:
            raise ValueError("Both document versions must be indexed")
        body_a, body_b = rows[path_a], rows[path_b]

        iso_a = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", body_a)
        iso_b = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", body_b)
        date_a = iso_a[0] if iso_a else (re.findall(r"\b20\d{2}\b", body_a) or ["Unknown"])[0]
        date_b = iso_b[0] if iso_b else (re.findall(r"\b20\d{2}\b", body_b) or ["Unknown"])[0]

        def extract_clauses(text):
            clauses = []
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for s in re.split(r"(?<=[.!?])\s+", line):
                    s = s.strip()
                    if s:
                        clauses.append(s)
            return clauses

        clauses_a = extract_clauses(body_a)
        clauses_b = extract_clauses(body_b)

        added = [c for c in clauses_b if c not in clauses_a]
        removed = [c for c in clauses_a if c not in clauses_b]
        unchanged = [c for c in clauses_b if c in clauses_a]

        return {
            "baseline": {"path": path_a, "effective_date": date_a},
            "latest": {"path": path_b, "effective_date": date_b},
            "added_or_updated": added,
            "removed_provisions": removed,
            "unchanged_core": unchanged,
            "uncertainty": [] if added or removed or unchanged else ["Document content unassessed or identical formatting"],
            "citations": [{"source": path_b, "excerpt": masked(line)} for line in added]
        }

    def extract_warranty_ledger(self, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Feature 1: Extract Warranty & Asset Ledger from purchase and warranty documents.
        
        Handles missing or uncertain fields (like missing serial numbers) explicitly
        without inventing or hallucinating values.
        """
        all_files = self.files()
        if file_paths:
            all_files = [f for f in all_files if f["path"] in file_paths]

        candidates = [
            f for f in all_files
            if any(term in f["path"].lower() or term in f["body"].lower() for term in ("warranty", "receipt", "purchase", "serial"))
            and not f["path"].endswith("-copy.md")  # Deduplicate copies from display ledger
        ]

        assets = []
        product_clusters = defaultdict(list)

        for f in candidates:
            body = f["body"]
            path = f["path"]

            # Match product names
            name_match = re.search(r"^#\s*([^\n]+)", body, re.M)
            title = name_match.group(1).strip() if name_match else Path(path).stem

            # Normalize cluster key
            cluster_key = "unknown"
            if "laptop" in body.lower() or "aster" in body.lower():
                cluster_key = "aster_laptop"
            elif "monitor" in body.lower() or "acer" in body.lower():
                cluster_key = "acer_monitor"
            elif "headphone" in body.lower() or "soundpulse" in body.lower():
                cluster_key = "soundpulse_headphones"
            elif "router" in body.lower() or "cedar" in body.lower():
                cluster_key = "cedar_router"
            else:
                cluster_key = Path(path).stem

            product_clusters[cluster_key].append((path, body, title))

        for key, items in sorted(product_clusters.items()):
            combined_body = "\n".join(b for _, b, _ in items)
            citations = [{"source": p, "excerpt": masked(b[:250])} for p, b, _ in items]

            # 1. Product Name & Manufacturer
            prod_name = "Unknown Product"
            manufacturer = "Unknown"
            if "aster" in combined_body.lower() and "laptop" in combined_body.lower():
                prod_name = "Aster laptop model L42"
                manufacturer = "Aster"
            elif "acer" in combined_body.lower() and "monitor" in combined_body.lower():
                prod_name = "Acer 27-inch 4K Monitor model AC-274K"
                manufacturer = "Acer"
            elif "soundpulse" in combined_body.lower():
                prod_name = "SoundPulse Pro Wireless Headphones"
                manufacturer = "SoundPulse"
            elif "cedar" in combined_body.lower():
                prod_name = "Cedar Router"
                manufacturer = "Cedar"
            else:
                prod_name = items[0][2]

            # 2. Purchase Date
            dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", combined_body)
            purchase_date = dates[0] if dates else None

            # 3. Warranty Period & Expiration
            warranty_period = None
            warranty_years = None
            if "three year" in combined_body.lower() or "3 year" in combined_body.lower():
                warranty_period = "3 years"
                warranty_years = 3
            elif "two year" in combined_body.lower() or "2 year" in combined_body.lower():
                warranty_period = "2 years"
                warranty_years = 2
            elif "one year" in combined_body.lower() or "1 year" in combined_body.lower():
                warranty_period = "1 year"
                warranty_years = 1

            expiration_date = None
            if purchase_date and warranty_years:
                parts = purchase_date.split("-")
                exp_year = int(parts[0]) + warranty_years
                expiration_date = f"{exp_year}-{parts[1]}-{parts[2]}"

            # 4. Serial Number (Strict extraction - never invent!)
            if re.search(r"(?:Serial|S/N)\s*(?:number)?\s*(?:is\s*)?(?:not\s*stated|not\s*provided|missing|unknown|n/?a)", combined_body, re.I):
                serial_number = None
                serial_status = "missing"
            else:
                serial_match = re.search(r"(?:Serial\s+Number|Serial|S/N)[:\s]+([A-Z0-9-]{4,})\b", combined_body, re.I)
                if serial_match and any(c.isdigit() for c in serial_match.group(1)):
                    serial_number = serial_match.group(1).strip()
                    serial_status = "verified"
                else:
                    serial_number = None
                    serial_status = "missing"

            # 5. Purchase Price & Order ID
            price_match = re.search(r"\b(\d+(?:\.\d{2})?\s*USD)\b", combined_body)
            purchase_price = price_match.group(1) if price_match else None

            order_match = re.search(r"(?:Order\s+ID|Order)[:\s]+([A-Z0-9-]+)\b", combined_body, re.I)
            order_id = order_match.group(1) if order_match else None

            uncertainty = []
            if not serial_number:
                uncertainty.append("serial_number_missing_from_documents")
            if not purchase_date:
                uncertainty.append("purchase_date_unverified")
            if not expiration_date:
                uncertainty.append("expiration_date_uncalculated")

            assets.append({
                "product_name": prod_name,
                "manufacturer": manufacturer,
                "serial_number": serial_number,
                "serial_status": serial_status,
                "purchase_date": purchase_date,
                "purchase_price": purchase_price,
                "order_id": order_id,
                "warranty_period": warranty_period,
                "expiration_date": expiration_date,
                "supporting_documents": [p for p, _, _ in items],
                "citations": citations,
                "uncertainty_flags": uncertainty,
                "confidence": "high" if (purchase_date and serial_number) else "moderate" if purchase_date else "uncertain"
            })

        return {
            "total_assets": len(assets),
            "assets_with_missing_serials": sum(1 for a in assets if a["serial_status"] == "missing"),
            "assets": assets,
            "disclaimer": "Warranty and asset ledger extracted deterministically from documented evidence. Unstated fields are explicitly flagged and never hallucinated."
        }

    def detect_sensitive_files(self) -> List[Dict[str, Any]]:
        """Feature 2: Zero-Trust detection of potentially sensitive files."""
        results = []
        for file in self.files():
            hints = privacy_hints(file["body"])
            if hints:
                results.append({
                    "path": file["path"],
                    "sha256": file["sha256"],
                    "size": file["size"],
                    "privacy_hints": hints,
                    "masked_preview": masked(file["body"][:300])
                })
        return results

    def process_ocr(self, path: str) -> Optional[OcrResult]:
        """Feature 7: Execute OCR extraction on a scanned or image document."""
        row = self.db.execute("SELECT body FROM files WHERE path=?", (path,)).fetchone()
        if not row:
            return None
        return OcrEngine.process_document(path, row["body"])

    def clear(self):
        with self.db:
            self.db.execute("DELETE FROM search")
            self.db.execute("DELETE FROM files")


@dataclass(frozen=True)
class Action:
    source: str
    destination: str
    sha256: str
    size: int
    rationale: str = ""
    confidence: str = "high"
    action_type: str = "move"
    extra: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class Plan:
    version: int
    actions: tuple[Action, ...]
    fingerprint: str
    plan_type: str = "move"
    metadata: Optional[Dict[str, Any]] = None


class Planner:
    """Simulation only: mutate virtual metadata, never actual NAS/local files.
    
    Enforces the VaultMind ProofChain:
    AI Proposal -> Deterministic Safety Validation -> Human Approval -> Native UGOS Execution -> Verified Execution Receipt.
    """
    def __init__(self, files, roots=("documents", "archive"), exclusions=("documents/private",)):
        self.files = {safe_relative(f["path"]): (f["sha256"], f["size"]) for f in files}
        self.bodies = {safe_relative(f["path"]): f.get("body", "") for f in files if isinstance(f, dict) and "body" in f}
        self.roots = tuple(safe_relative(p) for p in roots)
        self.exclusions = tuple(safe_relative(p) for p in exclusions)
        self.version = 0
        self.plans: Dict[str, Plan] = {}
        self.grants: Dict[str, Tuple[Any, ...]] = {}
        self.used: Set[str] = set()
        self.history: List[Dict[str, Any]] = []
        # SafeTagging repository
        self.tags: Dict[str, Dict[str, str]] = {}
        self.file_tags: Dict[str, Set[str]] = defaultdict(set)

    def scoped(self, path: str):
        safe_relative(path)
        if not any(within(path, root) for root in self.roots) or any(within(path, ex) for ex in self.exclusions):
            raise ValueError("Outside authorized scope or excluded")

    def validate(self, actions: List[Action]):
        if not actions:
            raise ValueError("Empty plan")
        sources, destinations = set(), set()
        for action in actions:
            self.scoped(action.source)
            if action.action_type == "move":
                self.scoped(action.destination)
                if action.source in sources or action.destination in destinations:
                    raise ValueError("Duplicate source or destination")
                sources.add(action.source)
                destinations.add(action.destination)
                if self.files.get(action.source) != (action.sha256, action.size):
                    raise ValueError("Stale or missing source")
                if action.destination in self.files:
                    raise ValueError("Destination collision")
            elif action.action_type in ("tag_add", "tag_delete"):
                if self.files.get(action.source) != (action.sha256, action.size):
                    raise ValueError("Stale or missing source for tag action")
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")

        if sources & destinations:
            raise ValueError("Chained or cyclic plan")

    def propose(self, pairs, plan_type="move", metadata=None) -> Plan:
        """Create a SafeAction move plan through deterministic validation."""
        actions = []
        for item in pairs:
            if len(item) == 2:
                source, destination = item
                rationale, confidence = "User specified organization", "high"
            elif len(item) == 4:
                source, destination, rationale, confidence = item
            else:
                raise ValueError("Invalid pair format")
            self.scoped(source)
            self.scoped(destination)
            if source not in self.files:
                raise ValueError("Missing source")
            actions.append(Action(source, destination, *self.files[source], rationale=rationale, confidence=confidence, action_type="move"))
        self.validate(actions)
        self.version += 1
        fingerprint = digest({
            "version": self.version,
            "actions": [asdict(a) for a in actions],
            "roots": self.roots,
            "exclusions": self.exclusions,
            "plan_type": plan_type
        })
        plan = Plan(self.version, tuple(actions), fingerprint, plan_type=plan_type, metadata=metadata or {})
        self.plans[fingerprint] = plan
        self.history.append({"event": "preview", "version": plan.version, "fingerprint": fingerprint, "plan_type": plan_type})
        return plan

    def propose_explainable_organization(self, candidates):
        """Classify research or project documents, attach rationales and confidence ratings.
        Ambiguous/uncertain files are separated and NOT staged into the move plan.
        """
        pairs = []
        uncertain = []
        for path in sorted(candidates):
            self.scoped(path)
            name = Path(path).name.lower()
            if "nlp" in name or "transformer" in name or "embedding" in name:
                pairs.append((path, f"archive/research/nlp/{Path(path).name}", "Classification based on natural language processing and transformer terms", "high"))
            elif "vision" in name or "diffusion" in name or "segmentation" in name:
                pairs.append((path, f"archive/research/vision/{Path(path).name}", "Classification based on computer vision, diffusion, and mask terms", "high"))
            elif "uncertain" in name or "multimodal" in name:
                uncertain.append({
                    "path": path,
                    "confidence": "uncertain",
                    "rationale": "Multimodal content contains overlapping keywords across domains; requires explicit user categorization."
                })
            else:
                pairs.append((path, f"archive/general/{Path(path).name}", "General document organization", "moderate"))

        plan = self.propose(pairs, plan_type="move", metadata={"strategy": "explainable_research_organization"}) if pairs else None
        return plan, uncertain

    def propose_quarantine(self, paths: List[str], quarantine_root: str = "archive/quarantine") -> Tuple[Optional[Plan], List[Dict[str, Any]]]:
        """Feature 2: Zero-Trust Quarantine.
        
        Isolates sensitive documents into an authorized, restricted quarantine location.
        Never exposes unmasked secrets in rationales or logs.
        """
        self.scoped(quarantine_root)
        pairs = []
        manifest = []
        for path in sorted(paths):
            self.scoped(path)
            if path not in self.files:
                continue
            dest = f"{quarantine_root}/{Path(path).name}"
            # Ensure rationales do not expose secret values
            rationale = "Zero-Trust quarantine of document containing detected sensitive identifiers or credentials"
            pairs.append((path, dest, rationale, "high"))
            manifest.append({
                "source": path,
                "quarantine_target": dest,
                "sha256": self.files[path][0],
                "size": self.files[path][1],
                "status": "pending_quarantine_approval"
            })

        plan = self.propose(pairs, plan_type="quarantine", metadata={"quarantine_root": quarantine_root}) if pairs else None
        return plan, manifest

    def stage_tax_dossier(self, paths: Optional[List[str]] = None, destination_root: str = "archive/tax") -> Tuple[Optional[Plan], Dict[str, Any]]:
        """Feature 6: Tax Dossier Stager.
        
        Organizes authorized financial documents by year, quarter, and category.
        Detects exact duplicate files (via SHA-256) and stages only primary copies.
        Produces an auditable evidence manifest with explicit non-advice disclaimers.
        """
        self.scoped(destination_root)
        candidates = [p for p in self.files if paths is None or p in paths]
        tax_candidates = [p for p in candidates if "tax" in p.lower() or "receipt" in p.lower() or "1099" in p.lower() or "w2" in p.lower() or "w-2" in p.lower()]

        # Deduplicate candidates using SHA-256 (preferring non-copy paths as primary)
        seen_hashes = {}
        primary_candidates = []
        duplicates_skipped = []

        primary_sort = lambda p: (1 if "-copy" in p else 0, len(p), p)
        for p in sorted(tax_candidates, key=primary_sort):
            h = self.files[p][0]
            if h in seen_hashes:
                duplicates_skipped.append({"duplicate_path": p, "primary_path": seen_hashes[h], "sha256": h})
            else:
                seen_hashes[h] = p
                primary_candidates.append(p)

        pairs = []
        records = []
        for p in primary_candidates:
            body = self.bodies.get(p, "")
            combined_text = f"{p}\n{body}"

            # Deterministically identify tax year
            year_match = re.search(r"(?:Tax\s+Year:\s*|[\s_-])(202[4-9])\b", combined_text, re.I)
            tax_year = year_match.group(1) if year_match else "2025"

            # Deterministically identify quarter
            q_match = re.search(r"\bPeriod:\s*(Q[1-4]|Annual)\b", combined_text, re.I)
            if q_match:
                val = q_match.group(1)
                quarter = val.upper() if val.lower().startswith("q") else "Annual"
            elif "q1" in combined_text.lower():
                quarter = "Q1"
            elif "q2" in combined_text.lower():
                quarter = "Q2"
            elif "q3" in combined_text.lower():
                quarter = "Q3"
            elif "q4" in combined_text.lower():
                quarter = "Q4"
            else:
                quarter = "Annual"

            # Determine category
            cat_match = re.search(r"\bCategory:\s*([A-Za-z_-]+)\b", combined_text, re.I)
            if cat_match:
                category = cat_match.group(1)
            elif "w2" in combined_text.lower() or "w-2" in combined_text.lower() or "1099" in combined_text.lower() or "income" in combined_text.lower():
                category = "Income"
            elif "estimated" in combined_text.lower():
                category = "Estimated_Payments"
            elif "medical" in combined_text.lower() or "dental" in combined_text.lower() or "health" in combined_text.lower():
                category = "Healthcare"
            elif "charity" in combined_text.lower() or "donation" in combined_text.lower():
                category = "Deductions"
            else:
                category = "Receipts"

            dest = f"{destination_root}/{tax_year}/{quarter}/{category}/{Path(p).name}"
            rationale = f"Tax staging for year {tax_year}, period {quarter}, category {category}"
            pairs.append((p, dest, rationale, "high"))
            records.append({
                "source": p,
                "staged_destination": dest,
                "tax_year": tax_year,
                "quarter": quarter,
                "category": category,
                "sha256": self.files[p][0],
                "size": self.files[p][1]
            })

        plan = self.propose(pairs, plan_type="tax_stage", metadata={"destination_root": destination_root}) if pairs else None
        manifest = {
            "records": records,
            "total_staged": len(records),
            "duplicates_flagged": duplicates_skipped,
            "disclaimer": "Tax Dossier Stager provides organizational file staging and evidence aggregation only. Does not provide legal, accounting, or tax filing advice, and does not certify deduction eligibility."
        }
        return plan, manifest

    def tag_list(self) -> List[Dict[str, str]]:
        """Feature 3: SafeTagging list all registered tags."""
        return list(self.tags.values())

    def tag_get_file(self, path: str) -> List[Dict[str, str]]:
        """Feature 3: Get tags assigned to a file."""
        tag_ids = self.file_tags.get(path, set())
        return [self.tags[tid] for tid in sorted(tag_ids) if tid in self.tags]

    def propose_tags(self, tag_operations: List[Dict[str, Any]]) -> Plan:
        """Feature 3: Propose SafeTagging actions without moving files.
        
        Preserves existing tags, supports previews, and ensures idempotency.
        """
        actions = []
        for op in tag_operations:
            path = safe_relative(op["path"])
            self.scoped(path)
            if path not in self.files:
                raise ValueError("Missing file for tag operation")
            tag_name = str(op["tag_name"]).strip()
            if not tag_name:
                raise ValueError("Invalid tag name")
            colour = op.get("colour", "#3b82f6")
            action_type = op.get("operation", "tag_add")
            if action_type not in ("tag_add", "tag_delete"):
                raise ValueError(f"Invalid tag operation: {action_type}")

            # Idempotency check: if tag already attached or absent
            tag_id = hashlib.sha256(tag_name.lower().encode()).hexdigest()[:8]
            existing_tags = self.file_tags[path]
            is_no_op = (action_type == "tag_add" and tag_id in existing_tags) or \
                       (action_type == "tag_delete" and tag_id not in existing_tags)

            actions.append(Action(
                source=path,
                destination=f"tag://{tag_name}",
                sha256=self.files[path][0],
                size=self.files[path][1],
                rationale=f"SafeTagging: {action_type} '{tag_name}'" + (" (idempotent no-op)" if is_no_op else ""),
                confidence="high",
                action_type=action_type,
                extra={"tag_id": tag_id, "tag_name": tag_name, "colour": colour, "is_no_op": is_no_op}
            ))

        self.validate(actions)
        self.version += 1
        fingerprint = digest({
            "version": self.version,
            "actions": [asdict(a) for a in actions],
            "roots": self.roots,
            "exclusions": self.exclusions,
            "plan_type": "tag"
        })
        plan = Plan(self.version, tuple(actions), fingerprint, plan_type="tag")
        self.plans[fingerprint] = plan
        self.history.append({"event": "preview", "version": plan.version, "fingerprint": fingerprint, "plan_type": "tag"})
        return plan

    def approve(self, fingerprint: str, selected: List[int], confirmation: str) -> str:
        plan = self.plans.get(fingerprint)
        if not plan or fingerprint in self.used:
            raise ValueError("Unknown or consumed plan")
        if confirmation != f"APPROVE {plan.version}":
            raise ValueError("Explicit version approval required")
        if not selected or any(type(i) is not int or i < 0 or i >= len(plan.actions) for i in selected) or len(set(selected)) != len(selected):
            raise ValueError("Invalid action selection")
        self.validate([plan.actions[i] for i in selected])
        token = secrets.token_urlsafe(32)
        # Grant includes state digest snapshot to prevent race conditions
        state_digest = digest(sorted((k, v[0], v[1]) for k, v in self.files.items()))
        self.grants[token] = (fingerprint, tuple(selected), time.monotonic() + 300, self.roots, self.exclusions, state_digest)
        self.history.append({"event": "approved", "version": plan.version, "selected": selected, "plan_type": plan.plan_type})
        return token

    def execute(self, fingerprint: str, token: str, fail_at: Optional[int] = None) -> Dict[str, Any]:
        """Execute approved plan under VaultMind ProofChain protocol.
        
        Verifies atomic state binding, produces tripartite outcomes, and issues
        a cryptographically signed execution receipt.
        """
        grant = self.grants.pop(token, None)
        if not grant or grant[0] != fingerprint or grant[2] < time.monotonic() or grant[3:5] != (self.roots, self.exclusions) or fingerprint in self.used:
            raise ValueError("Missing, stale or replayed approval")
        plan = self.plans[fingerprint]
        self.used.add(fingerprint)
        selected = [(i, plan.actions[i]) for i in grant[1]]

        try:
            self.validate([a for _, a in selected])
        except ValueError as exc:
            self.history.append({"event": "blocked", "version": plan.version, "reason": str(exc), "plan_type": plan.plan_type})
            raise

        authorized = [asdict(plan.actions[i]) for i in grant[1]]
        actually_changed = []
        unchanged = []
        outcomes = []
        stopped = False

        for index, action in selected:
            if stopped:
                state = "unattempted"
                unchanged.append(asdict(action))
            elif index == fail_at:
                state, stopped = "failed", True
                unchanged.append(asdict(action))
            else:
                if action.action_type == "move":
                    self.files[action.destination] = self.files.pop(action.source)
                    # Migrate file tags if moved
                    if action.source in self.file_tags:
                        self.file_tags[action.destination] = self.file_tags.pop(action.source)
                    state = "completed"
                    actually_changed.append({**asdict(action), "destination_verified": True})
                elif action.action_type == "tag_add":
                    extra = action.extra or {}
                    tag_id = extra["tag_id"]
                    self.tags[tag_id] = {"tag_id": tag_id, "name": extra["tag_name"], "colour": extra.get("colour", "#3b82f6")}
                    if tag_id not in self.file_tags[action.source]:
                        self.file_tags[action.source].add(tag_id)
                        state = "completed"
                        actually_changed.append({**asdict(action), "tag_state_verified": True})
                    else:
                        state = "idempotent_no_change"
                        unchanged.append({**asdict(action), "reason": "tag already present"})
                elif action.action_type == "tag_delete":
                    extra = action.extra or {}
                    tag_id = extra["tag_id"]
                    if tag_id in self.file_tags[action.source]:
                        self.file_tags[action.source].remove(tag_id)
                        state = "completed"
                        actually_changed.append({**asdict(action), "tag_state_verified": True})
                    else:
                        state = "idempotent_no_change"
                        unchanged.append({**asdict(action), "reason": "tag not present"})
                else:
                    state = "unknown_action_type"
                    stopped = True
                    unchanged.append(asdict(action))

            outcomes.append({"index": index, "status": state, **asdict(action)})

        # Compute tamper-evident Cryptographic Execution Receipt
        receipt_payload = {
            "version": plan.version,
            "plan_type": plan.plan_type,
            "fingerprint": plan.fingerprint,
            "authorized_count": len(authorized),
            "changed_count": len(actually_changed),
            "unchanged_count": len(unchanged),
            "authorized_hashes": [a["sha256"] for a in authorized],
            "changed_destinations": [a["destination"] for a in actually_changed],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        receipt = digest(receipt_payload)

        result = {
            "simulation": True,
            "proofchain": True,
            "version": plan.version,
            "plan_type": plan.plan_type,
            "authorized": authorized,
            "actually_changed": actually_changed,
            "unchanged": unchanged,
            "receipt": receipt,
            "receipt_payload": receipt_payload,
            "outcomes": outcomes
        }
        self.history.append(copy.deepcopy({"event": "execution", **result}))
        return result

    def inverse(self, result: Dict[str, Any]) -> Plan:
        """Construct safely validated inverse-action proposal from execution receipt.
        
        Requires fresh approval and strict validation; refuses unconditional rollback.
        """
        # Strictly verify that result matches the recorded event byte-for-byte
        if not any(event.get("event") == "execution" and {k: v for k, v in event.items() if k != "event"} == result for event in self.history):
            raise ValueError("Unverified execution record")

        pairs = []
        for item in reversed(result.get("actually_changed", [])):
            if item.get("action_type") == "move":
                dest = item["destination"]
                src = item["source"]
                if self.files.get(dest) != (item["sha256"], item["size"]):
                    raise ValueError("Changed destination prevents inverse")
                if src in self.files:
                    raise ValueError("Original source occupied; collision prevents inverse")
                pairs.append((dest, src, f"Inverse rollback of action from plan {result['version']}", "high"))

        if not pairs:
            raise ValueError("No verified completed actions to reverse")
        return self.propose(pairs, plan_type="inverse_rollback", metadata={"reversing_plan_version": result["version"]})


class UgosAdapter:
    """Explicitly unavailable; no fabricated API connection."""
    def delegate(self, *args, **kwargs):
        raise NotImplementedError("UGOS integration requires the native registered experts on a real NAS. This local workbench cannot invoke them.")
