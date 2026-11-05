# Sources, originality and limitations

VaultMind AI was newly authored for the UGREEN Hackathon on 2026-10-28. Principal original functionality: evidence-to-action workflow, bounded privacy-aware review, version-specific approval protocol, stale-evidence rejection requirements and guarded inverse planning. No prior Skill was reused as the core workflow.

AI assistance: OpenAI Codex researched official resources, authored and revised the orchestration and supporting documentation, and created local tests, synthetic fixtures, a review workbench and proposal materials. The entrant must review accuracy, ownership and final submission declarations. No human team identity or signature is supplied by the agent.

Authoring dependency: UGREEN uliya-skill-kit 0.7.3, catalog 2.0.0, from the [official starter kit](https://ai.ugreen.com/pages/hackathon-starter-kit). Used as documentation and a static checker. The kit is not bundled in this Skill. Its use is governed by UGREEN terms; no permissive open-source license was found in the downloaded archive.

Runtime dependencies: platform-provided file-agent, document-agent, knowledge-agent, and photo-agent, and their catalog capabilities. Governed by UGREEN platform terms. The package includes original Markdown only; it embeds no third-party libraries, model weights, datasets or executable code. No external service or data-transfer destination is configured.

Local development tools, outside this package: Python standard library (PSF license), SQLite (public domain), Node.js (MIT and bundled third-party notices), ReportLab (BSD), and PDF inspection dependencies as recorded in the repository. No library code is redistributed inside the Skill.

Not claimed: successful NAS installation, device execution, guaranteed model locality, custom indexing, an embedding store, automatic model selection, immutable audit storage, universal rollback or complete privacy detection. Supported semantic lookup is delegated to the document expert; measured model quality awaits NAS access. The separately labeled local workbench uses lexical retrieval and simulated file actions, not UGOS execution.

See the [competition overview](https://ugreenhackathon.devpost.com/) and [rules](https://ugreenhackathon.devpost.com/rules) for submission requirements. This Skill is independently developed and is not an official UGREEN product.
