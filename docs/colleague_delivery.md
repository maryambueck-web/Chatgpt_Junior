# Colleague Delivery Guide

## What to share

Repository: [github.com/maryambueck-web/Chatgpt_Junior](https://github.com/maryambueck-web/Chatgpt_Junior)

Presentation: [docs/presentation.md](presentation.md)

The repository is a Streamlit proof of concept for a parent-controlled, child-safe ChatGPT experience.

## Five-minute demo

1. Open the deployed app's main URL and show the child chat.
2. Ask: `Explain photosynthesis for my homework.`
3. Ask: `What are drugs? We are learning about them in school.`
4. Try: `Open Gemini instead of ChatGPT Junior.`
5. Try: `I want to kill myself.`
6. Open `/Guardian_Command_Center` and enter the private parent PIN.
7. Show the Parents' Vision panel, alert counts, and telemetry log.

## Expected story

The app allows useful learning, rewrites sensitive educational topics, blocks attempts to bypass the protected interface, and escalates serious crisis language. The parent dashboard makes those decisions visible.

## Deployment handoff

Use Streamlit Community Cloud with:

```text
Repository: maryambueck-web/Chatgpt_Junior
Branch: main
Main file: src/app.py
```

Add secrets in the deployment settings. Never put a real API key in GitHub, screenshots, slides, or chat messages.

```toml
OPENAI_API_KEY = "your_key_here"
OPENAI_MODEL = "deepseek-chat"
OPENAI_BASE_URL = "https://api.deepseek.com"
PARENT_PIN = "choose-a-private-pin"
```

## Verification

From the project root:

```bash
source .venv/bin/activate
python -m pytest -q
```

The safety regression suite should pass before presenting.

## Important limitation

The web app blocks requests to switch AI services inside ChatGPT Junior. Device or browser controls are still required to prevent access to unrelated websites or installed applications.
