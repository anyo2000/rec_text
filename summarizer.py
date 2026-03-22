from datetime import date, datetime
from pathlib import Path
from google import genai
import config


client = genai.Client(api_key=config.GEMINI_API_KEY)

ANALYZE_PROMPT = """\
당신은 보험업계 전속영업부문(채널/FP) 관점에서 회의/교육 내용을 정리하는 전문가입니다.

아래 화자 구분된 회의록을 분석하여 정리하세요.

## 규칙

### 메타데이터
- **제목**: 회의/교육명 - 핵심키워드 형식. 날짜, 시간, 괄호 사용 금지. 간결하게. (예: 상품전략회의 - 로봇수술)
- **주제**: 핵심 키워드 3~5개를 쉼표로 나열. 문장으로 쓰지 말 것. (예: 로봇수술, 손해율, 갱신주기, 보장한도)
- **태그**: 검색용 해시태그 3~5개 (예: #로봇수술 #손해율 #요율인상)

### 채널 관점 브리핑
전속FP/채널 상품PM 관점에서 이번 내용이 어떤 의미인지 빠르게 판단할 수 있도록:
- **유리해지는 것**: 채널/FP에게 긍정적인 변화
- **불리해지는 것**: 보험료 인상, 보장 축소, 판매 제약 등
- **공지/안내 필요사항**: FP에게 전달해야 할 변경사항
- **주의/리스크**: 역선택, 손해율 이슈 등 주의점

### 핵심 요약 (Executive Summary)
- 전체 흐름을 파악할 수 있는 불렛포인트
- 숫자, 날짜, 결정사항 위주로 명확하게
- 1시간 기준 15~30줄, 짧은 녹음은 비례 축소
- 중요 키워드/수치는 **볼드** 처리

### 교육 및 세일즈 포인트
- **교육 포인트**: 교육 자료 제작 시 강조할 논리, 화법, 예시
- **현장 이슈**: 영업 현장에서 나올 불만/오해/우려 및 대응 논리
- **기획 아이디어**: 마케팅, 프로모션, 커리큘럼에 적용 가능한 아이디어

### 할 일 (Action Items)
- 팔로업해야 할 업무를 항목별로 정리
- 기한이 언급되었다면 기한 명시

### 정리된 원문
- 주제가 바뀌는 큰 구간별로 ### 번호. 소제목 형식의 헤더로 분리
- **각 구간 시작에 해당 구간의 핵심 내용 3~5줄 요약을 인용 블록(>)으로 먼저 배치**
- 화자가 바뀔 때마다 빈 줄로 구분
- 중요 수치, 키워드, 결정사항은 **볼드** 처리
- 화자 라벨(화자1:, 화자2: 등)은 유지. 역할이 식별되면 표기 (예: 화자1(상품팀):)
- 불명확한 부분은 문맥상 보정하고 (보정됨) 표기
- 교육/상품 출시/영업 현장 반응 관련 내용은 우선 배치

## 마크다운 작성 규칙 (매우 중요)
- 볼드는 반드시 **단어** 형식만 사용 (별표 정확히 2개씩)
- 별표 3개 이상 연속 사용 금지 (***금지***, ****금지****)
- 불렛 포인트는 * 대신 - 사용
- 소제목과 볼드를 섞지 마세요

## 반드시 아래 형식으로만 응답하세요:

[메타데이터]
제목: (회의명 - 핵심키워드. 날짜/시간/괄호 금지)
주제: (키워드 3~5개 쉼표 나열)
태그: (해시태그)

[채널 관점 브리핑]
(유리/불리/공지/리스크 항목별 정리)

[핵심 요약]
(불렛포인트 요약)

[교육 및 세일즈 포인트]
(교육 포인트, 현장 이슈, 기획 아이디어)

[할 일]
(액션 아이템)

[정리된 원문]
(### 구간별 소제목 + 인용 블록 요약 + 화자 구분된 원문)
"""

SPLIT_PROMPT = """\
당신은 보험업계 전속영업부문(채널/FP) 관점에서 회의/교육 내용을 정리하는 전문가입니다.

아래 회의록은 약 {est_min}분 분량으로, 노션 붙여넣기 한계 때문에 2개 파트로 나누어 정리해야 합니다.
내용의 큰 주제 흐름을 보고 자연스러운 분기점에서 파트 1과 파트 2로 나누세요.

각 파트는 독립적으로 읽을 수 있도록 아래 형식을 모두 갖춰야 합니다.

## 각 파트별 규칙 (파트 1, 파트 2 동일)

### 메타데이터
- **제목**: 회의명-N 핵심키워드 형식. 날짜, 시간, 괄호 사용 금지. (예: 상품전략회의-1 로봇수술)
- **주제**: 해당 파트의 핵심 키워드 3~5개를 쉼표로 나열
- **태그**: 검색용 해시태그 3~5개

### 채널 관점 브리핑
전속FP/채널 상품PM 관점에서:
- **유리해지는 것**: 채널/FP에게 긍정적인 변화
- **불리해지는 것**: 보험료 인상, 보장 축소, 판매 제약 등
- **공지/안내 필요사항**: FP에게 전달해야 할 변경사항
- **주의/리스크**: 역선택, 손해율 이슈 등 주의점

### 핵심 요약
- 불렛포인트, 숫자/결정사항 위주
- 중요 키워드/수치는 **볼드** 처리

### 교육 및 세일즈 포인트
- **교육 포인트**: 강조할 논리, 화법, 예시
- **현장 이슈**: 불만/오해/우려 및 대응 논리
- **기획 아이디어**: 적용 가능한 아이디어

### 할 일 (Action Items)
- 팔로업 업무, 기한 명시

### 정리된 원문
- ### 번호. 소제목 헤더로 구간 분리
- **각 구간 시작에 핵심 3~5줄 요약을 인용 블록(>)으로 배치**
- 화자 바뀔 때마다 빈 줄로 구분
- 중요 수치/키워드/결정사항은 **볼드** 처리
- 화자 라벨 유지, 역할 식별 시 표기
- 불명확한 부분은 문맥상 보정하고 (보정됨) 표기

## 마크다운 작성 규칙 (매우 중요)
- 볼드는 반드시 **단어** 형식만 사용 (별표 정확히 2개씩)
- 별표 3개 이상 연속 사용 금지 (***금지***, ****금지****)
- 불렛 포인트는 * 대신 - 사용
- 소제목과 볼드를 섞지 마세요

## 반드시 아래 형식으로 응답하세요:

===== 파트 1 =====

[메타데이터]
제목: (회의명-1 핵심키워드. 날짜/시간/괄호 금지)
주제: (키워드 쉼표 나열)
태그: (해시태그)

[채널 관점 브리핑]
(항목별 정리)

[핵심 요약]
(불렛포인트)

[교육 및 세일즈 포인트]
(교육/현장/기획)

[할 일]
(액션 아이템)

[정리된 원문]
(### 구간별 소제목 + 인용 블록 요약 + 화자 구분된 원문)

===== 파트 2 =====

[메타데이터]
제목: (회의명-2 핵심키워드. 날짜/시간/괄호 금지)
주제: (키워드 쉼표 나열)
중요도: (★ 표기)
태그: (해시태그)

[채널 관점 브리핑]
(항목별 정리)

[핵심 요약]
(불렛포인트)

[교육 및 세일즈 포인트]
(교육/현장/기획)

[할 일]
(액션 아이템)

[정리된 원문]
(### 구간별 소제목 + 인용 블록 요약 + 화자 구분된 원문)
"""


def _fix_markdown(text: str) -> str:
    """Gemini가 생성한 마크다운에서 별표 중첩 등 깨진 문법 정리"""
    import re
    # 별표 3개 이상 연속 → 2개로 (볼드만 사용)
    text = re.sub(r'\*{3,}', '**', text)
    # 불렛 포인트 * → - 로 통일 (줄 시작에서)
    text = re.sub(r'^(\s*)\* ', r'\1- ', text, flags=re.MULTILINE)
    return text


def analyze(text: str) -> dict:
    """전사된 텍스트를 Gemini API로 분석하여 구조화된 결과를 반환 (1파일용)"""
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            {"role": "user", "parts": [{"text": f"{ANALYZE_PROMPT}\n\n---\n\n{text}"}]},
        ],
    )

    result_text = _fix_markdown(response.text)
    return _parse_result(result_text, text)


def analyze_split(text: str, est_min: int) -> list:
    """전사된 텍스트를 2개 파트로 분리 분석 (1시간 초과용)"""
    prompt = SPLIT_PROMPT.format(est_min=est_min)
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            {"role": "user", "parts": [{"text": f"{prompt}\n\n---\n\n{text}"}]},
        ],
    )

    result_text = _fix_markdown(response.text)
    return _parse_split_result(result_text, text)


def _parse_split_result(result: str, original_text: str) -> list:
    """2개 파트로 분리된 Gemini 응답을 파싱"""
    parts = []

    # ===== 파트 1 ===== 와 ===== 파트 2 ===== 로 분리
    part_texts = []
    current_part = ""
    for line in result.split("\n"):
        if line.strip().startswith("===== 파트") and current_part:
            part_texts.append(current_part)
            current_part = ""
        else:
            current_part += line + "\n"
    if current_part.strip():
        part_texts.append(current_part)

    for part_text in part_texts:
        parsed = _parse_result(part_text, original_text)
        if parsed["subject"] and parsed["subject"] != "음성메모":
            parts.append(parsed)

    # 파싱 실패 시 전체를 하나로
    if not parts:
        return [_parse_result(result, original_text)]

    return parts


def _parse_result(result: str, original_text: str) -> dict:
    """Gemini 응답을 파싱하여 구조화된 딕셔너리로 변환"""
    sections = {
        "metadata": "",
        "briefing": "",
        "summary": "",
        "edu_sales": "",
        "action_items": "",
        "formatted_original": "",
        "original": original_text,
    }

    section_map = {
        "[메타데이터]": "metadata",
        "[채널 관점 브리핑]": "briefing",
        "[핵심 요약]": "summary",
        "[교육 및 세일즈 포인트]": "edu_sales",
        "[할 일]": "action_items",
        "[정리된 원문]": "formatted_original",
    }

    current_section = None
    lines = result.strip().split("\n")

    for line in lines:
        stripped = line.strip()

        # 섹션 헤더 감지
        matched = False
        for header, key in section_map.items():
            if stripped.startswith(header):
                current_section = key
                matched = True
                break

        if matched:
            continue

        if current_section:
            sections[current_section] += line + "\n"

    # 메타데이터에서 제목 추출 (파일명용)
    subject = _extract_subject(sections["metadata"])
    sections["subject"] = _sanitize_filename(subject)

    return sections


def _extract_subject(metadata: str) -> str:
    """메타데이터에서 제목을 추출"""
    for line in metadata.strip().split("\n"):
        if line.strip().startswith("제목:"):
            return line.split(":", 1)[1].strip()
    return "음성메모"


def _sanitize_filename(name: str) -> str:
    """파일명에 사용할 수 없는 문자를 제거"""
    invalid_chars = '<>:"/\\|?*#'
    for ch in invalid_chars:
        name = name.replace(ch, "")
    return name.strip()


def save_result(result: dict, output_dir: Path = config.OUTPUT_DIR) -> Path:
    """정리된 결과를 마크다운 파일로 저장"""
    filename = f"{result['subject']}.md"
    output_path = output_dir / filename

    # 동일 파일명 존재 시 번호 추가
    counter = 1
    while output_path.exists():
        filename = f"{result['subject']}_{counter}.md"
        output_path = output_dir / filename
        counter += 1

    metadata = result.get("metadata", "").strip()

    # 정리된 원문이 있으면 사용, 없으면 원본 텍스트 사용
    original = result.get("formatted_original", "").strip()
    if not original:
        original = result["original"]

    content = f"""{metadata}

---

## 채널 관점 브리핑

{result['briefing'].strip()}

---

## 핵심 요약

{result['summary'].strip()}

---

## 교육 및 세일즈 포인트

{result['edu_sales'].strip()}

---

## 할 일

{result['action_items'].strip()}

---

## 전문 (원문)

{original}
"""

    output_path.write_text(content, encoding="utf-8")
    return output_path
