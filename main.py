import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from transcriber import transcribe
from summarizer import analyze, analyze_split, save_result
from notion_uploader import upload_to_notion

# MP3 128kbps 기준 1분 ≈ 0.94MB, 60분 ≈ 56MB
ONE_HOUR_THRESHOLD_MB = 56


def estimate_duration_min(file_path: Path) -> int:
    """파일 크기로 대략적인 녹음 시간(분) 추정"""
    size_mb = file_path.stat().st_size / (1024 * 1024)
    return int(size_mb / 0.94)


def process_file(file_path: Path):
    """음성 파일 하나를 처리하는 전체 파이프라인"""
    file_path = Path(file_path)
    print(f"\n처리 시작: {file_path.name}")

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    est_min = estimate_duration_min(file_path)
    need_split = file_size_mb > ONE_HOUR_THRESHOLD_MB

    # 음성 파일 생성 날짜 추출 (녹음 날짜)
    file_stat = file_path.stat()
    # macOS: st_birthtime(생성일), 없으면 st_mtime(수정일)
    created_ts = getattr(file_stat, 'st_birthtime', file_stat.st_mtime)
    recording_date = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d")

    # 1) 음성 → 텍스트 (화자 구분 + 용어 보정 포함)
    print("  [1/3] 음성을 텍스트로 변환 중...")
    text = transcribe(file_path)
    print(f"  변환 완료 (글자수: {len(text)}, 추정 {est_min}분)")

    # 2) 텍스트 분석
    if need_split:
        print(f"  [2/3] 1시간 초과 ({est_min}분) — 2개 파일로 분리 분석 중...")
        results = analyze_split(text, est_min)
        print(f"  정리 완료 ({len(results)}개 파트)")
    else:
        print("  [2/3] 텍스트 분석 및 정리 중...")
        results = [analyze(text)]
        print(f"  정리 완료 (주제: {results[0]['subject']})")

    # 3) 파일 저장 + 노션 업로드
    print("  [3/3] 결과 저장 중...")
    output_paths = []
    for result in results:
        output_path = save_result(result)
        output_paths.append(output_path)
        print(f"  텍스트 저장: {output_path}")

        # 노션 업로드
        try:
            notion_url = upload_to_notion(result, recording_date=recording_date)
            if notion_url:
                print(f"  노션 업로드 완료: {notion_url}")
        except Exception as e:
            print(f"  노션 업로드 실패: {e}")

    # 원본 음성파일을 output 폴더로 이동
    first_output = output_paths[0]
    # 분리된 경우 -1 빼고 기본 이름 사용
    base_stem = first_output.stem.rsplit("-1", 1)[0] if need_split else first_output.stem
    audio_new_name = base_stem + file_path.suffix
    dest = config.OUTPUT_DIR / audio_new_name
    counter = 1
    while dest.exists():
        audio_new_name = f"{base_stem}_{counter}{file_path.suffix}"
        dest = config.OUTPUT_DIR / audio_new_name
        counter += 1
    shutil.move(str(file_path), str(dest))
    print(f"  원본 이동: {dest}")

    return output_paths


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
        est = estimate_duration_min(f)
        print(f"  - {f.name} (약 {est}분)")

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
