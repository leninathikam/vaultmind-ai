# Competition requirements

Verified 2026-10-28. Sources: [overview](https://ugreenhackathon.devpost.com/), [rules](https://ugreenhackathon.devpost.com/rules), [resources](https://ugreenhackathon.devpost.com/resources), [starter kit](https://ai.ugreen.com/pages/hackathon-starter-kit).

## Rules checklist

- [x] Develop a new Skill during the event using the official creation tool (rules §4).
- [x] Markdown orchestration through registered experts; no custom runtime or manifest (§4).
- [x] Provide ten proposal responses, at most 500 English words (§4).
- [x] Include an initial ZIP; NAS execution is unnecessary for Round 1 (§4).
- [ ] Entrant verifies age, residence, ownership and team eligibility (§3-4).
- [ ] Entrant submits by November 15, 2026, 11:45 p.m. Pacific: November 16, 2:45 a.m. Eastern (§1).
- [ ] If selected, validate on the assigned NAS day and submit Round 2 by November 30, 11:45 p.m. Pacific (§1,4).

Judging: equal weight for user value, differentiation, technical quality, and AI NAS fit/validation (§6). Rules prevail over conflicting publicity (§11).

## Overview checklist

- [x] Proposal PDF below 1 MB; separate from ZIP.
- [x] ZIP and extracted package below 10 MB; each file below 1 MB; fewer than 100 files.
- [x] Entry point has name and description; supporting Markdown is linked directly.
- [x] Disclose AI assistance, original work, third-party sources and licenses.
- [x] No credentials, personal data, scripts or binary assets in Skill ZIP.

AI assistance is contemplated by the starter kit, which names Codex. The overview expressly requests AI-tool disclosure. This is not a substitute for entrant review and accurate authorship declarations.

The resources FAQ explicitly permits AI assistants with disclosure, while recommending that entrants write proposal answers in their own voice. The generated PDF is therefore prepared for the entrant's review and personalization. This recommendation is not an AI-use prohibition. The publication standards also prohibit searching credential/system material; VaultMind makes those mandatory exclusions in addition to user-selected private folders.

## Official package inspection

Downloaded [uliya-skill-kit-0.7.3-en.zip](https://cdn.shopify.com/s/files/1/0630/9416/1602/files/uliya-skill-kit-0.7.3-en.zip?v=1790578898).
SHA-256: `cf557e5a022e4297892f39768132855154232efdedeb726b2845450ccd70e1b3`.
Local evidence: `vendor/official/uliya-skill-kit/`; catalog version 2.0.0, generated 2026-09-01.

The inspected kit provides a Node static checker, a capability catalog and authoring instructions. It does not install Skills or emulate a NAS. Its standard identifies SKILL.md as the runtime entry point, only name/description frontmatter, and optional linked Markdown references. No permission manifest is defined. The parent delegates; registered experts enforce their own Registry, gateway approvals, validation and audit.

`ug-document/qa` explicitly supports `semantic_lookup`, `comparison`, and `summary`; `ug-filesystem/sha256sum` supports exact-hash evidence; `ug-filemgr/scan-dedupe` supports discovery. `ug-filesystem/cpmv` is a gateway-approved state change. `ug-knowledge/save-text` is workflow-approved. Catalog permissions, prerequisites, stability and error-code details are often marked unknown; some translated descriptions are incomplete. Do not infer stronger guarantees.

No catalog capability installs Sentence Transformers, FAISS, SQLite, custom Python services, embedding models, or a management website. No model-selection, resource-inspection or incremental-index administration API is published. VaultMind therefore uses platform document reasoning and bounded fresh discovery. Model locality must be verified on the target device before processing private content; no cloud fallback is authorized by this Skill.

## Verification evidence

See `artifacts/official-check.json`, `artifacts/test-results.txt`, `artifacts/benchmark.json`, and `artifacts/release.json` after running the documented build. Static compliance and synthetic experiments do not establish NAS compatibility. Installation, model locality, runtime permissions, exclusion enforcement, actual approval binding, recovery and performance require target-device validation.

## Research availability

The configured session has no DevRelay gateway tools. Community article/comment research was unavailable; no community claims or citations were invented. Official kit and competition sources determine this implementation.
