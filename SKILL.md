---
name: readable-patent-generator
description: >-
  Use when users need to extract invention points from local technical materials and
  generate, rewrite, review, or iteratively refine Chinese patent technical
  disclosure delivery packages for patent agents, with governed DOCX, Markdown,
  and figure outputs under strict local-only workflows and language-routing contracts.
---

# Readable Patent Generator

Use this skill when the work is about turning local research notes, design
documents, implementation code, prior patent drafts, and engineering context
into readable Chinese patent drafts and review artifacts.

Primary delivery contract: produce a Chinese 《专利技术交底书》 delivery
package suitable for handing to a patent agent. The default formal package is:

- a strict-template DOCX main manuscript
- the confirmed Markdown source稿
- an independent figures package that also feeds the embedded DOCX figures

Keep evidence notes, missing administrative fields, terms, and claim drafts in
internal sidecars unless the user explicitly asks to include them in the main
disclosure. Keep the hard preview gate: first return `preview_pending`, then
only enter formal delivery generation after explicit preview confirmation.
Apply `assets/examination_quality_contract.json` to every case.

Use disclosure model 4.0 and claims map 3.0 for new work. Treat
`technical_profile` as a writing-profile choice only; it never enables,
disables, or selects examination rules. Apply the registered rules from the
case facts instead: hard AI facts mandate AI examination rules and cannot be
opted out, soft AI signals require a reasoned human applicability decision,
and a no-AI decision still requires human confirmation. Require `ai_scope`
whenever AI rules apply.

Bind embedded semantic reviews to the exact reviewed content hash. Require
current human confirmations for governed quantitative facts, every
independent-claim feature set, and AI applicability. Treat headings, step IDs,
or words such as “通过” as labels only, never as enabling content or review
evidence. Older disclosure or claims models require explicit migration and a
new semantic review; conversion alone never restores reviewed status.

Keep this root thin:

- treat the installed skill directory as read-only; write runtime cases,
  materials, and outputs only under the current local work folder or an
  explicitly selected research root
- route Python file creation or modification through `readable-python-generator`
- route bat/cmd, shell/bash, PowerShell, and Tcl script creation or
  modification through `readable-script-generator`
- keep formal skill content under `skills/readable-patent-generator/`; do not
  place `tests/`, `tools/`, or flat scripts inside the skill directory
- keep all Python files under `scripts/python/<function>/`
- keep all non-Python scripts under their matching `scripts/<family>/`
- install Python dependencies only through `pip install -r requirements.txt`;
  CNIPA online search uses the standard-library `urllib` production entrypoint
  and needs no browser-runtime installation

Default workflow:

1. Check the root `AGENTS.md` and local governance state.
2. Read only the local source material needed for the current patent task.
3. Extract invention points, draft the required patent sections, and record
   reviewable intermediate artifacts under governed directories.
   Treat every imported material as review input, not as正文事实. Before a
   material can contribute to the formal draft, require an explicit human
   decision and an explicit `source_roles` value of `invention_evidence` or
   `prior_art`; never infer the role from a file name, paper section, or model
   guess. Keep rejected, pending, conflicting, and unknown-role material out of
   the formal model.
   Treat every measured value, comparison, percentage, threshold, sample
   count, parameter value, and performance statement as a governed data
   candidate. It may enter the formal draft only after explicit acceptance and
   assignment of a stable `data_id` in `data_registry`. Do not copy numerical
   results from papers or supplied materials merely because they appear
   relevant. Formula literals are governed by `formula_registry`, not silently
   reclassified as experimental data.
   Background technology must explain the prior mechanism, inputs/outputs,
   constraints, and technical gap from verified prior-art records. Cite every
   sourced background statement with stable numeric references and include the
   corresponding bibliographic entries; unverifiable non-patent background
   text must block formal drafting.
   Classify each prior-art record against the patent reference date. Documents
   published after that date may be retained only as later references and must
   not be used to establish the background or inventive-step baseline.
   For inventive-step review, record the closest prior art, distinguishing
   features, their technical effects, the reformulated objective technical
   problem, and whether the prior art supplies a technical motivation with
   evidence. Bind every technical feature to stable evidence identifiers,
   normalize terminology through `term_registry`, and block unsupported,
   contradictory, or drifting technical points.
   Generate claims only from mapped support. Unsupported independent claims
   block delivery; unsupported dependent, system, device, or medium candidates
   are omitted and reported for optional material supplementation.
4. When display formulas enter the formal draft, provide confirmed semantics
   in `<research-root>/formula_facts.json`, including purpose, sources,
   references, inputs/outputs, constraints, and every symbol's meaning, unit,
   and domain. Missing formula semantics must block validation; never infer
   them from variable names alone.
   Export every display and inline formula as an editable equation object. The
   default `mathtype` mode uses Word COM and MathType's `Equation.DSMT4`
   `IDataObject` interface to create native MathType OLE/MTEF equations. The
   explicit `office` compatibility mode writes native OMML. Standalone formula
   images, plain-text fallback, and silent fallback from MathType to Office are
   forbidden. Any formula conversion failure must block delivery.
5. Persist the formal disclosure as model 4.0, including
   `source_manifest`, `evidence_registry`, `data_registry`,
   `formula_registry`, `term_registry`, and `figure_registry`. Every generated
   figure must retain its draft source, file outputs, section bindings, and
   source-item provenance; unregistered figures must block delivery.
6. Generate claims through claims map 3.0. Keep each independent claim bound
   to confirmed feature and evidence identifiers; a stale or missing human
   confirmation blocks delivery.
7. Keep generated assets, references, evals, and fixtures in their governed
   locations.
8. Export through `assets/cn_technical_disclosure_template.docx`; do not treat a
   case as complete unless the final DOCX preserves the template information
   table, required section headings, non-empty technical sections, and no
   internal review placeholders. Apply the governed Chinese layout contract:
   body text uses 宋体 14 pt, 1.5 line spacing, and a two-character first-line
   indent; numbered steps and reference entries use a two-character hanging
   indent; display formulas and figures are centered; each populated template
   slot ends with exactly one blank paragraph and each empty slot with none.
   Validate these properties independently from the final saved DOCX before
   delivery.
9. Verify structure, language gates, and delivery evidence before treating the
   work as complete.

Formula export modes:

- `run_pipeline.py` defaults to `--equation-mode mathtype`; this requires
  Windows, Word, MathType, and pywin32, and emits native `Equation.DSMT4` OLE
  equations.
- `run_pipeline.py --equation-mode office` remains an explicit compatibility
  mode for native OMML output.
- Supported inline delimiters are `$...$` and `\(...\)`; display formulas use
  governed `$$...$$` blocks.

See [references/README.md](references/README.md) for current workflow
references, writing rules, and review checkpoints.
