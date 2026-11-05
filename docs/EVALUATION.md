# Evaluation and evidence levels

The canonical measured output is `artifacts/benchmark.json`. Run `python tools/benchmark.py` to regenerate fixtures and measure this workstation. Timing varies by host and filesystem. The submitted ZIP does not include these scripts or measurements.

## Actual local experiment

133 indexed synthetic text files; one private fixture excluded. Ten authored queries, including a synonym-heavy query that the lexical baseline misses. Three known duplicate pairs. Four sensitive-pattern positives and 129 negatives. Labels and queries were authored alongside the fixtures, so this is a small biased functional benchmark, not an independent quality study. The corpus has manuals, receipts, warranty, research, privacy controls and distractor notes; image/OCR coverage is not tested.

Observed baseline: macro Recall@5 0.90, MRR@5 0.90; all three duplicate pairs recovered without false pairs. The pattern detector had zero false positives among the synthetic negative controls. These results say nothing about real private-file detection accuracy or NAS semantic search quality. The complete measurements include initial indexing throughput, unchanged-row reindex timing, mean/p95 query latency and Python allocation peak.

Recall@5 is relevant documents retrieved in the first five divided by labeled relevant documents, averaged across queries. MRR@5 averages reciprocal rank of the first relevant result, using zero for a miss. Duplicate metrics use unordered pairs, not group counts. Sensitive false-positive rate is false positives divided by labeled negative files. Thirty passes over ten queries yield 300 warm timing observations; p95 uses nearest rank. No timing samples are discarded. `tracemalloc` measures Python allocations, not native allocations or total resident memory.

Local indexing rehashes content on every scan but rewrites only changed SQLite rows; it is not a background filesystem watcher. Oversized, unreadable or rejected-link files are reported as unassessed. This reader is intended for a trusted synthetic corpus, not hostile concurrent filesystem mutation.

## Tests and UI verification

`artifacts/test-results.txt` records unit and HTTP integration results. Tests cover bounded indexing, exclusions, changed/deleted sources, query escaping, duplicate labels, masked previews, immutable plan records, missing/wrong/expired/replayed approvals, scope changes, collisions, partial approval/failure, fresh inverse approval and an explicitly unavailable UGOS adapter. HTTP tests check the interface assets, CSRF/origin rejection, and that a simulated move leaves actual source bytes unchanged.

Browser review verifies source results, the plan preview, simulated completion and inverse preview. It supplements automated tests and is not a NAS runtime recording.

## Intentionally unmeasured

NAS semantic retrieval, local-model latency/memory, NAS indexing throughput, OCR, gateway enforcement and actual time saved versus manual organization are null/unmeasured. For a human-time comparison, recruit participants to perform the same counterbalanced retrieval/organization tasks manually and with the actual Skill, record completion time and errors, and report medians and spread. Do not infer time saved from search latency.
