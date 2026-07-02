from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List


def chunk_text(text: str, size: int) -> Iterator[str]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    for start in range(0, len(text), size):
        yield text[start : start + size]


class MockAsr:
    def stream(self, chunks: Iterable[str]) -> Iterator[tuple[str, bool]]:
        transcript = ""
        for chunk in chunks:
            transcript += chunk
            yield transcript.strip(), False
        yield transcript.strip(), True


class MockTranslator:
    def __init__(self, direction: str) -> None:
        self.direction = direction

    def translate(self, text: str) -> str:
        if not text:
            return text
        if self.direction == "id_to_llm":
            return text.lower().replace("rumah sakit", "hospital")
        if self.direction == "llm_to_id":
            return text.replace("hospital", "rumah sakit")
        raise ValueError(f"unsupported translation direction: {self.direction}")


class MockLlm:
    def respond(self, prompt: str) -> str:
        normalized = prompt.lower()
        if "jadwal" in normalized or "schedule" in normalized:
            return "Saya bantu cek informasi jadwal layanan rumah sakit."
        if "daftar" in normalized or "register" in normalized:
            return "Silakan siapkan identitas pasien untuk proses pendaftaran."
        return "Terima kasih, saya akan bantu meneruskan informasi ke petugas yang tepat."


class MockTts:
    def synthesize(self, text: str) -> List[str]:
        if not text:
            return []
        return [segment.strip() for segment in text.split(".") if segment.strip()]


@dataclass(frozen=True)
class PipelineResult:
    source_chunks: List[str]
    partial_transcripts: List[str]
    final_transcript: str
    llm_input: str
    llm_output: str
    final_indonesian: str
    tts_frames: List[str]


def run_poc_turn(input_text: str, chunk_size: int = 24) -> PipelineResult:
    source_chunks = list(chunk_text(input_text, chunk_size))
    asr = MockAsr()
    translator_to_llm = MockTranslator("id_to_llm")
    translator_to_id = MockTranslator("llm_to_id")
    llm = MockLlm()
    tts = MockTts()

    partial_transcripts: List[str] = []
    final_transcript = ""
    for partial_transcript, is_final in asr.stream(source_chunks):
        if partial_transcript:
            partial_transcripts.append(partial_transcript)
        if is_final:
            final_transcript = partial_transcript

    llm_input = translator_to_llm.translate(final_transcript)
    llm_output = llm.respond(llm_input)
    final_indonesian = translator_to_id.translate(llm_output)
    tts_frames = tts.synthesize(final_indonesian)

    return PipelineResult(
        source_chunks=source_chunks,
        partial_transcripts=partial_transcripts,
        final_transcript=final_transcript,
        llm_input=llm_input,
        llm_output=llm_output,
        final_indonesian=final_indonesian,
        tts_frames=tts_frames,
    )


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run the hospital hotline POC pipeline.")
    parser.add_argument("input", nargs="?", default=None, help="Input text for the POC turn")
    parser.add_argument("--chunk-size", type=int, default=24, help="Chunk size used to simulate streaming ASR")
    args = parser.parse_args()

    input_text = args.input if args.input is not None else sys.stdin.read().strip()
    if not input_text:
        raise SystemExit("Provide input text via argument or stdin.")

    result = run_poc_turn(input_text, chunk_size=args.chunk_size)

    print("source_chunks:")
    for chunk in result.source_chunks:
        print(f"- {chunk}")
    print("partial_transcripts:")
    for transcript in result.partial_transcripts:
        print(f"- {transcript}")
    print(f"final_transcript: {result.final_transcript}")
    print(f"llm_input: {result.llm_input}")
    print(f"llm_output: {result.llm_output}")
    print(f"final_indonesian: {result.final_indonesian}")
    print("tts_frames:")
    for frame in result.tts_frames:
        print(f"- {frame}")


if __name__ == "__main__":
    main()