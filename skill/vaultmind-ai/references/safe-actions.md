# SafeAction Planner & VaultMind ProofChain

This is an orchestration contract, not executable validation code. Enforcement belongs to registered experts and platform gates. If they cannot establish a guard, refuse the write and leave a preview.

## The VaultMind ProofChain Protocol

All mutating or tagging workflows follow an immutable five-stage lifecycle:
1. **AI Proposal**: Generate an explainable, structured plan (move, quarantine, tax stage, or SafeTag) with rationales, citations, and confidence ratings.
2. **Deterministic Safety Validation**: Verify canonical path containment, exclusion precedence, absence of symlinks/junctions, no destination collisions, non-circularity, and current source SHA-256 and size matching.
3. **Human Approval**: Require explicit plan-version approval syntax (e.g. `APPROVE 3: 0, 1`). Binds to the exact cryptographic plan fingerprint and filesystem state snapshot.
4. **Native UGOS Execution**: Verify single-use token, re-validate freshness of source hashes, execute serially one-by-one via platform experts, and halt immediately on first failure.
5. **Verified Execution Receipt**: Produce a cryptographic execution receipt with tripartite outcomes (Authorized, Actually Changed, Unchanged) and tamper-evident SHA-256 digest.

## Plan Record and Workflows

Assign a session-local monotonically increasing plan version. Record goal, authorized roots, exclusions, actor, creation context, coverage and selected evidence.

### 1. Explainable Organization & Tax Dossier Staging
For smart organization (e.g. research papers, project archives, or financial records):
- Action number and operation (`move` or `tax_stage`)
- Source path, proposed destination, SHA-256 and size
- Explicit classification rationale explaining why this document belongs in the proposed destination
- Classification confidence level (`high`, `moderate`, or `uncertain`)
- Source citations (e.g. topic keywords, tax year, quarter, category)
- Collision and path validation checks
- Pre-move snapshot for inverse recovery

Documents with `uncertain` confidence or ambiguous categories are separated into an "Uncertain / Requires Clarification" list. They are never assigned an automated move destination without explicit user direction.

### 2. Zero-Trust Quarantine
For sensitive documents containing credentials, API keys, passwords, or unmasked PII:
- Propose isolating files to an authorized restricted quarantine directory (e.g. `archive/quarantine/`).
- Verify destination access permissions before moving.
- In all previews, logs, and audit entries, mask secret values using standard redaction patterns; never expose raw credentials.

### 3. SafeTagging Workflows
To organize files without altering directory structures:
- Use native `ug-filemgr` tagging commands: `tag-list`, `tag-get-by-name`, `tag-get-file`, `tag-add`, `tag-add-file`, and `tag-delete-file`.
- Discover existing tags on target files before proposing modifications.
- **Idempotency Guarantee**: If a proposed tag is already attached, mark the operation as an idempotent no-op; never duplicate tags.
- Preserves all other tags on the file.
- Moves zero physical files; file hashes and paths remain unchanged.

## Adversarial Safety Invariants

The policy engine rejects all unsafe proposals before presenting them for approval:
1. **Canonical Scope Escape**: Path traversals (`..`, `../`, `..\\`), root escapes, and backslashes are strictly blocked.
2. **Symlink and Junction Traversal**: Symlinks, soft links, and Windows directory junctions are rejected.
3. **Excluded Directory Precedence**: Exclusions override inclusions. Child folders and prefix lookalike names (e.g. `archive-lookalike`) cannot bypass boundaries.
4. **Destination Collision**: Moves target only non-existent paths. Overwrites are strictly prohibited.
5. **Chained / Cyclic Plans**: Intra-plan collisions where a destination is also a source (`A -> B, B -> C`) are rejected.
6. **Stale Source Rejection**: If source file content, size, or hash changes between proposal and execution, execution immediately halts.
7. **Generic Confirmation Rejection**: Generic affirmations ("yes", "ok", "proceed") are rejected; only `APPROVE <version>` is accepted.
8. **Token Expiration and Replay Prevention**: Execution tokens expire after 300 seconds and are permanently consumed upon first use.

## Execution Contract and Tripartite Ledger

1. Re-read source metadata and hash; compare against the reviewed preview evidence. Any mismatch immediately blocks the operation.
2. Independently verify permissions, canonical paths, exclusions and a destination that does not exist. Require platform mechanisms to enforce no overwrite at execution time, not merely a preflight check.
3. Follow current gateway approval and Registry constraints. If atomic conflict handling or identity enforcement is unavailable, retain preview-only status.
4. Move or tag one item at a time. Immediately verify the new path or tag with fresh stat and SHA-256.
5. On error, cancellation or uncertain completion, stop immediately. Fail closed.

Record the execution outcome using a tripartite ledger:
- **Authorized**: Exactly what was approved by the user (plan version, action numbers, verified hashes).
- **Actually Changed**: Verified completed actions with confirmed post-move paths or verified tag states and matching SHA-256 digests.
- **Unchanged**: Unattempted actions (halted after prior error), blocked actions (stale hash or collision), and failed actions.

Generate a structured cryptographic execution receipt recording these three sets.

## Recovery Evidence and Inverse Plans

On a user request to undo, construct a new inverse plan exclusively for items in the verified "Actually Changed" set. Prerequisites for inverse execution:
1. Confirm that each moved file at its current destination has unchanged SHA-256 and size.
2. Confirm that the original source path is currently vacant.
3. Confirm that the original parent directory exists and both paths remain within authorized scope.
4. Present a fresh inverse preview and require a separate explicit approval token (e.g. `APPROVE 4: 0`).

The inverse remains a guarded move, not a guaranteed transaction. If any precondition fails, stop and report manual recovery requirements. Never overwrite or delete content to force a rollback to succeed.

## Audit and Storage Semantics

Record plan version, selected actions, classification rationales, user approval scope, validation failures, tripartite outcomes and inverse-plan links in the visible session. Optional redacted report export is separately approved. Hash duplicates describe content equality, not user intent to remove a copy. Logical redundant bytes equal the sum of non-keeper sizes, but physical reclaimable bytes are unknown; organization moves reclaim zero physical capacity.
