import unittest

from voice_agent_poc import MicrophoneCaptureResult, PipelineResult
from web_app import DemoRequest, build_demo_payload, render_page, serialize_pipeline_result


class WebAppTests(unittest.TestCase):
    def test_serialize_pipeline_result(self) -> None:
        result = PipelineResult(
            source_chunks=["sa", "ya"],
            partial_transcripts=["sa", "saya"],
            final_transcript="saya",
            llm_input="saya",
            llm_output="jawaban",
            final_indonesian="jawaban",
            tts_frames=["jawaban"],
        )

        payload = serialize_pipeline_result(result)

        self.assertEqual(payload["final_transcript"], "saya")
        self.assertEqual(payload["tts_frames"], ["jawaban"])

    def test_build_demo_payload_text_mode(self) -> None:
        def fake_turn_runner(input_text: str, chunk_size: int) -> PipelineResult:
            self.assertEqual(input_text, "halo")
            self.assertEqual(chunk_size, 12)
            return PipelineResult(
                source_chunks=["ha", "lo"],
                partial_transcripts=["ha", "halo"],
                final_transcript="halo",
                llm_input="halo",
                llm_output="jawaban",
                final_indonesian="jawaban",
                tts_frames=["jawaban"],
            )

        payload = build_demo_payload(
            DemoRequest(mode="text", input_text="halo", chunk_size=12),
            turn_runner=fake_turn_runner,
        )

        self.assertEqual(payload["mode"], "text")
        self.assertEqual(payload["pipeline"]["final_transcript"], "halo")

    def test_build_demo_payload_microphone_mode(self) -> None:
        def fake_microphone_runner(**kwargs) -> MicrophoneCaptureResult:
            self.assertEqual(kwargs["transcript_hint"], "halo")
            self.assertEqual(kwargs["duration_seconds"], 1.5)
            self.assertEqual(kwargs["sample_rate"], 16000)
            self.assertEqual(kwargs["block_size"], 512)
            return MicrophoneCaptureResult(
                audio_chunks=[b"abc", b"def"],
                pipeline_result=PipelineResult(
                    source_chunks=["ha", "lo"],
                    partial_transcripts=["ha", "halo"],
                    final_transcript="halo",
                    llm_input="halo",
                    llm_output="jawaban",
                    final_indonesian="jawaban",
                    tts_frames=["jawaban"],
                ),
            )

        payload = build_demo_payload(
            DemoRequest(
                mode="microphone",
                input_text="halo",
                mic_seconds=1.5,
                sample_rate=16000,
                block_size=512,
            ),
            microphone_runner=fake_microphone_runner,
        )

        self.assertEqual(payload["mode"], "microphone")
        self.assertEqual(payload["microphone_audio_chunks"], 2)
        self.assertEqual(payload["pipeline"]["final_transcript"], "halo")

    def test_render_page_contains_web_controls(self) -> None:
        html = render_page()

        self.assertIn("VoIP LLM POC Dashboard", html)
        self.assertIn("/api/demo", html)
        self.assertIn("Browser microphone preview", html)


if __name__ == "__main__":
    unittest.main()