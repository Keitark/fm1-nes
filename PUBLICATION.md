# Source publication checklist

This branch prepares a source-only candidate. It does not authorize changing
repository visibility or claim legal clearance. Keep the repository private
until the maintainer resolves the source-publication decisions below.

## Before making the repository public

- [ ] Review the focused map in PROVENANCE.md, especially the retained FM-1_010
  LCD initialization table and stock-specific boot/board adaptation. Record the
  basis for publishing each questioned portion; where rights remain unclear,
  obtain permission, seek applicable legal advice, or exclude/reimplement it
  from an appropriately reviewed specification. Relabeling or changing names
  does not establish independent implementation.
- [ ] Confirm any relevant firmware/tool acquisition terms, confidentiality
  commitments and access-method questions. Repository scans cannot establish
  those facts. Obtain jurisdiction-specific advice for unresolved legal issues.
- [ ] Verify upstream attribution, licenses and modification notices for the
  exact source being released. Do not assume a link to public research grants
  rights to third-party content hosted there.
- [ ] On the final commit, run the source checks and host tests below, inspect
  the ZIP inventory, and record its hash. Review any changed CI workflow itself.
- [ ] Review all branches/tags that will be visible, plus GitHub issues, PR
  discussions, Actions logs/artifacts, releases, attachments and any wiki/pages.
  The local Git scanner does not inspect those hosted surfaces or unfetched refs.
  Keep private review notes outside tracked paths and public discussions.
- [ ] Confirm the exact visibility change separately. Do not automate publication
  merely because tests pass or an archive exists.

No legal sign-off is recorded by this checklist. Detailed review evidence can
remain private; retain truthful public attribution and required notices.
Do not erase development evidence or claim clean-room development retroactively.

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
