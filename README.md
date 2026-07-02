# VoIP LLM POC

## Quick start

Repository layout:

- `voice-agent-service/` for the isolated voice engine microservice.
- `ui-laravel/` for the Laravel web UI, CRUD, and auth layer.
- The current Python POC remains the reference implementation for the voice path until the service split is fully complete.

Run the web dashboard:

```bash
uvicorn web_app:app --reload
```

Run the POC pipeline with text input:

```bash
python voice_agent_poc.py "Saya ingin daftar di rumah sakit"
```

Run the microphone-first demo:

```bash
python voice_agent_poc.py --mic
```

Run the built-in checks:

```bash
python -m unittest
```

## Laravel migration plan

Laravel is the recommended UI stack for CRUD and simple auth, but it should live in its own `ui-laravel/` app so the voice agent can remain a separate microservice.

Target responsibilities:

- Laravel: dashboard, CRUD, auth, admin views, and orchestration calls.
- Voice service: microphone capture, ASR, translation, LLM, and TTS.
- Communication: HTTP API calls from Laravel to the voice service, not direct coupling inside the web app.
