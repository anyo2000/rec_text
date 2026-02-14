import shutil
import sys
from pathlib import Path

# main.py가 있는 폴더를 기준으로 모듈 import
sys.path.insert(0, str(Path(__file__).parent))

import config
from transcriber import transcribe
from summarizer import summarize, format_original, save_result


def process_file(file_path: Path):
    """음성 파일 하나를 처리하는 전체 파이프라인"""
    file_path = Path(file_path)
    print(f"\n처리 시작: {file_path.name}")

    # 1) 음성 → 텍스트
    print("  [1/3] 음성을 텍스트로 변환 중...")
    text = transcribe(file_path)
    print(f"  변환 완료 (글자수: {len(text)})")

    # 2) 텍스트 정리 (요약 + 핵심포인트)
    print("  [2/4] 텍스트 정리 중 (GPT)...")
    result = summarize(text)
    print(f"  정리 완료 (주제: {result['subject']})")

    # 3) 원문 포맷팅 (단락/소제목 추가)
    print("  [3/4] 원문 보기좋게 정리 중...")
    result['formatted_original'] = format_original(text)
    print("  원문 정리 완료")

    # 4) 파일 저장
    print("  [4/4] 결과 저장 중...")
    output_path = save_result(result)
    print(f"  텍스트 저장: {output_path}")

    # 5) 원본 음성파일도 output 폴더로 이동 (텍스트파일과 같은 이름)
    audio_new_name = output_path.stem + file_path.suffix  # 예: 2026-02-15_상품교육.m4a
    dest = config.OUTPUT_DIR / audio_new_name
    shutil.move(str(file_path), str(dest))
    print(f"  원본 이동: {dest}")

    return output_path


def main():
    """input 폴더 안의 모든 음성 파일을 처리"""
    audio_files = [
        f for f in config.INPUT_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in config.AUDIO_EXTENSIONS
    ]

    if not audio_files:
        print("input 폴더에 음성 파일이 없습니다.")
        print(f"  폴더 위치: {config.INPUT_DIR}")
        input("\n아무 키나 누르면 종료...")
        return

    print(f"발견된 음성 파일: {len(audio_files)}개")
    for f in audio_files:
        print(f"  - {f.name}")

    print("\n변환을 시작합니다...")

    success = 0
    for file_path in audio_files:
        try:
            process_file(file_path)
            success += 1
        except Exception as e:
            print(f"\n  오류 발생 ({file_path.name}): {e}")

    print(f"\n===== 완료 =====")
    print(f"  성공: {success}/{len(audio_files)}개")
    print(f"  결과 폴더: {config.OUTPUT_DIR}")
    input("\n아무 키나 누르면 종료...")


if __name__ == "__main__":
    main()
