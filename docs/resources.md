# Resources

## Hugging Face Spaces

```text
osolmaz/openclaw-huggingface
```

Generic Docker Space template for OpenClaw on Hugging Face.

```text
osolmaz/onurclawtest
```

Private test Space used with a Telegram bot during verification.

```text
osolmaz/hf-egress-tls-repro
```

Public diagnostic Space used to test outbound DNS, TCP, TLS, fetch, and
WebSocket behavior from Hugging Face runtimes.

```text
osolmaz/openclaw-bootstrap
```

Merve-style bootstrap repo/Space work. Kept as historical context while the
tracking repo records the broader Hugging Face deployment effort.

## Hugging Face Buckets

```text
osolmaz/onurclawtest-data
```

Private bucket mounted at `/data` for the `osolmaz/onurclawtest` Space.

## GitHub

```text
osolmaz/openclaw-on-huggingface
```

This tracking repo.

```text
openclaw/openclaw
```

Correct location for the OpenClaw runtime/session-lock fix.

## Container Images

Current Space template base image:

```text
ghcr.io/openclaw/openclaw:latest
```

Planned temporary test image:

```text
ghcr.io/osolmaz/openclaw:hf-session-fence-test
```

The temporary image is only for verifying the OpenClaw fix on Hugging Face
Spaces before the upstream `latest` image contains the fix.
