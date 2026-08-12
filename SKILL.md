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
Apply `assets/examination_quality_contract.json` to every case. Keep the
general profile active by default. If local facts suggest an AI case, expose a
`profile_check` in the preview and require the user to explicitly keep
`general` or select `ai_algorithm`; never switch profiles automatically.

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
  if CNIPA browser search is needed, run `python -m playwright install
  chromium` after installation

Default workflow:

1. Check the root `AGENTS.md` and local governance state.
2. Read only the local source material needed for the current patent task.
3. Extract invention points, draft the required patent sections, and record
   reviewable intermediate artifacts under governed directories.
   Background technology must explain the prior mechanism, inputs/outputs,
   constraints, and technical gap from verified prior-art records. Cite every
   sourced background statement with stable numeric references and include the
   corresponding bibliographic entries; unverifiable non-patent background
   text must block formal drafting.
   For inventive-step review, record the closest prior art, distinguishing
   features, their technical effects, the reformulated objective technical
   problem, and whether the prior art supplies a technical motivation with
   evidence.
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
5. Keep generated assets, references, evals, and fixtures in their governed
   locations.
6. Export through `assets/cn_technical_disclosure_template.docx`; do not treat a
   case as complete unless the final DOCX preserves the template information
   table, required section headings, non-empty technical sections, and no
   internal review placeholders. Apply the governed Chinese layout contract:
   body text uses 宋体 14 pt, 1.5 line spacing, and a two-character first-line
   indent; numbered steps and reference entries use a two-character hanging
   indent; display formulas and figures are centered; each populated template
   slot ends with exactly one blank paragraph and each empty slot with none.
   Validate these properties independently from the final saved DOCX before
   delivery.
7. Verify structure, language gates, and delivery evidence before treating the
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
