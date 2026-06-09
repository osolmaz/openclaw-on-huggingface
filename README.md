# OpenClaw on Hugging Face

Tracking repo for making OpenClaw deploy cleanly on Hugging Face Spaces.

This repository is for coordination, docs, investigation notes, and verification
checklists. It is not the source of truth for OpenClaw runtime code fixes.

## Scope

- Track the Hugging Face deployment shape for OpenClaw.
- Record Space, bucket, and image resources used during testing.
- Preserve prior writeups from the Hugging Face Space/bootstrap repos.
- Document root-cause investigations and verification steps.

## Not In Scope

- OpenClaw core source changes. Those belong in `openclaw/openclaw`.
- Secrets, bot tokens, gateway tokens, or private bucket contents.
- A second copy of the deployable Hugging Face Space artifact.

## Current State

The current test deployment uses a Hugging Face Docker Space based on:

```text
ghcr.io/openclaw/openclaw:latest
```

Telegram connectivity on paid HF Space hardware has been verified. The current
blocking issue is an OpenClaw embedded-session fence bug triggered after a model
tool call, documented in:

```text
docs/session-fence-root-cause.md
```

## Docs

```text
docs/resources.md                 Current HF/GitHub/GHCR resources
docs/session-fence-root-cause.md  Root cause for Telegram reply failures
docs/2026-06-09-session-mutation-controller-refactor-plan.md
                                  Long-term OpenClaw session mutation fix plan
docs/space-verification-plan.md   How to verify a fixed OpenClaw image on Spaces
docs/ghcr-test-image.md           Temporary GHCR image plan
docs/gemma-4-12b-inference-endpoint.md
                                  Gemma 4 12B endpoint path
tracking/2026-06-09-session-fence-tool-result-takeover.md
                                  Session-fence incident diagnosis
tracking/2026-06-09-online-search-session-fence-takeover.md
                                  Online-search session-fence incident
tracking/decisions.md             Decisions made so far
```

## Archive

Prior writeups and Space READMEs are copied verbatim under `archive/`.

```text
archive/plans/
archive/hf-space-readmes/
archive/hermes/
archive/scripts/
```

These files preserve history. Current docs should link to archived files instead
of editing them.
