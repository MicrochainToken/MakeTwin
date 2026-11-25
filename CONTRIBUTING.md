# Contributing

1. Fork and create a branch from `main`.
2. Run the checks before opening a pull request:
   ```sh
   python3 scripts/doctor.py
   bash tests/run_tests.sh
   ```
3. Keep user product photos, manuals, credentials, and generated case models out of the repository. The existing illustrative preview is documented in `PROVENANCE.md`.
4. Add a line to `CHANGELOG.md` under an "Unreleased" heading for user-visible changes.

## Commit titles

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
`type: short description`, with an optional scope such as `fix(viewer): restore the assembled pose`.

- `fix:` correct behavior or a release defect.
- `feat:` add a user-facing capability.
- `docs:` update instructions or explanatory material.
- `test:` add or improve regression coverage.
- `chore:` maintain tooling, dependencies or release metadata.

Keep each commit focused, use the imperative ("include", "validate", "document"),
and explain non-obvious reasons in the body. Mark incompatible changes with `!`
and a `BREAKING CHANGE:` explanation. Existing history does not need renaming.

## Browser integration check

After `doctor.py --smoke --out ../maketwin-example`, serve that folder using the
README command. With Node.js 22+, install the test-only browser tools locally:

```sh
npm install --no-save --package-lock=false playwright@1.65.1
npx playwright install --with-deps chromium
node tests/browser_smoke.cjs http://127.0.0.1:8000 ../maketwin-browser-check
```

This checks GLB/manifest/layout loads, console errors, exploration and playback
reset, and saves desktop/mobile screenshots. Review the screenshots as well.
Do not include node_modules or generated test outputs in a release archive.
