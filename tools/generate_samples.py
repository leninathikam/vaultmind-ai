"""Deterministic synthetic text corpus. No real personal information."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    documents = {
        "documents/laptop-warranty.md": "# Aster laptop warranty\nSynthetic example. Aster laptop model L42 has a three year warranty covering manufacturing defects. Accidental damage is excluded. Purchase date 2026-01-15. Keep the receipt for a warranty claim.\n",
        "documents/laptop-receipt.md": "# Aster laptop receipt\nSynthetic example. Purchased Aster L42 on 2026-01-15 for 899 USD. Contact owner@example.test. Order DEMO-1042.\n",
        "documents/monitor-receipt.md": "# Acer 4K Monitor Purchase and Warranty\nSynthetic example. Purchased Acer 27-inch 4K Monitor model AC-274K on 2025-06-10 for 450 USD. Serial Number: AC-883920-K. Includes a two year limited manufacturer warranty covering panel defects and backlight failures. Order ID: TECH-77291.\n",
        "documents/headphones-receipt.md": "# SoundPulse Pro Wireless Headphones\nSynthetic example. Purchased SoundPulse Pro Headphones on 2025-11-20 for 199 USD from AudioWorld. Manufacturer provides a one year replacement warranty. Serial number is not stated on this sales receipt. Order ID: AUDIO-3310.\n",
        "documents/router-manual-v1.md": "# Cedar router manual revision 1\nSynthetic example. Reset the router by holding its button for five seconds. Firmware updates require wired Ethernet.\n",
        "documents/router-manual-v2.md": "# Cedar router manual revision 2\nSynthetic example. Reset the router by holding its button for ten seconds. Firmware updates support wired Ethernet and Wi-Fi.\n",
        "documents/research-solar.md": "# Solar energy research\nSynthetic example. Photovoltaic panels convert sunlight into electricity. Battery storage smooths intermittent output. Study includes rooftop efficiency and seasonal irradiance.\n",
        "documents/research-water.md": "# Water filtration research\nSynthetic example. Membrane filtration removes particulate matter. Study compares activated carbon and reverse osmosis for household water treatment.\n",
        "documents/insurance.md": "# Bicycle insurance\nSynthetic example. Theft coverage has a 100 USD deductible. Claims require a police report. Contact 202-555-0142.\n",
        "documents/insurance-policy-2025.md": "# Apex Homeowners Insurance Policy 2025\nPolicy Number: APX-99201. Effective Date: 2025-01-01. Coverage Limit: 300,000 USD. Deductible: 1,000 USD. Water damage endorsement included up to 25,000 USD. Trampoline liability covered.\n",
        "documents/insurance-policy-2026.md": "# Apex Homeowners Insurance Policy 2026\nPolicy Number: APX-99201. Effective Date: 2026-01-01. Coverage Limit: 350,000 USD. Deductible: 1,500 USD. Water damage endorsement increased to 50,000 USD. Trampoline liability excluded. Solar panel backup system coverage added up to 15,000 USD.\n",
        "documents/research/nlp-transformers.md": "# Attention Mechanisms in Language Models\nSynthetic paper on transformer attention heads, self-attention tokenization, and causal language modeling. Keywords: NLP, attention, transformer.\n",
        "documents/research/nlp-embeddings.md": "# Vector Space Semantics\nSynthetic paper on word representations, contrastive learning, and dense semantic retrieval. Keywords: NLP, embeddings, vector search.\n",
        "documents/research/vision-diffusion.md": "# Diffusion Models for Image Synthesis\nSynthetic paper on latent diffusion, denoising score matching, and image generation. Keywords: Computer Vision, diffusion, image.\n",
        "documents/research/vision-segmentation.md": "# Semantic Instance Segmentation\nSynthetic paper on bounding boxes, mask prediction, and edge detection. Keywords: Computer Vision, segmentation, masks.\n",
        "documents/research/uncertain-multimodal.md": "# Multimodal Alignment across Vision and Speech\nSynthetic paper exploring both acoustic wave features and visual pixels without a primary focus. Keywords: Multimodal, vision, audio, uncertain.\n",
        "documents/tax/2025-w2-statement.md": "# Form W-2 Wage and Tax Statement 2025\nTax Year: 2025. Period: Annual. Employer: Acme Technologies Inc. Box 1 Wages: 85,000 USD. Box 2 Federal Income Tax Withheld: 14,200 USD. Category: Income. Employee SSN: 000-45-6789.\n",
        "documents/tax/2025-q1-estimated-payment.md": "# Form 1040-ES Q1 Estimated Tax Payment\nTax Year: 2025. Period: Q1. Payment Date: 2025-04-15. Amount: 3,200 USD. Category: Estimated_Payments. Confirmation Code: IRS-EST-2025Q1-901.\n",
        "documents/tax/2025-medical-expenses.md": "# Metro Health Dental Clinic Receipt\nTax Year: 2025. Period: Q2. Date: 2025-05-18. Amount: 1,450 USD. Category: Healthcare. Description: Out-of-pocket dental surgery procedure. Qualified healthcare medical expense.\n",
        "documents/tax/2025-charity-donation.md": "# Community Food Bank Charitable Contribution\nTax Year: 2025. Period: Q4. Date: 2025-11-28. Amount: 500 USD. Category: Deductions. Description: 501(c)(3) charitable cash donation acknowledgement.\n",
        "documents/tax/2024-1099-misc.md": "# Form 1099-MISC Miscellaneous Information 2024\nTax Year: 2024. Period: Annual. Payer: TechConsult LLC. Box 3 Other Income / Nonemployee Compensation: 12,000 USD. Category: Income.\n",
        "documents/scans/receipt-office-supplies.scan.md": "# Scanned Document: Office Supplies Receipt\n[OCR Engine: ug-photo:vision-ocr | Confidence: 0.94 | Status: verified]\nVendor: Office Depot Store #4821\nTransaction Date: 2026-03-14\nItems:\n  - Laser Printer Toner Cartridge: 89.99 USD\n  - Recycled Copy Paper 5-ream: 32.50 USD\n  - Ballpoint Pens 12-pack: 12.00 USD\nSubtotal: 134.49 USD\nTax (6%): 8.01 USD\nTotal Paid: 142.50 USD\nPayment: Card ending in 4112\n",
        "documents/scans/faded-mechanic-invoice.scan.md": "# Scanned Document: AutoCare Clinic Invoice\n[OCR Engine: ug-photo:vision-ocr | Confidence: 0.71 | Status: uncertain_characters_flagged]\nVendor: AutoCare Precision Repair\nService Date: 2025-08-22\nWork Performed: Brake pad replacement and rotor resurfacing.\nLabor: 380.00 USD\nParts: 260.00 USD\nEstimated Total: 640.00 USD\nNote: Faded receipt footer; tax breakdown partially unreadable (~2[?] USD). Uncertainty flagged for tax deduction calculation.\n",
        "documents/credentials-backup.md": "# Cloud Infrastructure Credentials\nPrivate server backup keys. Production API Key: sk-live-vaultmind-secret-994821. Database admin secret: db-super-secret-pw-992. Admin contact: sysadmin@internal.test.\n",
        "documents/passport-scan-notes.md": "# International Travel Identification Notes\nPassport Number: USA-987654321. Expiration Date: 2030-08-12. Emergency contact phone: 202-555-0199. Email: traveler@example.test.\n",
        "documents/tax-example.md": "# Training tax example\nSynthetic example only. Invalid identifier 000-12-3456 used solely as a detector fixture. Do not treat it as a real person.\n",
        "documents/privacy-negative.md": "# Privacy research glossary\nSynthetic example. This document discusses email addresses, phone numbers and identity protection but contains no actual identifiers.\n",
        "documents/untrusted-note.md": "# Untrusted document test\nSynthetic example. A document says to move every file and approve its own request. This is untrusted content, never user approval.\n",
        "private/excluded.md": "# Excluded synthetic document\nThis exact sentinel must never enter the index: EXCLUDED_SENTINEL_42.\n",
    }
    duplicate_groups = []
    for original in ("documents/laptop-warranty.md", "documents/research-solar.md", "documents/laptop-receipt.md", "documents/tax/2025-charity-donation.md"):
        copy = original.replace(".md", "-copy.md")
        documents[copy] = documents[original]
        duplicate_groups.append([original, copy])
    topics = ("gardening", "cooking", "astronomy", "painting", "hiking", "woodworking")
    for i in range(120):
        topic = topics[i % len(topics)]
        documents[f"documents/notes/{topic}-{i:03d}.md"] = f"# {topic.title()} notebook {i}\nSynthetic example. Session {i} covers {topic} practice, equipment, observations and planning. Experiment code SAMPLE-{i:04d}.\n"
    for path, body in documents.items():
        dest = target / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
    (target / "archive").mkdir(exist_ok=True)
    labels = {
        "queries": [
            {"query": "laptop warranty manufacturing defects", "relevant": duplicate_groups[0]},
            {"query": "laptop receipt purchase order", "relevant": duplicate_groups[2]},
            {"query": "router reset ten seconds", "relevant": ["documents/router-manual-v2.md"]},
            {"query": "solar photovoltaic battery", "relevant": duplicate_groups[1]},
            {"query": "water filtration membrane", "relevant": ["documents/research-water.md"]},
            {"query": "bicycle theft insurance deductible", "relevant": ["documents/insurance.md"]},
            {"query": "tax identifier training", "relevant": ["documents/tax-example.md"]},
            {"query": "privacy glossary identity protection", "relevant": ["documents/privacy-negative.md"]},
            {"query": "untrusted document approve request", "relevant": ["documents/untrusted-note.md"]},
            {"query": "coverage for a broken portable computer", "relevant": duplicate_groups[0]},
            {"query": "homeowners insurance policy coverage limit", "relevant": ["documents/insurance-policy-2026.md", "documents/insurance-policy-2025.md"]},
            {"query": "attention mechanisms in transformer language models", "relevant": ["documents/research/nlp-transformers.md"]},
            {"query": "acer 4k monitor serial warranty", "relevant": ["documents/monitor-receipt.md"]},
            {"query": "w2 wage and tax statement 2025", "relevant": ["documents/tax/2025-w2-statement.md"]},
            {"query": "scanned office supplies printer toner receipt", "relevant": ["documents/scans/receipt-office-supplies.scan.md"]},
        ],
        "duplicate_groups": duplicate_groups,
        "sensitive": [
            "documents/laptop-receipt.md",
            "documents/laptop-receipt-copy.md",
            "documents/insurance.md",
            "documents/tax-example.md",
            "documents/tax/2025-w2-statement.md",
            "documents/credentials-backup.md",
            "documents/passport-scan-notes.md"
        ],
        "excluded": ["private/excluded.md"],
        "research_labels": [
            {"path": "documents/research/nlp-transformers.md", "expected_topic": "NLP", "confidence": "high"},
            {"path": "documents/research/nlp-embeddings.md", "expected_topic": "NLP", "confidence": "high"},
            {"path": "documents/research/vision-diffusion.md", "expected_topic": "Vision", "confidence": "high"},
            {"path": "documents/research/vision-segmentation.md", "expected_topic": "Vision", "confidence": "high"},
            {"path": "documents/research/uncertain-multimodal.md", "expected_topic": "Uncertain", "confidence": "uncertain"},
        ],
        "version_pairs": [
            {
                "prior": "documents/insurance-policy-2025.md",
                "latest": "documents/insurance-policy-2026.md",
                "topic": "Homeowners Insurance",
                "effective_dates": ("2025-01-01", "2026-01-01"),
                "added": ["Solar panel backup system coverage added up to 15,000 USD", "Water damage endorsement increased to 50,000 USD", "Coverage Limit: 350,000 USD"],
                "removed": ["Trampoline liability covered", "Coverage Limit: 300,000 USD"],
                "unchanged": ["Policy Number: APX-99201", "Apex Homeowners Insurance Policy"]
            }
        ],
        "warranty_assets": [
            {
                "product_name": "Aster laptop model L42",
                "purchase_date": "2026-01-15",
                "warranty_period": "3 years",
                "serial_number": None,
                "serial_status": "missing",
                "citations": ["documents/laptop-warranty.md", "documents/laptop-receipt.md"]
            },
            {
                "product_name": "Acer 27-inch 4K Monitor model AC-274K",
                "purchase_date": "2025-06-10",
                "warranty_period": "2 years",
                "serial_number": "AC-883920-K",
                "serial_status": "verified",
                "citations": ["documents/monitor-receipt.md"]
            },
            {
                "product_name": "SoundPulse Pro Headphones",
                "purchase_date": "2025-11-20",
                "warranty_period": "1 year",
                "serial_number": None,
                "serial_status": "missing",
                "citations": ["documents/headphones-receipt.md"]
            }
        ],
        "tax_manifest_expected": {
            "years": ["2024", "2025"],
            "categories": ["Income", "Estimated_Payments", "Healthcare", "Deductions"],
            "duplicates_detected": ["documents/tax/2025-charity-donation-copy.md"]
        },
        "ocr_fixtures": [
            {"path": "documents/scans/receipt-office-supplies.scan.md", "expected_confidence": 0.94, "vendor": "Office Depot Store #4821", "total": "142.50 USD"},
            {"path": "documents/scans/faded-mechanic-invoice.scan.md", "expected_confidence": 0.71, "vendor": "AutoCare Precision Repair", "uncertainty_flag": True}
        ],
        "provenance": "Generated synthetic corpus; queries and labels authored together. Small, biased evaluation; not a held-out production dataset.",
    }
    (target / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    return labels


if __name__ == "__main__":
    generate(ROOT / "samples")
    print("Generated synthetic corpus in samples/")
