# Validation contract

Local authoring and static checks cannot prove NAS installation or execution. Validate on the assigned device with synthetic fixtures and registered platform experts across core feature domains:

## 1. Warranty & Asset Ledger Validation
- **Structured Extraction**: Test extraction on electronics and appliance purchase documents.
- **Serial Verification & Missing Handling**: Verify that items with explicit serial numbers (e.g. Acer monitor) have `serial_status: verified`, while items lacking serials (e.g. SoundPulse headphones) are explicitly flagged with `serial_status: missing` and uncertainty warnings. Confirm no serial numbers are hallucinated.
- **Expiration Timing**: Verify warranty duration and expiration calculations derived from purchase dates.
- **Citations**: Confirm supporting document citations link directly to purchase receipts and warranty terms.

## 2. Zero-Trust Quarantine & Privacy Isolation
- **Sensitivity Detection**: Test detection of credentials, API keys, passwords, and sensitive identifiers.
- **Approval-First Quarantine**: Verify that quarantine proposals require explicit version approval.
- **Zero Secret Leakage**: Confirm that sensitive strings are strictly masked in preview tables, execution history, and audit receipts.
- **Destination Verification**: Confirm that quarantine folders enforce restricted permissions.

## 3. SafeTagging Workflows
- **Metadata Isolation**: Confirm file tags are applied using native `ug-filemgr` without moving files or altering file hashes.
- **Idempotency**: Test adding an existing tag; confirm the operation is an idempotent no-op that preserves existing file tags.
- **ProofChain Integration**: Verify tag proposals require human approval and produce verified tag execution receipts.

## 4. Cryptographic Execution Receipts & ProofChain
- **Lifecycle Integrity**: Test proposal -> validation -> approval -> serial execution -> cryptographic receipt.
- **Tamper Evidence**: Verify that the execution receipt contains normalized SHA-256 digests over authorized and actually changed sets.
- **Guarded Inverse Rollback**: Verify that inverse plans are generated exclusively for verified changed files, require fresh approval, and reject modified destination files.

## 5. Collision & Symlink Protection
- **Traversal Rejection**: Verify 100% rejection of `../`, `..\\`, absolute paths, symlinks, and Windows directory junctions.
- **Exclusion Precedence**: Verify child exclusion folders and prefix lookalikes are pruned before discovery.
- **Stale Plan Rejection**: Test modifying source file content after preview; confirm execution immediately fails closed.
- **Destination Collision**: Test destination path collision; confirm execution blocks without overwriting.

## 6. Tax Dossier Staging & Duplicate Detection
- **Hierarchical Staging**: Test organization into `archive/tax/{year}/{quarter}/{category}/` structures.
- **Exact Duplicate Deduplication**: Confirm SHA-256 duplicate forms or receipts (e.g. donation slips) stage only primary files while flagging copies as skipped duplicates.
- **Statutory Notice**: Verify the non-advice disclaimer is present in every tax report and manifest.

## 7. Native OCR for Scanned Documents
- **Capability Invocation**: Test invocation of photo-agent `ug-photo:vision-ocr` on receipt and invoice scans.
- **Provenance & Confidence**: Confirm extracted output retains engine identifier, timestamp, and confidence scores (e.g. 0.94 vs 0.71).
- **Uncertainty Flags**: Confirm faded or low-contrast characters are flagged with uncertainty indicators rather than guessed digits.

## 8. Measurable Benchmark Suite
Evaluate system performance across quantitative dimensions:
1. **Retrieval accuracy**: Macro Recall@5 and MRR@5 across standard, synonym, and temporal queries.
2. **Classification quality**: Topic classification precision, recall, and uncertainty calibration on research documents.
3. **Adversarial safety rejection**: 100% rejection across all 10 adversarial attack vectors.
4. **Approval invalidation integrity**: Verification of token revocation upon state modification.
5. **End-to-end task completion**: Success rate across complete discovery-preview-approval-execution-inverse lifecycles.

Never substitute workstation baseline results for NAS model performance. Report observed local measurements separately from unmeasured device properties.
