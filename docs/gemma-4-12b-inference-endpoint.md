# Gemma 4 12B via Hugging Face Inference Endpoints

Date: 2026-06-09

This note records what is needed to run OpenClaw on `google/gemma-4-12B-it`
from Hugging Face.

## Summary

`google/gemma-4-12B-it` exists on the Hugging Face Hub, but it is not currently
usable through the shared Hugging Face Router chat endpoint used by the test
Space:

```text
https://router.huggingface.co/v1/chat/completions
```

A direct router request returned:

```text
The requested model 'google/gemma-4-12B-it' is not a chat model.
```

This means the model is not exposed by the enabled Hugging Face Inference
Providers as an OpenAI-compatible chat-completion model. It does not mean the
model weights cannot generate text.

The production path is to deploy a dedicated Hugging Face Inference Endpoint for
the model and serve it with an OpenAI-compatible chat API.

## Required Architecture

OpenClaw expects a chat-completions API. To use Gemma 4 12B, the endpoint must
serve:

```text
POST /v1/chat/completions
```

The likely serving options are:

- Hugging Face Inference Endpoint with TGI.
- Hugging Face Inference Endpoint with vLLM.

TGI documents an OpenAI-compatible messages API at `/v1/chat/completions`:

```text
https://huggingface.co/docs/text-generation-inference/messages_api
```

Hugging Face documents TGI as an Inference Endpoints engine:

```text
https://huggingface.co/docs/inference-endpoints/main/en/engines/tgi
```

## Endpoint Creation Flow

Use the Hugging Face Inference Endpoints UI:

```text
https://endpoints.huggingface.co/
```

Create a new private endpoint with:

```text
Model:      google/gemma-4-12B-it
Engine:     vLLM first if available, otherwise TGI
Task:       Text Generation or the model-specific generation task shown by HF
Hardware:   GPU hardware large enough for a 12B model
Visibility: Private
Scaling:    Enable scale-to-zero if idle cost matters
```

The exact hardware should be selected from the configurations Hugging Face
offers for the model. Expect this to require paid GPU capacity.

## Endpoint Verification

After the endpoint is live, test the OpenAI-compatible chat API before changing
OpenClaw:

```bash
curl "https://<endpoint>.endpoints.huggingface.cloud/v1/chat/completions" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tgi",
    "messages": [{"role": "user", "content": "Reply exactly: ok"}],
    "max_tokens": 8
  }'
```

The endpoint is usable by OpenClaw only if this returns a normal chat-completion
response.

Some serving engines ignore the `model` field. Others require a specific value.
If `"tgi"` fails, inspect the endpoint docs/logs or try the deployed model id:

```text
google/gemma-4-12B-it
```

## OpenClaw Space Configuration

Once the endpoint test succeeds, update the Space variables:

```bash
hf spaces variables add osolmaz/onurclawtest \
  -e OPENCLAW_MODEL_BASE_URL=https://<endpoint>.endpoints.huggingface.cloud/v1 \
  -e OPENCLAW_MODEL=huggingface/tgi
```

Restart the Space if the variable update does not restart it automatically:

```bash
hf spaces restart osolmaz/onurclawtest
```

Then verify the logs:

```bash
hf spaces logs osolmaz/onurclawtest -n 120
```

Expected signal:

```text
[gateway] agent model: huggingface/tgi
```

Also send a Telegram message and confirm the model replies without the generic
OpenClaw error response.

## Current Findings

The shared Hugging Face Router rejected these models on 2026-06-09:

```text
google/gemma-4-12B-it
google/gemma-4-12B-it-assistant
google/gemma-4-12B
huihui-ai/Huihui-gemma-4-12B-it-abliterated
```

`google/gemma-3-27b-it` did work through the shared router chat endpoint in a
direct test:

```text
https://router.huggingface.co/v1/chat/completions
```

So the short-term choices are:

- Keep using `huggingface/Qwen/Qwen3-8B` through the shared router.
- Switch to `huggingface/google/gemma-3-27b-it` through the shared router.
- Deploy a dedicated endpoint for `google/gemma-4-12B-it` and point OpenClaw at
  that endpoint.

## Caveat

The Hugging Face endpoint catalog CLI did not show `google/gemma-4-12B-it` as a
ready-made catalog preset on 2026-06-09. It did show other Gemma 4 entries.
Therefore exact 12B deployment may require a custom endpoint configuration, and
Hugging Face may reject a runtime/hardware combination that it cannot serve.
