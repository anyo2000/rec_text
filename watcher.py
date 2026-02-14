import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import config


class AudioFileHandler(FileSystemEventHandler):
    """input 폴더에 새로운 음성 파일이 추가되면 처리"""

    def __init__(self, process_func):
        self.process_func = process_func

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() not in config.AUDIO_EXTENSIONS:
            return

        # 파일 복사가 완료될 때까지 대기
        self._wait_for_copy(file_path)
        print(f"\n새 파일 감지: {file_path.name}")
        self.process_func(file_path)

    def _wait_for_copy(self, file_path: Path, timeout: int = 120):
        """파일 복사/전송 완료까지 대기 (크기 변화가 없을 때까지)"""
        prev_size = -1
        stable_count = 0
        elapsed = 0

        while elapsed < timeout:
            try:
                current_size = file_path.stat().st_size
            except OSError:
                time.sleep(1)
                elapsed += 1
                continue

            if current_size == prev_size and current_size > 0:
                stable_count += 1
                if stable_count >= 3:
                    return
            else:
                stable_count = 0

            prev_size = current_size
            time.sleep(1)
            elapsed += 1


def start_watching(process_func):
    """input 폴더를 감시하여 새 음성 파일 자동 처리"""
    observer = Observer()
    handler = AudioFileHandler(process_func)
    observer.schedule(handler, str(config.INPUT_DIR), recursive=False)
    observer.start()

    print(f"폴더 감시 시작: {config.INPUT_DIR}")
    print("음성 파일을 input 폴더에 넣으면 자동으로 처리됩니다.")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n폴더 감시를 종료합니다.")

    observer.join()
