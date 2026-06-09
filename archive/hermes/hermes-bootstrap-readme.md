# Hermes Agent Bootstrap Local Patch

Local-only patched copy of Merve's Hermes Agent bootstrap script.

The only behavioral change is that `bootstrap.sh` reads the Hugging Face token from:

```bash
hf auth token
```

instead of importing `huggingface_hub` from the system `python3`.

Run:

```bash
bash /Users/onur/repos/hermes-agent-bootstrap-local/bootstrap.sh
```
