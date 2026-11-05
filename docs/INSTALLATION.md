# Installation and initialization

## Local workstation

Use Python 3.12+ with SQLite FTS5. Run `python tools/generate_samples.py`, then `python -m workbench.server`. Open the loopback URL printed by the server. All sample files are synthetic; the simulator only changes in-memory metadata. Stop the process to reset approvals and simulated activity. The default in-memory index disappears on shutdown. `Index.clear()` removes generated local index rows only, not source files; it is not a secure-erasure guarantee.

## Official authoring tool

The official archive is downloaded and inspected locally under ignored `vendor/`. Its Node checker runs directly without npm dependencies. Its SKILL.md and mandatory references were read and applied when authoring VaultMind. No assistant-wide installation or configuration is necessary for the recorded checks. To integrate the tool in a different assistant session, follow the official starter-kit installation instructions for that assistant.

## UGREEN NAS: pending device verification

Use the finalist connection and installation instructions supplied by UGREEN on the assigned testing day. The downloaded creation kit explicitly does not install Skills or verify runtime behavior. No verified NAS installer command or UI procedure was available in this session; do not substitute a shell script, Docker service or fabricated API.

The pre-test ZIP contains SKILL.md at its root with references beneath it. Confirm accepted archive layout in the actual importer and record any required layout correction as a new release. Import through the supported device workflow, confirm the registered file, document and knowledge experts are present, and confirm the configured model keeps private processing local. Start with the synthetic fixtures only. Select a real authorized source directory, exclude a child folder, and ask for a read-only warranty search. Verify actual citations and coverage before testing approved moves.

Runtime permission declarations are governed by the platform's expert Registry and approval gateway, not a separate manifest. If locality, canonical scope, no-overwrite or source-identity enforcement cannot be established, keep affected operations blocked or preview-only. Approval in a chat does not substitute for the gateway's own checks.

## Removal

Use the platform-supported Skill removal controls supplied with the actual device. No removal command has been verified. The Skill installs no custom database or daemon. Removing it does not establish removal of platform caches, model context, logs or optional exported reports. Use platform controls and documented retention policies for those resources; no secure purge capability is asserted.
