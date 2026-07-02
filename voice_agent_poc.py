from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, List, Sequence


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
class MicrophoneCaptureResult:
    audio_chunks: List[bytes]
    pipeline_result: PipelineResult


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


def record_microphone_chunks(
    duration_seconds: float,
    sample_rate: int = 16000,
    block_size: int = 1024,
    stream_factory: Callable[..., object] | None = None,
    sleep_fn: Callable[[int], None] | None = None,
) -> List[bytes]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")

    if stream_factory is None or sleep_fn is None:
        import sounddevice as sd

        stream_factory = sd.RawInputStream if stream_factory is None else stream_factory
        sleep_fn = sd.sleep if sleep_fn is None else sleep_fn

    captured_chunks: List[bytes] = []

    def callback(indata: Sequence[bytes] | bytes, frames: int, time_info: object, status: object) -> None:
        del frames, time_info, status
        captured_chunks.append(bytes(indata))

    stream = stream_factory(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=block_size,
        callback=callback,
    )

    with stream if hasattr(stream, "__enter__") else nullcontext(stream):
        sleep_fn(int(duration_seconds * 1000))

    return captured_chunks


def run_microphone_demo(
    transcript_hint: str,
    duration_seconds: float = 2.0,
    sample_rate: int = 16000,
    block_size: int = 1024,
    stream_factory: Callable[..., object] | None = None,
    sleep_fn: Callable[[int], None] | None = None,
) -> MicrophoneCaptureResult:
    audio_chunks = record_microphone_chunks(
        duration_seconds=duration_seconds,
        sample_rate=sample_rate,
        block_size=block_size,
        stream_factory=stream_factory,
        sleep_fn=sleep_fn,
    )
    pipeline_result = run_poc_turn(transcript_hint, chunk_size=24)
    return MicrophoneCaptureResult(audio_chunks=audio_chunks, pipeline_result=pipeline_result)


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run the hospital hotline POC pipeline.")
    parser.add_argument("input", nargs="?", default=None, help="Input text for the POC turn")
    parser.add_argument("--chunk-size", type=int, default=24, help="Chunk size used to simulate streaming ASR")
    parser.add_argument("--mic", action="store_true", help="Capture from microphone before running the POC turn")
    parser.add_argument("--mic-seconds", type=float, default=2.0, help="Microphone capture duration in seconds")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Microphone sample rate")
    parser.add_argument("--block-size", type=int, default=1024, help="Microphone block size")
    args = parser.parse_args()

    input_text = args.input if args.input is not None else sys.stdin.read().strip()
    if not input_text:
        if not args.mic:
            raise SystemExit("Provide input text via argument or stdin, or use --mic.")
        input_text = "Saya ingin daftar di rumah sakit"

    if args.mic:
        mic_result = run_microphone_demo(
            transcript_hint=input_text,
            duration_seconds=args.mic_seconds,
            sample_rate=args.sample_rate,
            block_size=args.block_size,
        )
        print(f"microphone_audio_chunks: {len(mic_result.audio_chunks)}")
        result = mic_result.pipeline_result
    else:
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