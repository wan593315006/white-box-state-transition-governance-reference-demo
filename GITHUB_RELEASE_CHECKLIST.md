# GitHub Release Checklist

## Purpose

This checklist prepares the public repository release of the v0.2.2 reference
demo. It does not authorize commercial use, disclose protected implementation
details, or replace qualified legal review of the custom license and patent
boundary.

## Before upload

- [ ] Confirm `SHA256SUMS.txt` and `RELEASE_MANIFEST.json` both verify from a
      clean copy.
- [ ] Confirm Python 3.9 and Python 3.13 test receipts each report 14 passing
      tests, and that the fixed cases and semantic-ablation receipts are present.
- [ ] Confirm `G0_PUBLIC_BOUNDARY_AUDIT.json` reports `PASS`.
- [ ] Confirm the final paper files are
      `paper/White语义白盒治理_v0.2.2.docx` and
      `paper/White语义白盒治理_v0.2.2.pdf`.
- [ ] Confirm the owner accepts the public disclosure boundary and has obtained
      any legal/IP advice considered necessary before publishing.

## Repository setup

- [ ] Create a **public** repository named
      `white-box-state-transition-governance-reference-demo`.
- [ ] Do not select a standard GitHub license template. This repository carries
      its own custom `LICENSE.md`.
- [ ] Upload the complete verified package, including `LICENSE.md`,
      `CITATION.cff`, the paper files, the public-boundary audit, checksums, and
      source/tests/results.
- [ ] Enable **Issues** for reproducible defects in the public reference demo.
- [ ] Enable **Discussions** for public technical questions and non-confidential
      research discussion.
- [ ] Keep credentials, non-public agreements, protected implementation details,
      and commercial negotiation out of public issues and discussions.

## Freeze and public check

- [ ] Verify the uploaded files against `SHA256SUMS.txt` from the repository.
- [ ] Create and verify the tag `v0.2.2-reference-demo` on the release commit.
- [ ] Create a GitHub Release using the same version and a factual summary of
      the reference-demo scope and its explicit limits.
- [ ] Verify that the collaboration address `593315006@qq.com` is visible in
      the README and license, and that commercial use is described as requiring
      prior written authorization.
- [ ] Copy the final GitHub repository/release URL into the later Zenodo record;
      do not guess it in advance.
