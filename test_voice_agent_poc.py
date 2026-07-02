import unittest

from voice_agent_poc import chunk_text, run_poc_turn


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


if __name__ == "__main__":
    unittest.main()