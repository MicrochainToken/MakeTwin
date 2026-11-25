# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org).

## [1.0.1] - 2026-11-25

### Fixed
- Wrap download and playback controls on narrow screens so navigation remains accessible.
- Hide physical guide captions during display-only inspection and restore them on playback.
- Release archives include VERSION and a complete preview asset set under the stable skill install ID; exclude local inputs, output and Git history.
- Setup checks cover every viewer dependency and verify vendor module hashes.
- The synthetic mini-oven smoke run includes validated part semantics and authored take-apart metadata.
- Boolean regression expectations now respect Blender 4.2–4.4's EXACT solver while retaining volume and fallback checks.
- Full regression runs now include the camera export/render fixture and stop early when Blender is unavailable.
- Bundled Mapbox Earcut attribution is retained alongside the Three.js license.

### Added
- A separate Blender/browser integration workflow with saved test logs and screenshots.

### Documentation
- Add a runnable example, Linux setup guidance and Conventional Commit guidance.
- Align viewer/camera instructions with the shipped interface; remove deleted supervisor/broker assumptions and outdated release labels.
- Describe the illustrative preview and its partial validation status explicitly.

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
