from datetime import date, datetime
from pathlib import Path
from openai import OpenAI
import config


client = OpenAI(api_key=config.OPENAI_API_KEY)

SYSTEM_PROMPT = """\
당신은 음성 녹음을 텍스트로 변환한 내용을 정리하는 전문가입니다.
주어진 텍스트를 분석하여 아래 형식으로 정리해주세요.

규칙:
1. 요약은 1시간 분량 기준 15~30줄로 충분히 상세하게 작성합니다. 짧은 녹음은 비례하여 줄여주세요.
2. 내용의 성격을 자동으로 판별합니다:
   - 상품 교육/설명회/세미나 → "핵심 포인트"로 정리 (기억해야 할 내용, 중요 수치, 특징 등)
   - 회의/업무 대화/일상 메모 → "할 일"로 정리 (TODO, 액션 아이템, 결정사항 등)
3. 주제는 내용을 대표하는 간결한 제목을 추출합니다 (10자 이내 권장).
4. 요약은 마크다운으로 작성합니다. 중요한 키워드나 수치는 **볼드**로 강조해주세요.
5. 핵심 포인트/할 일은 항목별로 구분하고, 중요도가 높은 것에 🔴, 보통은 🟡, 참고용은 🟢 이모지를 붙여주세요.

반드시 아래 형식으로만 응답하세요:

[주제]
(내용을 대표하는 간결한 제목)

[요약]
(마크다운 형식의 상세 요약. 중요 키워드는 **볼드** 처리)

[핵심 포인트] 또는 [할 일]
(중요도 이모지 + 항목별 정리)
"""

ORIGINAL_FORMAT_PROMPT = """\
아래 음성 녹음 텍스트를 보기 좋게 정리해주세요.

규칙:
1. 내용을 의미 단위로 나누어 단락을 구분해주세요 (단락 사이에 빈 줄 넣기).
2. 각 단락 앞에 해당 내용을 대표하는 짧은 소제목을 ### 마크다운으로 붙여주세요.
3. 말의 내용 자체는 변경하지 마세요. 원문 그대로 유지하되 구조만 잡아주세요.
4. "어...", "음...", "그..." 같은 추임새는 제거해주세요.
5. 문장이 너무 길면 적절한 위치에서 줄바꿈해주세요.

원문:
"""


def summarize(text: str) -> dict:
    """텍스트를 GPT API로 분석하여 요약/정리 결과를 반환"""
    response = client.chat.completions.create(
        model=config.GPT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"다음 음성 녹음 텍스트를 정리해주세요:\n\n{text}"},
        ],
    )

    result_text = response.choices[0].message.content
    return _parse_result(result_text, text)


def format_original(text: str) -> str:
    """원문 텍스트를 단락/소제목으로 보기 좋게 정리"""
    print("  [2.5/3] 원문 포맷팅 중...")
    response = client.chat.completions.create(
        model=config.GPT_MODEL,
        messages=[
            {"role": "user", "content": ORIGINAL_FORMAT_PROMPT + text},
        ],
    )
    return response.choices[0].message.content


def _parse_result(result: str, original_text: str) -> dict:
    """GPT 응답을 파싱하여 구조화된 딕셔너리로 변환"""
    sections = {"subject": "", "summary": "", "key_section_title": "", "key_section": "", "original": original_text}

    current_section = None
    lines = result.strip().split("\n")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[주제]"):
            current_section = "subject"
            continue
        elif stripped.startswith("[요약]"):
            current_section = "summary"
            continue
        elif stripped.startswith("[핵심 포인트]"):
            sections["key_section_title"] = "핵심 포인트"
            current_section = "key_section"
            continue
        elif stripped.startswith("[할 일]"):
            sections["key_section_title"] = "할 일"
            current_section = "key_section"
            continue

        if current_section and stripped:
            if current_section == "subject":
                sections["subject"] = stripped
                current_section = None
            else:
                sections[current_section] += line + "\n"

    # 주제가 비어있으면 기본값
    if not sections["subject"]:
        sections["subject"] = "음성메모"

    # 파일명에 사용 불가능한 문자 제거
    sections["subject"] = _sanitize_filename(sections["subject"])

    return sections


def _sanitize_filename(name: str) -> str:
    """파일명에 사용할 수 없는 문자를 제거"""
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "")
    return name.strip()


def save_result(result: dict, output_dir: Path = config.OUTPUT_DIR) -> Path:
    """정리된 결과를 마크다운 파일로 저장"""
    today = date.today().strftime("%Y-%m-%d")
    filename = f"{today}_{result['subject']}.md"
    output_path = output_dir / filename

    # 동일 파일명 존재 시 번호 추가
    counter = 1
    while output_path.exists():
        filename = f"{today}_{result['subject']}_{counter}.md"
        output_path = output_dir / filename
        counter += 1

    title = result.get("key_section_title", "핵심 포인트")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""# 📋 {result['subject']}

> 📅 {now} | 🎙️ 음성 녹음 정리

---

## 📝 요약

{result['summary'].strip()}

---

## {'📌 핵심 포인트' if title == '핵심 포인트' else '✅ 할 일'}

{result['key_section'].strip()}

---

## 🎤 전문 (원문)

{result.get('formatted_original', result['original'])}
"""

    output_path.write_text(content, encoding="utf-8")
    return output_path
