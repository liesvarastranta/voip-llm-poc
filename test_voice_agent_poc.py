import unittest

from voice_agent_poc import chunk_text, record_microphone_chunks, run_poc_turn


class VoiceAgentPocTests(unittest.TestCase):
    def test_chunk_text_splits_incrementally(self) -> None:
        self.assertEqual(list(chunk_text("abcdef", 2)), ["ab", "cd", "ef"])

    def test_pipeline_runs_end_to_end(self) -> None:
        result = run_poc_turn("Saya ingin daftar di rumah sakit", chunk_size=7)

        self.assertGreater(len(result.source_chunks), 1)
        self.assertTrue(result.partial_transcripts)
        self.assertEqual(result.final_transcript, "Saya ingin daftar di rumah sakit")
        self.assertIn("hospital", result.llm_input)
        self.assertTrue(result.llm_output)
        self.assertTrue(result.final_indonesian)
        self.assertTrue(result.tts_frames)

    def test_record_microphone_chunks_supports_injected_stream(self) -> None:
        captured_kwargs = {}

        def fake_stream_factory(**kwargs):
            captured_kwargs.update(kwargs)

            class FakeStream:
                def __enter__(self):
                    callback = kwargs["callback"]
                    callback(b"abc", 3, None, None)
                    callback(b"def", 3, None, None)
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            return FakeStream()

        def fake_sleep(milliseconds: int) -> None:
            self.assertEqual(milliseconds, 100)

        chunks = record_microphone_chunks(
            duration_seconds=0.1,
            sample_rate=16000,
            block_size=256,
            stream_factory=fake_stream_factory,
            sleep_fn=fake_sleep,
        )

        self.assertEqual(chunks, [b"abc", b"def"])
        self.assertEqual(captured_kwargs["samplerate"], 16000)
        self.assertEqual(captured_kwargs["channels"], 1)
        self.assertEqual(captured_kwargs["dtype"], "int16")
        self.assertEqual(captured_kwargs["blocksize"], 256)


if __name__ == "__main__":
    unittest.main()