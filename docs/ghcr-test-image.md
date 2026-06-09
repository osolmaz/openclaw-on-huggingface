# Temporary GHCR Test Image

The Hugging Face Space currently uses a fixed OpenClaw build from local fix
commit `53e662fba3`.

```text
ghcr.io/osolmaz/openclaw-live-test:hf-53e662fb
```

Digest:

```text
sha256:3f729e1a9c74c885a3f05b3ad4ee48f072a84b02654d9374e4dc304bb610abeb
```

The image was built locally from `~/oc/openclaw-worktrees/hf-online-search-fence`
and first pushed to a new GHCR package:

```text
ghcr.io/osolmaz/openclaw-hf-test:53e662fb
```

That package was private, and anonymous pulls failed with `401 Unauthorized`.
Because Hugging Face must pull the `FROM` image anonymously during Docker Space
builds, the image was copied into an existing public package:

```bash
docker buildx imagetools create \
  -t ghcr.io/osolmaz/openclaw-live-test:hf-53e662fb \
  ghcr.io/osolmaz/openclaw-hf-test:53e662fb
```

Anonymous pull was verified with:

```bash
docker logout ghcr.io
docker buildx imagetools inspect ghcr.io/osolmaz/openclaw-live-test:hf-53e662fb
```

The test Space `osolmaz/onurclawtest` is on commit:

```text
0251267002af2274cdd289185f2beaf053ae084b
```

It reached `RUNNING` on `2026-06-09` with gateway ready and Telegram polling
started.

## Requirements

- Docker installed locally or CI available.
- GitHub account/token that can push packages to `ghcr.io/osolmaz`.
- Token scopes:

```text
write:packages
read:packages
```

The final `FROM` image must be public. Hugging Face Docker Spaces can expose
build secrets to `RUN` steps, but that does not help authenticate the initial
`FROM ghcr.io/...` pull.

## Login

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u osolmaz --password-stdin
```

## Build and Push

Current confirmed build command:

```bash
cd ~/oc/openclaw-worktrees/hf-online-search-fence
docker buildx build --platform linux/amd64 \
  -t ghcr.io/osolmaz/openclaw-hf-test:53e662fb \
  --push .
```

## Cleanup

After the fix is merged and the official image includes it:

1. Update the Space Dockerfile back to:

```dockerfile
FROM ghcr.io/openclaw/openclaw:<official-tag-containing-the-session-fence-fix>
```

2. Rebuild and re-run the Space verification checklist.
3. Delete or deprecate the temporary GHCR tags.
