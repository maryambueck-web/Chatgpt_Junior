# Contributing to Juni SafeChatGPT

Thanks for considering a contribution — this project protects real children, so we're glad for the extra eyes.

## Before you start

- Check open [issues](https://github.com/maryambueck-web/Chatgpt_Junior/issues) and [pull requests](https://github.com/maryambueck-web/Chatgpt_Junior/pulls) to avoid duplicate work.
- For a new feature or a significant change, open an issue first to discuss the approach before writing code.
- For a bug fix, a typo, or a small doc improvement, a PR is fine without a prior issue.

## Development setup

```bash
git clone https://github.com/maryambueck-web/Chatgpt_Junior.git
cd Chatgpt_Junior
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
streamlit run src/app.py
```

See the [README Quick Start](README.md#quick-start) for the Docker option, and [docs/architecture.md](docs/architecture.md) for how the pieces fit together.

## Before opening a PR

```bash
python -m pytest -q      # safety regression suite must pass
./verify.sh               # if you touched Docker/deployment/storage code
```

- **Any change to `src/classifier.py` or `src/policy_engine.py` needs a regression test.** These files decide what a child sees; an untested change here is the highest-risk kind of change in this repo.
- Keep the tone of user-facing copy consistent with Juni's voice: calm, warm, never clinical — except crisis/self-harm responses, which stay deliberately plain and serious.
- After editing any module other than `app.py` itself (e.g. `image_service.py`, `chatgpt_adapter.py`, `shared_store.py`), fully restart `streamlit run` rather than relying on autoreload — see the note in the [README](README.md#quick-start) for why.

## Pull request checklist

- [ ] Tests pass locally (`python -m pytest -q`)
- [ ] New behavior has a regression test
- [ ] README/docs updated if behavior, configuration, or setup steps changed
- [ ] No secrets, API keys, or real `.env` values included in the diff

## Reporting a safety gap

If you find a prompt or phrasing that slips past the safety classifier (a jailbreak, an unsafe response that should have been blocked, etc.), please open an issue with the exact input and expected vs. actual decision — this is exactly the kind of report that improves the project fastest. See [SECURITY.md](SECURITY.md) if the gap could expose real user data rather than a classifier miss.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you're expected to uphold it.
