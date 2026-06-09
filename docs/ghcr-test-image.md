# Temporary GHCR Test Image

The Hugging Face Space currently uses:

```text
ghcr.io/openclaw/openclaw:latest
```

For Space verification before an upstream release, publish a temporary image:

```text
ghcr.io/osolmaz/openclaw:hf-session-fence-test
```

## Requirements

- Docker installed locally or CI available.
- GitHub account/token that can push packages to `ghcr.io/osolmaz`.
- Token scopes:

```text
write:packages
read:packages
```

If the image is public, Hugging Face can pull it without registry credentials.

## Login

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u osolmaz --password-stdin
```

## Build and Push

Exact commands depend on the OpenClaw repository's image build target. Record the
final commands here once confirmed from `openclaw/openclaw`.

Expected shape:

```bash
cd ~/oc/openclaw
docker build -t ghcr.io/osolmaz/openclaw:hf-session-fence-test .
docker push ghcr.io/osolmaz/openclaw:hf-session-fence-test
```

## Cleanup

After the fix is merged and the official image includes it:

1. Update the Space Dockerfile back to:

```dockerfile
FROM ghcr.io/openclaw/openclaw:latest
```

2. Rebuild and re-run the Space verification checklist.
3. Delete or deprecate the temporary GHCR tag.
