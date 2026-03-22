from __future__ import annotations

import threading
import time
import shutil
import tempfile
import mimetypes
from pathlib import Path
from google import genai
import config


client = genai.Client(api_key=config.GEMINI_API_KEY)

TRANSCRIBE_PROMPT = """\
당신은 한국어 보험업계 회의/교육 음성을 전사하는 전문가입니다.

## 지시사항
1. 음성 파일의 전체 내용을 한국어로 빠짐없이 텍스트로 변환하세요.
2. 서로 다른 화자를 구분하여 "화자1:", "화자2:" 등으로 표시하세요.
   - 화자가 바뀔 때마다 새 줄에 화자 라벨을 붙이세요.
   - 같은 화자가 계속 말하는 경우 라벨을 반복하지 마세요.
3. 보험 용어(상품명, 특약명, 업계 용어 등)는 문맥을 고려하여 정확한 표현으로 전사하세요.
4. 음성이 불명확하거나 목소리가 작은 부분은 전후 맥락을 고려하여 가장 적절한 내용으로 보정하세요.
5. "어...", "음...", "그..." 같은 의미 없는 추임새는 제거하세요.
6. 문장 부호를 적절히 넣되, 요약하지 말고 전체 내용을 그대로 옮기세요.

## 출력 형식
화자1: 말한 내용...
화자2: 응답 내용...
화자1: 이어지는 내용...
"""


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
    """Gemini API로 음성 파일을 텍스트로 변환 (화자 구분 + 용어 보정 포함)"""
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

        # Gemini로 텍스트 변환 (화자 구분 + 용어 보정)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                uploaded_file,
                TRANSCRIBE_PROMPT,
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
