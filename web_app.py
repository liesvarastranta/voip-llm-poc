from __future__ import annotations

from html import escape
from textwrap import dedent
from typing import Any, Callable, Dict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from voice_agent_poc import MicrophoneCaptureResult, PipelineResult, run_microphone_demo, run_poc_turn

app = FastAPI(title="VoIP LLM POC", version="0.1.0")

DEFAULT_TEXT_INPUT = "Saya ingin daftar di rumah sakit"


class DemoRequest(BaseModel):
    mode: str = Field(default="text", pattern="^(text|microphone)$")
    input_text: str = Field(default=DEFAULT_TEXT_INPUT)
    chunk_size: int = Field(default=24, ge=1, le=256)
    mic_seconds: float = Field(default=2.0, gt=0, le=30)
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    block_size: int = Field(default=1024, ge=64, le=8192)


def serialize_pipeline_result(result: PipelineResult) -> Dict[str, Any]:
    return {
        "source_chunks": result.source_chunks,
        "partial_transcripts": result.partial_transcripts,
        "final_transcript": result.final_transcript,
        "llm_input": result.llm_input,
        "llm_output": result.llm_output,
        "final_indonesian": result.final_indonesian,
        "tts_frames": result.tts_frames,
    }


def build_demo_payload(
    request: DemoRequest,
    turn_runner: Callable[[str, int], PipelineResult] = run_poc_turn,
    microphone_runner: Callable[..., MicrophoneCaptureResult] = run_microphone_demo,
) -> Dict[str, Any]:
    if request.mode == "microphone":
        mic_result = microphone_runner(
            transcript_hint=request.input_text,
            duration_seconds=request.mic_seconds,
            sample_rate=request.sample_rate,
            block_size=request.block_size,
        )
        return {
            "mode": request.mode,
            "input_text": request.input_text,
            "microphone_audio_chunks": len(mic_result.audio_chunks),
            "pipeline": serialize_pipeline_result(mic_result.pipeline_result),
        }

    result = turn_runner(request.input_text, request.chunk_size)
    return {
        "mode": request.mode,
        "input_text": request.input_text,
        "microphone_audio_chunks": 0,
        "pipeline": serialize_pipeline_result(result),
    }


def render_page() -> str:
    return dedent(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>VoIP LLM POC Dashboard</title>
          <style>
            :root {
              color-scheme: dark;
              --bg: #07111f;
              --panel: rgba(8, 18, 34, 0.84);
              --panel-strong: #0d1d33;
              --border: rgba(174, 195, 221, 0.18);
              --text: #e9f0fb;
              --muted: #9fb0c9;
              --accent: #63d9c4;
              --accent-2: #f4b860;
              --danger: #ff8c8c;
              --shadow: 0 18px 60px rgba(0, 0, 0, 0.38);
            }

            * { box-sizing: border-box; }

            body {
              margin: 0;
              font-family: "Avenir Next", "Segoe UI", "Trebuchet MS", sans-serif;
              background:
                radial-gradient(circle at top left, rgba(99, 217, 196, 0.18), transparent 28%),
                radial-gradient(circle at right 18%, rgba(244, 184, 96, 0.12), transparent 24%),
                linear-gradient(180deg, #09111c 0%, #07111f 100%);
              color: var(--text);
              min-height: 100vh;
            }

            .shell {
              max-width: 1320px;
              margin: 0 auto;
              padding: 32px 20px 48px;
            }

            .hero {
              display: grid;
              grid-template-columns: 1.4fr 0.9fr;
              gap: 20px;
              align-items: stretch;
            }

            .banner, .panel, .metric, .result-card {
              background: var(--panel);
              border: 1px solid var(--border);
              border-radius: 22px;
              box-shadow: var(--shadow);
              backdrop-filter: blur(16px);
            }

            .banner {
              padding: 28px;
              overflow: hidden;
              position: relative;
            }

            .banner::after {
              content: "";
              position: absolute;
              inset: auto -40px -70px auto;
              width: 220px;
              height: 220px;
              border-radius: 50%;
              background: radial-gradient(circle, rgba(99, 217, 196, 0.3), transparent 68%);
            }

            .eyebrow {
              display: inline-flex;
              align-items: center;
              gap: 8px;
              padding: 7px 12px;
              border-radius: 999px;
              background: rgba(99, 217, 196, 0.12);
              border: 1px solid rgba(99, 217, 196, 0.22);
              color: var(--accent);
              font-size: 12px;
              letter-spacing: 0.12em;
              text-transform: uppercase;
              font-weight: 700;
            }

            h1 {
              margin: 16px 0 10px;
              font-size: clamp(34px, 5vw, 58px);
              line-height: 0.98;
              letter-spacing: -0.04em;
            }

            .lede {
              max-width: 64ch;
              color: var(--muted);
              font-size: 16px;
              line-height: 1.7;
              margin: 0;
            }

            .stats {
              display: grid;
              grid-template-columns: repeat(3, minmax(0, 1fr));
              gap: 14px;
              margin-top: 18px;
            }

            .metric {
              padding: 16px 18px;
            }

            .metric span {
              display: block;
              color: var(--muted);
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 0.12em;
              margin-bottom: 10px;
            }

            .metric strong {
              font-size: 18px;
              color: var(--text);
            }

            .panel-grid {
              display: grid;
              grid-template-columns: 380px 1fr;
              gap: 20px;
              margin-top: 20px;
            }

            .panel {
              padding: 20px;
            }

            .panel h2 {
              margin: 0 0 6px;
              font-size: 20px;
            }

            .panel p.note {
              margin: 0 0 18px;
              color: var(--muted);
              line-height: 1.6;
            }

            label {
              display: block;
              font-size: 12px;
              color: var(--muted);
              text-transform: uppercase;
              letter-spacing: 0.12em;
              margin-bottom: 8px;
            }

            input, select, button, textarea {
              width: 100%;
              border-radius: 14px;
              border: 1px solid rgba(174, 195, 221, 0.18);
              background: rgba(4, 10, 18, 0.7);
              color: var(--text);
              padding: 12px 14px;
              font: inherit;
            }

            textarea { min-height: 112px; resize: vertical; }

            .field { margin-bottom: 14px; }

            .row {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 12px;
            }

            .actions {
              display: flex;
              gap: 12px;
              margin-top: 12px;
            }

            button {
              cursor: pointer;
              font-weight: 700;
              border: 0;
              background: linear-gradient(135deg, var(--accent), #4ca6ff);
              color: #031118;
              transition: transform 0.18s ease, filter 0.18s ease;
            }

            button.secondary {
              background: rgba(255, 255, 255, 0.08);
              color: var(--text);
              border: 1px solid var(--border);
            }

            button:hover { transform: translateY(-1px); filter: brightness(1.03); }

            .results {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 16px;
            }

            .result-card {
              padding: 16px;
              min-height: 150px;
            }

            .result-card h3 {
              margin: 0 0 10px;
              font-size: 14px;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              color: var(--accent);
            }

            .chips {
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
            }

            .chip {
              padding: 8px 10px;
              border-radius: 999px;
              background: rgba(99, 217, 196, 0.11);
              border: 1px solid rgba(99, 217, 196, 0.18);
              color: var(--text);
              font-size: 13px;
            }

            pre {
              margin: 0;
              white-space: pre-wrap;
              word-break: break-word;
              color: var(--text);
              line-height: 1.6;
            }

            .status {
              margin-top: 12px;
              color: var(--muted);
              min-height: 24px;
            }

            .browser-preview {
              margin-top: 18px;
              padding-top: 16px;
              border-top: 1px solid rgba(174, 195, 221, 0.12);
            }

            .browser-preview video, .browser-preview audio {
              width: 100%;
              margin-top: 12px;
              border-radius: 14px;
            }

            .timeline {
              display: grid;
              gap: 10px;
            }

            .step {
              display: grid;
              grid-template-columns: 24px 1fr;
              gap: 12px;
              align-items: start;
              padding: 12px 0;
              border-bottom: 1px solid rgba(174, 195, 221, 0.08);
            }

            .step:last-child { border-bottom: 0; }

            .step .dot {
              width: 14px;
              height: 14px;
              border-radius: 999px;
              margin-top: 4px;
              background: linear-gradient(180deg, var(--accent), var(--accent-2));
              box-shadow: 0 0 0 4px rgba(99, 217, 196, 0.12);
            }

            .step strong { display: block; margin-bottom: 4px; }

            @media (max-width: 1080px) {
              .hero, .panel-grid, .results, .stats { grid-template-columns: 1fr; }
            }

            @media (max-width: 720px) {
              .shell { padding: 18px 14px 34px; }
              .actions, .row { grid-template-columns: 1fr; flex-direction: column; }
              .actions { display: grid; }
            }
          </style>
        </head>
        <body>
          <main class="shell">
            <section class="hero">
              <div class="banner">
                <span class="eyebrow">On-premise POC dashboard</span>
                <h1>Hospital VoIP voice agent, visible in a browser.</h1>
                <p class="lede">This dashboard keeps the current POC intentionally small: microphone-first validation, chunked ASR simulation, translation, LLM response, and TTS segmentation. The browser page is only the viewing layer; the pipeline remains local.</p>
                <div class="stats">
                  <div class="metric"><span>Mode</span><strong>Text or microphone demo</strong></div>
                  <div class="metric"><span>Stack</span><strong>FastAPI + plain HTML + JS</strong></div>
                  <div class="metric"><span>Scope</span><strong>Minimal, on-prem, reviewable</strong></div>
                </div>
              </div>
              <div class="banner">
                <span class="eyebrow">Implementation flow</span>
                <div class="timeline" id="timeline">
                  <div class="step"><div class="dot"></div><div><strong>Audio source</strong><span>Text input or local microphone capture.</span></div></div>
                  <div class="step"><div class="dot"></div><div><strong>ASR chunks</strong><span>Transcript grows incrementally per chunk.</span></div></div>
                  <div class="step"><div class="dot"></div><div><strong>Translate + LLM</strong><span>Mock translation and hospital response are visible.</span></div></div>
                  <div class="step"><div class="dot"></div><div><strong>TTS frames</strong><span>Final response is split into playback-ready frames.</span></div></div>
                </div>
              </div>
            </section>

            <section class="panel-grid">
              <div class="panel">
                <h2>Run the POC</h2>
                <p class="note">Use the buttons below to run the baseline pipeline, or preview a browser microphone capture. The backend microphone demo still uses the local machine microphone through the configured Python environment.</p>

                <div class="field">
                  <label for="mode">Demo mode</label>
                  <select id="mode">
                    <option value="text">Text demo</option>
                    <option value="microphone">Microphone demo</option>
                  </select>
                </div>

                <div class="field">
                  <label for="input_text">Prompt / transcript hint</label>
                  <textarea id="input_text">Saya ingin daftar di rumah sakit</textarea>
                </div>

                <div class="row">
                  <div class="field">
                    <label for="chunk_size">Chunk size</label>
                    <input id="chunk_size" type="number" min="1" max="256" value="24" />
                  </div>
                  <div class="field">
                    <label for="mic_seconds">Mic seconds</label>
                    <input id="mic_seconds" type="number" min="0.1" max="30" step="0.1" value="2.0" />
                  </div>
                </div>

                <div class="row">
                  <div class="field">
                    <label for="sample_rate">Sample rate</label>
                    <input id="sample_rate" type="number" min="8000" max="48000" value="16000" />
                  </div>
                  <div class="field">
                    <label for="block_size">Block size</label>
                    <input id="block_size" type="number" min="64" max="8192" value="1024" />
                  </div>
                </div>

                <div class="actions">
                  <button id="run_btn" type="button">Run demo</button>
                  <button id="clear_btn" class="secondary" type="button">Clear</button>
                </div>

                <div class="browser-preview">
                  <h2 style="margin-top:0;">Browser microphone preview</h2>
                  <p class="note">This is only a visual preview in the browser. It helps confirm the website can access local microphone input while the backend pipeline remains separate.</p>
                  <div class="actions">
                    <button id="browser_mic_start" type="button">Start browser mic</button>
                    <button id="browser_mic_stop" class="secondary" type="button" disabled>Stop</button>
                  </div>
                  <div class="status" id="browser_mic_status">Idle.</div>
                  <audio id="browser_mic_playback" controls></audio>
                </div>
              </div>

              <div class="panel">
                <h2>Pipeline output</h2>
                <p class="note">The result cards below are filled from the local pipeline, so you can inspect the ASR chunking path and the final TTS segmentation from a browser.</p>
                <div class="results" id="results">
                  <div class="result-card"><h3>Source chunks</h3><pre id="source_chunks">No run yet.</pre></div>
                  <div class="result-card"><h3>Partial transcripts</h3><pre id="partial_transcripts">No run yet.</pre></div>
                  <div class="result-card"><h3>Final transcript</h3><pre id="final_transcript">No run yet.</pre></div>
                  <div class="result-card"><h3>LLM input</h3><pre id="llm_input">No run yet.</pre></div>
                  <div class="result-card"><h3>LLM output</h3><pre id="llm_output">No run yet.</pre></div>
                  <div class="result-card"><h3>Final Indonesian</h3><pre id="final_indonesian">No run yet.</pre></div>
                  <div class="result-card" style="grid-column: 1 / -1;"><h3>TTS frames</h3><div class="chips" id="tts_frames"></div></div>
                </div>
                <div class="status" id="status">Ready.</div>
              </div>
            </section>
          </main>

          <script>
            const $ = (id) => document.getElementById(id);
            const state = { stream: null, recorder: null, chunks: [] };

            function setStatus(message) {
              $("status").textContent = message;
            }

            function setBrowserStatus(message) {
              $("browser_mic_status").textContent = message;
            }

            function clearResults() {
              $("source_chunks").textContent = "No run yet.";
              $("partial_transcripts").textContent = "No run yet.";
              $("final_transcript").textContent = "No run yet.";
              $("llm_input").textContent = "No run yet.";
              $("llm_output").textContent = "No run yet.";
              $("final_indonesian").textContent = "No run yet.";
              $("tts_frames").innerHTML = "";
              setStatus("Ready.");
            }

            function renderList(items) {
              return Array.isArray(items) ? items.map((item) => `- ${item}`).join("\n") : "";
            }

            function renderChips(items) {
              return Array.isArray(items) ? items.map((item) => `<span class="chip">${item}</span>`).join("") : "";
            }

            async function runDemo() {
              const payload = {
                mode: $("mode").value,
                input_text: $("input_text").value,
                chunk_size: Number($("chunk_size").value),
                mic_seconds: Number($("mic_seconds").value),
                sample_rate: Number($("sample_rate").value),
                block_size: Number($("block_size").value),
              };

              setStatus("Running demo locally...");
              const response = await fetch("/api/demo", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
              });

              if (!response.ok) {
                const error = await response.text();
                throw new Error(error || `Request failed: ${response.status}`);
              }

              const data = await response.json();
              const pipeline = data.pipeline;
              $("source_chunks").textContent = renderList(pipeline.source_chunks);
              $("partial_transcripts").textContent = renderList(pipeline.partial_transcripts);
              $("final_transcript").textContent = pipeline.final_transcript || "";
              $("llm_input").textContent = pipeline.llm_input || "";
              $("llm_output").textContent = pipeline.llm_output || "";
              $("final_indonesian").textContent = pipeline.final_indonesian || "";
              $("tts_frames").innerHTML = renderChips(pipeline.tts_frames);

              const modeLabel = data.mode === "microphone" ? `microphone (${data.microphone_audio_chunks} audio chunks)` : "text";
              setStatus(`Completed ${modeLabel} run.`);
            }

            async function startBrowserMic() {
              state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
              state.chunks = [];
              const options = MediaRecorder.isTypeSupported("audio/webm") ? { mimeType: "audio/webm" } : undefined;
              state.recorder = new MediaRecorder(state.stream, options);
              state.recorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                  state.chunks.push(event.data);
                }
              };
              state.recorder.onstop = () => {
                const blob = new Blob(state.chunks, { type: state.recorder.mimeType || "audio/webm" });
                const url = URL.createObjectURL(blob);
                $("browser_mic_playback").src = url;
                setBrowserStatus(`Captured ${Math.round(blob.size / 1024)} KB of browser microphone audio.`);
                $("browser_mic_start").disabled = false;
                $("browser_mic_stop").disabled = true;
              };
              state.recorder.start();
              setBrowserStatus("Recording from browser microphone...");
              $("browser_mic_start").disabled = true;
              $("browser_mic_stop").disabled = false;
            }

            function stopBrowserMic() {
              if (state.recorder && state.recorder.state !== "inactive") {
                state.recorder.stop();
              }
              if (state.stream) {
                state.stream.getTracks().forEach((track) => track.stop());
                state.stream = null;
              }
            }

            $("run_btn").addEventListener("click", async () => {
              try {
                await runDemo();
              } catch (error) {
                setStatus(`Error: ${error.message}`);
              }
            });

            $("clear_btn").addEventListener("click", clearResults);
            $("browser_mic_start").addEventListener("click", async () => {
              try {
                await startBrowserMic();
              } catch (error) {
                setBrowserStatus(`Browser microphone error: ${error.message}`);
              }
            });
            $("browser_mic_stop").addEventListener("click", stopBrowserMic);
          </script>
        </body>
        </html>
        """
    ).strip()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return render_page()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/demo")
def api_demo(request: DemoRequest) -> Dict[str, Any]:
    return build_demo_payload(request)
