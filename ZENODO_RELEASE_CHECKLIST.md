# Zenodo Release Checklist

## Do before creating a new Zenodo version

- [ ] Confirm the Git tag `v0.2.2-reference-demo` resolves to the intended
      frozen commit.
- [ ] Verify `SHA256SUMS.txt` and `RELEASE_MANIFEST.json` from a clean copy.
- [ ] Re-run Python 3.9 and 3.13 tests; retain the resulting evidence files.
- [ ] Upload the final PDF, DOCX, Figure 1, source, license, citation file,
      reproducibility guide, public-boundary audit, and checksums together.
- [ ] Confirm that Figure 2 and protected implementation materials are absent.
- [ ] Complete independent legal review of the license and patent/public
      disclosure boundary before making a public legal commitment.
- [ ] Create a new Zenodo version or draft; do not delete the older Zenodo
      draft merely to replace it.
- [ ] Add the GitHub Release link only after the public repository and release
      have been created.

## Metadata to enter manually

- Title: White Box State Transition Governance
- Version: 0.2.2
- Author: 万根
- Affiliation: Independent Researcher
- License: Research and Noncommercial License v1.0
- Related identifier: Git tag/release URL, after it exists

## Current boundary

This checklist prepares a release; it does not create a GitHub repository,
GitHub Release, Zenodo record, DOI, or commercial authorization. The public
contact channel is stated in `README.md` and `LICENSE.md`.
