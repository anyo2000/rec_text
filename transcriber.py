import threading
import time
import shutil
import tempfile
import mimetypes
from pathlib import Path
from google import genai
import config


client = genai.Client(api_key=config.GEMINI_API_KEY)


def _progress_indicator(file_size_mb: float, stop_event: threading.Event):
    """진행 상태 표시"""
    estimated = max(20, int(file_size_mb * 3))
    start = time.time()
    while not stop_event.is_set():
        elapsed = int(time.time() - start)
        print(f"\r    ... {elapsed}s (예상 약 {estimated}s)", end="", flush=True)
        stop_event.wait(3)
    elapsed = int(time.time() - start)
    print(f"\r    ... 완료! ({elapsed}s)                ")


def transcribe(file_path: str | Path) -> str:
    """Gemini API로 음성 파일을 텍스트로 변환"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    if file_path.suffix.lower() not in config.AUDIO_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {file_path.suffix}")

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"  파일 크기: {file_size_mb:.1f}MB")

    # 한글 파일명 대응: 임시 영문 파일명으로 복사
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / f"audio{file_path.suffix}"
    shutil.copy2(str(file_path), str(temp_file))

    # 진행 표시 시작
    stop_event = threading.Event()
    progress = threading.Thread(target=_progress_indicator, args=(file_size_mb, stop_event))
    progress.start()

    try:
        # 파일 업로드
        mime_type = mimetypes.guess_type(str(temp_file))[0] or "audio/mp4"
        uploaded_file = client.files.upload(
            file=temp_file,
            config={"mime_type": mime_type},
        )

        # Gemini로 텍스트 변환
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                uploaded_file,
                "이 음성 파일의 내용을 한국어로 빠짐없이 텍스트로 변환해주세요. "
                "말한 내용을 그대로 받아적되, 문장 부호를 적절히 넣어주세요. "
                "요약하지 말고 전체 내용을 그대로 텍스트로 옮겨주세요."
            ],
        )

        return response.text
    finally:
        stop_event.set()
        progress.join()
        # 임시 파일 정리
        try:
            temp_file.unlink()
            Path(temp_dir).rmdir()
        except Exception:
            pass
