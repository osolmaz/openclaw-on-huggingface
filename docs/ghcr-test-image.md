# Temporary GHCR Test Image

The Hugging Face Space currently uses a fixed OpenClaw build from main commit
`5e1fbca3cbc60b1a4d4fa8c937dad22b826899b6`.

```text
ghcr.io/osolmaz/openclaw-live-test:hf-5e1fbca3
```

Digest:

```text
sha256:6b67ce03ba63cb50ce00369b258d8265005b7f460a38c22a0e9f93e1a74c29c6
```

The image was built locally from `~/oc/openclaw-worktrees/hf-online-search-fence`
and first pushed to a new GHCR package:

```text
ghcr.io/osolmaz/openclaw-hf-test:5e1fbca3
```

That package was private, and anonymous pulls failed with `401 Unauthorized`.
Because Hugging Face must pull the `FROM` image anonymously during Docker Space
builds, the image was copied into an existing public package:

```bash
docker buildx imagetools create \
  -t ghcr.io/osolmaz/openclaw-live-test:hf-5e1fbca3 \
  ghcr.io/osolmaz/openclaw-hf-test:5e1fbca3
```

Anonymous pull was verified with:

```bash
docker logout ghcr.io
docker buildx imagetools inspect ghcr.io/osolmaz/openclaw-live-test:hf-5e1fbca3
```

The test Space `osolmaz/onurclawtest` is on commit:

```text
58551d6a638bef36d2c5968c1c5d2f9f31480b0e
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
  -t ghcr.io/osolmaz/openclaw-hf-test:5e1fbca3 \
  --push .
```

## Cleanup

After the fix is merged and the official image includes it:

1. Update the Space Dockerfile back to:

```dockerfile
FROM ghcr.io/openclaw/openclaw:<official-tag-containing-5e1fbca3-or-newer>
```

2. Rebuild and re-run the Space verification checklist.
3. Delete or deprecate the temporary GHCR tags.
