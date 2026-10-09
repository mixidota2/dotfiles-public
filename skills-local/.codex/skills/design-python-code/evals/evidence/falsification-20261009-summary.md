# Falsification review: independent evaluation

The evaluated v2 runtime passed the deep gate: **50/50 fresh trials and 240/240 requirements**. This records review behavior on supplied scenarios; it does not prove general architecture superiority or validate downstream production implementations.

- [Compact manifest: runtime hashes, trial identities and every requirement verdict](falsification-20261009-manifest.json)
- [Task manifest](../eval.yaml), [append-only evaluation ledger](../ledger.yaml)
- Evaluated package SHA256: `88404f9700a96b64bad6702493ff0af350bc25b14dc442e06952e38f446db32c`
- Evaluated runtime SHA256: `c570335812c2b87a06b2e959d01aa5ccafa867c18e572ac6858b726419015f3c`

The runtime hash excludes `evals/`. Source runtime files were independently rechecked against the frozen snapshot before adding this evaluation record. Appending evidence changes the package hash, not the evaluated runtime.

## Observed results

| Phase | Critical-task successes / trials | Requirements passed / total |
| --- | --- | --- |
| Retained v1, stopped first round | 3/5 | 24/26 |
| v2 clear round 1 | 22/22 | 106/106 |
| v2 clear round 2 | 22/22 | 106/106 |
| v2 final regression | 2/2 | 10/10 |
| Original flat-library holdout | 2/2 | 6/6 |
| Independent mutable-alias holdout | 2/2 | 12/12 |
| No-Skill baselines | 1/2 formal gate; both substantively sound | 11/12 |

There were **57 actual completed trials**: 50 v2, five v1 and two baselines. A prepared but undispatched v1 workspace is excluded. Historical ledger results are not counted as fresh evidence.

Each clear round covered two independent trials for all 11 fixed scenarios: four original behaviors, three new task-manifest cases and four independently selected cases. The additional cases examined duplicate ID ownership and pass-through boundaries, a tiny flat parser, optional-backend transitive imports and unknown overwrite authority. Public API, configuration/DI reuse, protected files, read-only authority and narrow syntax repair remained covered. The final regression repeated `falsify-local-but-invalid-candidate` twice. The four syntax trials made only the expected one-character fixture repair and passed its focused test.

## Failure and correction

The v1 inventory output kept the overall proposal provisional but assigned Evidence Pass because unknowns were honestly disclosed. It failed `no-false-pass` (3/4). Re-inspection found the same mismatch in the first indexing output, correcting its grade from 7/7 to 6/7; the initial grade is retained and separately hashed. These are review-contract failures, not findings that the entire architectures were unsafe.

One Evidence rubric row was clarified: factual support must be sufficient for the scoped design, while material unknowns remain Revise even when disclosed. Explicit facts about a hypothetical system can support judgments within that scope. Scenarios and grading requirements were unchanged, and v2 restarted both convergence rounds. The compact manifest retains both failed trials and the corrected grade's provenance.

## Readable examples

These four deliverables are byte-identical to the measured outputs. Portable grades retain the original requirement judgments and line references; path fields are normalized. Their `deliverable` paths are relative to `evals/evidence/`.

- v1 indexing failure: [output](examples/r1-indexing-ownership-t1/deliverable.md), [initial grade](examples/r1-indexing-ownership-t1/semantic-grade.initial.json), [corrected grade](examples/r1-indexing-ownership-t1/semantic-grade.json). The correction concerns Evidence sufficiency, not the substantive architecture.
- v1 missing-evidence failure: [output](examples/r1-keep-missing-evidence-provisional-t1/deliverable.md), [grade](examples/r1-keep-missing-evidence-provisional-t1/semantic-grade.json).
- v2 missing-evidence correction: [output](examples/v2-r1-keep-missing-evidence-provisional-t1/deliverable.md), [grade](examples/v2-r1-keep-missing-evidence-provisional-t1/semantic-grade.json).
- v2 minimal flat design: [output](examples/v2-r2-tiny-flat-parser-t2/deliverable.md), [grade](examples/v2-r2-tiny-flat-parser-t2/semantic-grade.json).

Inputs: [inventory task](../tasks/missing-evidence.yaml); [unchanged independent indexing/parser requests and criteria](representative-cases.json). These examples supplement the complete trial identities, hashes and verdicts in the compact manifest; they are not full engine transcripts.

## Baseline value and cost

Both no-Skill baselines already produced sound minimal architectures. Indexing passed all six substantive requirements; its only formal miss was the explicit ten-dimension evidence review. The tiny parser passed 5/5. The supported benefit is repeatable review coverage, counterfactual checks, evidence discipline and preservation of constraints, not unique solution quality or statistically established superiority.

There is a verbosity cost: tiny-parser candidate outputs were 70–91 lines and 6,627–8,682 UTF-8 bytes, versus 28 lines and 2,621 bytes for its baseline. Reliable token, tool-call, cost and comparable timing measurements were unavailable.

## Method, integrity and limits

- Every measured trial used a fresh agent context and one ordinary task. Runtime copies omitted eval files; expected answers, protected grading criteria and prior outputs were withheld. No new model API, credentials or runner was added.
- An independent evaluator inspected actual deliverables, applied each fixed semantic requirement and recorded line-linked reasons. Self-reported success did not determine grades. Two non-required text misses were retained as surface disagreements rather than semantic failures.
- Both holdouts remained outside the edit loop and ran only after the two clear rounds and final regression. The independent scenario was locked before iteration; its unchanged specification hash is in the manifest.
- A continuity gap was reported at 05:26 UTC. Recovery found 42 persisted grades and two completed ungraded artifacts, which were inspected without rerunning. Exact lifecycle timestamps and uninterrupted execution cannot be established.
- The final audit covered all 57 trials with zero remaining integrity errors. Logical task/file-copy isolation used a shared filesystem, not separate OS sandboxes. Helper errors and a citation correction were retained in the external evaluator record without creating extra behavior trials.
- Four representative outputs and their detailed grades are included above. Other detailed outputs, raw case copies and line-linked grading reasons are retained outside this repository. The compact manifest contains all identities and hashes, every requirement verdict and retained failure explanations; unlinked hashes are not download locations. Native engine transcripts were unavailable.
- Routing was not rerun because the activation description was unchanged. Historical routing evidence remains historical. Narrative implementation/test plans are not claimed as executed production tests.
- No runtime Skill installation, merge, issue closure or publication is established by this evidence. Passing these cases is not a guarantee for all future designs.
