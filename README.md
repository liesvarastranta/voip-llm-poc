# VoIP LLM POC

## Quick start

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
