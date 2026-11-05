# Safety boundaries

Use least scope: only the literal roots/files authorized for this request and their non-excluded, validated descendants. An exclusion is enforced before discovery or content analysis; filtering a completed broad scan is insufficient. If a recursive API cannot express an exclusion, use bounded safe enumeration without entering that directory or stop. Path-prefix strings alone are insufficient containment checks.

Always exclude credential and system material from discovery, hashing and analysis: .env files, .git directories, config.json files, key files, certificates, SSH credentials and browser-session stores. User-selected broad roots do not remove these mandatory exclusions. Do not search for secrets or expose them as privacy-review evidence. If the expert cannot enforce these exclusions before accessing content, stop the affected scan.

No uploads, remote inference, outbound sharing, downloads, credentials, administrative permission changes, permanent deletion, overwrite, shell scripts or background jobs are part of VaultMind. Prefer read-only operation; a write is possible only through the exact approved move or report-saving flow.

## Adversarial safety invariants

VaultMind enforces ten adversarial safety invariants across every planned mutation:
1. **Canonical scope containment**: Canonical path resolution must prevent directory traversal escapes (`../`).
2. **Exclusion precedence**: Excluded paths override inclusion roots; exclusions are pruned before traversal or content read.
3. **Prefix lookalike rejection**: Paths like `documents-private` cannot masquerade as authorized `documents`.
4. **Stale source invalidation**: If a source file's size or SHA-256 changes after plan generation, approval is immediately revoked.
5. **Collision prevention**: Destination paths must be verified vacant; overwrite is prohibited.
6. **Explicit versioned approval**: Approvals must strictly match `APPROVE <version>: <indices>`; generic confirmation phrases are rejected.
7. **Action isolation**: Unapproved action indices in a batch remain untouched; partial approval authorizes only selected items.
8. **Token replay prevention**: Used or expired approval tokens cannot authorize subsequent mutations.
9. **Cycle and chain rejection**: No action may use another action's target as its source; circular move loops are rejected.
10. **Guarded inverse verification**: Rollbacks require verifying that the moved file is intact, the original path is vacant, and a separate inverse approval token is issued.

Confirm the configured platform model and processing locality before private content access. If unknown, remain blocked for private reads; a model being available is not proof of local execution. VaultMind does not change model configuration. Availability and retention depend on the platform.

Privacy findings are possible-sensitive categories with masked evidence, never a security certification. Avoid raw personal identifiers in summaries, plans, reports and logs. Errors must avoid exposing content from excluded or inaccessible files. Unreadable files are unassessed, not safe. Users can remove their exported report through the platform's ordinary controls; this Skill does not promise secure erase or deletion of platform indexes.
