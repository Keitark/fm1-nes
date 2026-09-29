# Source publication checklist

This branch prepares a source-only candidate. It does not authorize changing
repository visibility or claim legal clearance. Keep the repository private
until the maintainer resolves the source-publication decisions below.

## Before making the repository public

- [x] Complete the bounded source-reference and publication-surface review.
  See PROVENANCE.md, LCD_PROVENANCE.md and PUBLICATION_AUDIT.md. The review
  distinguishes documented interfaces from retained board-specific findings.
- [ ] Record the maintainer's publication decision for retained LCD/boot/board
  material and the SDK-derived instruction templates in host audit scripts.
  Where rights remain unclear, obtain permission, seek applicable legal advice,
  or exclude/reimplement the affected portion from an appropriately reviewed
  specification. Relabeling or squashing does not establish independent origin.
- [x] Ask the maintainer about acquisition/confidentiality agreements. On
  2026-09-30 the maintainer reported: "No NDA or private agreement that I know of".
  This is a qualified personal report, not independent verification or a claim
  that every public download was free of terms.
- [x] Inspect the available pinned source licenses/notices and official download
  landing pages. PUBLICATION_AUDIT.md records scope and limits. Historical
  installer terms and access-method legality were not independently established;
  these limitations belong in the publication decision above, not a false pass.
- [x] Verify attribution, license copies and generated modification notices for
  the reviewed SDK/PeakRacing source adaptations. No source-license conflict was
  identified in that scoped review. A reference link is not a redistribution grant.
- [x] Run source checks and host tests for this candidate and review the CI
  workflow. The commit/archive verification receipt is recorded on issue #5.
  Repeat checks and inspect a fresh ZIP for any later release commit.
- [x] Review advertised branches/tags and PR refs, plus available GitHub issue/PR
  bodies, comments, Actions logs/artifacts, releases, attachment links and
  wiki/Pages/Discussions settings. The dated snapshot and limits are recorded in
  PUBLICATION_AUDIT.md. Refresh changed surfaces before publication; the local
  Git scanner alone does not cover them. Private evidence stays untracked.
- [ ] Confirm the exact visibility change separately. Do not automate publication
  merely because tests pass or an archive exists.

No legal sign-off is recorded by this checklist. Detailed review evidence can
remain private; retain truthful public attribution and required notices.
Do not erase development evidence or claim clean-room development retroactively.

The bounded LCD comparison is complete in [LCD_PROVENANCE.md](LCD_PROVENANCE.md):
all 21 records are mapped, but the publication decision is still open. Ten SDK
matches corroborate individual values; they do not change the existing origin.

## Repeatable technical checks

Stage only reviewed files listed in `public-files.txt`, then run:

```powershell
python -m unittest discover -s tests -v
python scripts/release.py --check --git
python scripts/build.py host
python scripts/release.py --git --output dist/fm1-source-candidate.zip
```

Use a fresh output filename for each candidate. The default legacy archive may
be stale; never distribute it merely because it exists. Packaging snapshots the
allowlisted working-tree bytes, so finalize and review the commit before making
the release archive. A ZIP includes `SOURCES.sha256` for its actual file bytes.

The source-only CI job checks packaging and local reachable history with the
same limited patterns. It does not download SDKs/ROMs, build device firmware,
publish artifacts, change visibility or replace a rights review. It also cannot
recognize every credential, private datum, or ROM disguised as text.

## Separate gates for binaries and hardware products

- Review the linked archives and toolchain terms listed in PROVENANCE.md before
  distributing firmware binaries, including any statically linked notices.
- Resolve the inherited USB VID/PID `3654:5155` before product distribution;
  it is a bench identity, not a project allocation or certification.
- Qualify a complete image, recovery path and hardware behavior separately.
  The `.app.bin` output is not a complete flash image.
- The standalone peripheral profile currently fails its static audit with
  `USB trace merged-global offset changed: 240`. Do not bypass this check or
  advertise that profile as qualified. See VALIDATION.md.

These binary/product gates do not by themselves prohibit publishing appropriately
licensed experimental source, but they must not be presented as completed.
