# Local development and testing

## Requirements

- Python 3.12 (Render uses 3.12.8)
- FFmpeg available on `PATH`
- A Telegram bot token to run the live application

## Install

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
~~~

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Environment

~~~bash
export BOT_TOKEN="your-bot-token"
export WEBHOOK_SECRET="a-long-random-secret"
~~~

Start the local server:

~~~bash
PYTHONPATH=src uvicorn instadlbot.app:app --host 0.0.0.0 --port 8000
~~~

Check `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/health`.

For real Telegram updates, expose the server through an HTTPS tunnel and set `RENDER_EXTERNAL_URL` to the public HTTPS base URL before startup.

## Tests

~~~bash
pytest -q
~~~

`pyproject.toml` adds `src` to pytest's import path and discovers tests in `tests/`. `tests/conftest.py` supplies placeholder required environment values for import-time configuration. The current unit tests do not require live Telegram credentials.

## Project conventions

- Application source: `src/instadlbot/`
- Automated tests: `tests/`
- Technical documentation: `docs/`
- Runtime dependencies: `requirements.txt`
- Development tools: `requirements-dev.txt`
- Keep credentials and downloaded content out of Git.
- Preserve the single-worker deployment model unless the in-memory queue and Telegram application lifecycle are redesigned.
