# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org).

## [1.0.0] - 2026-11-24

First official release of MakeTwin. This version focuses on mechanical products; general product support is planned.

### Added
- Dark-mode "MakeTwin" browser viewer with take-apart, isolate, transparent context, section preview, and guided tour.
- Named-part Blender/glTF workflow with function, relationship, and evidence metadata (`parts.json`, `explorer.json`).
- Validation tooling: geometry/collision checker, metadata and explosion audits, delivery verification.
- Packaging scripts and regression suites.

### Changed
- Promoted from the `mechanical-explorer-test` preview; the installation ID `mechanical-explorer-test` is kept for compatibility.
- Removed the optional Codex-specific batch runner so the skill is provider-agnostic: it runs in any coding agent with file and shell access.
- Validation notes moved to `docs/VALIDATION.md`.

### Fixed
- Viewer controller test mock now supports the dark-mode panel lookup.
