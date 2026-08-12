<p align="center">
  <a href="README.md"><strong>English</strong></a>
  <span>&nbsp;|&nbsp;</span>
  <a href="README-CN.md">中文</a>
</p>

<h1 align="center">Readable Patent Generator</h1>

<p align="center">
  <img src="assets/readme/hero.png" alt="Readable Patent Generator hero illustration" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-1f6feb"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f81f7"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v2.1.6-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent--skill-16a34a"></a>
  <a href="references/README.md"><img alt="Target" src="https://img.shields.io/badge/target-Chinese--patent--package-f59e0b"></a>
</p>

<p align="center">
  A Codex skill for turning technical material into a reviewable Chinese patent technical-disclosure package.
</p>

Readable Patent Generator helps researchers, engineers, and patent-writing collaborators turn research notes, design documents, implementation records, and other technical material into a clear Chinese patent disclosure. It keeps the source material, draft, claims, formulas, and figures connected so the result is easier to review with a patent professional. The workflow is deliberately local and review-first: material roles are confirmed before formal modeling, accepted facts retain source links, and unsupported claim features block delivery.

## What it helps you do

- Organize technical material into a coherent invention description.
- Separate invention material from prior-art material.
- Review important facts, terms, formulas, and claim scope before drafting.
- Produce an editable DOCX document, a Markdown draft, and a separate figure set.
- Start with a preview so you can correct the direction before formal delivery.

## Install the skill

Ask your AI assistant to install the skill from the public repository:

```text
Install the readable-patent-generator skill from https://github.com/Eriemon/patent-generator
```

After the skill is available, you can use it directly in your AI assistant.

## Use it

### 1. Prepare your material

Put the material you want the assistant to review in the working folder you choose. Useful inputs include research notes, design documents, implementation records, experiment descriptions, drawings, and relevant prior-art references.

![Traceable source map](assets/readme/project-facts.png)

The source map separates input material from the structured model and the source links that support it. In particular, a number, threshold, sample count, or formula is not treated as a fact merely because it appears in a document: it must be accepted, assigned a stable identifier, and linked back to a source location.

### 2. Ask for a patent disclosure

Call the skill by name and describe the result you want. For example:

```text
Use $readable-patent-generator to turn the materials in this folder into a Chinese patent technical-disclosure package. Start with a preview and ask me to confirm the source roles, important facts, and invention scope before drafting.
```

### 3. Review the preview

The assistant will show how the material, technical terms, key facts, formulas, claims, and figures fit together. Confirm or correct anything that affects the invention before asking for the formal package.

![Preview-first review](assets/readme/design-profile.png)

The preview is a control point. Before drafting, review the source roles, accepted facts, terminology, formula meaning, and invention scope. If source support conflicts, a number has no acceptance record, a formula is ambiguous, or a claim lacks support, the workflow remains blocked.

### 4. Receive the delivery package

After you confirm the preview, the assistant prepares the formal package:

- The Chinese patent technical disclosure as the main deliverable.
- An editable DOCX version for review and handoff.
- A Markdown version for traceable editing.
- A separate figure set for the disclosure.

![Review before delivery](assets/readme/rule-rendering.png)

The support map is intended to be inspected rather than trusted as a black box. Quantitative statements use accepted stable data IDs; independent-claim features point to current human-reviewed support; equations remain editable; and figure captions, numbering, and source bindings stay connected through delivery.

## What to expect

This skill organizes and drafts technical disclosure material; it does not replace a patent agent's legal review or filing decisions. Keep confidential material in a workspace you trust and review the generated package before sharing it.

![Delivery package](assets/readme/local-delivery.png)

The output is a local, editable package: the disclosure in DOCX, the confirmed Markdown source, the separate figure set, and the claim/support map. You decide what leaves the workspace and when to involve a patent professional; the skill does not make legal filing decisions.

## Authors and citation

Jiyuan Liu and He Li are with Southeast University (东南大学). The work is developed with the Heterogeneous Intelligence and Quantum Computing Laboratory (HIQC).

If you build on this skill, cite the package through [CITATION.cff](CITATION.cff):

```bibtex
@software{liu_2026_readable_patent_generator,
  author = {Jiyuan Liu and He Li},
  title = {{Readable Patent Generator}: A Governed Local Skill for Chinese Patent Packages},
  year = {2026},
  version = {2.1.6},
  date = {2026-08-12},
  url = {https://github.com/Eriemon/patent-generator},
  license = {Apache-2.0}
}
```

Released under the Apache License 2.0. See [LICENSE](LICENSE), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CITATION.cff](CITATION.cff).

Release date: 2026-08-12 · Version: v2.1.6
