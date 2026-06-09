---
title: HF Egress TLS Repro
emoji: 🔎
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
---

# HF Egress TLS Repro

Public repro for outbound TLS behavior from a Hugging Face Docker Space. It
checks DNS, TCP, TLS, fetch, and WebSocket behavior for public endpoints used by
bot/messaging integrations.

Open `/diagnostics` for JSON output.
