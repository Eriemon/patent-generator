---
name: readable-patent-generator
description: >-
  Use when users need to extract invention points from local technical materials and
  generate, rewrite, review, or iteratively refine readable Chinese patent drafts
  under governed local-only workflows with strict language-routing and directory
  contracts.
---

# Readable Patent Generator

Use this skill when the work is about turning local research notes, design
documents, implementation code, prior patent drafts, and engineering context
into readable Chinese patent drafts and review artifacts.

Keep this root thin:

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
4. Keep generated assets, references, evals, and fixtures in their governed
   locations.
5. Verify structure, language gates, and delivery evidence before treating the
   work as complete.

See [references/README.md](references/README.md) for current workflow
references, writing rules, and review checkpoints.
