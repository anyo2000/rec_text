from notion_client import Client
import config


client = Client(auth=config.NOTION_API_TOKEN)


def _markdown_to_blocks(markdown: str) -> list:
    """마크다운 텍스트를 노션 블록 리스트로 변환"""
    blocks = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 빈 줄 스킵
        if not stripped:
            i += 1
            continue

        # 구분선
        if stripped == "---":
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        # 헤더
        if stripped.startswith("### "):
            blocks.append({
                "type": "heading_3",
                "heading_3": {"rich_text": _parse_rich_text(stripped[4:])}
            })
            i += 1
            continue
        if stripped.startswith("## "):
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": _parse_rich_text(stripped[3:])}
            })
            i += 1
            continue
        if stripped.startswith("# "):
            blocks.append({
                "type": "heading_1",
                "heading_1": {"rich_text": _parse_rich_text(stripped[2:])}
            })
            i += 1
            continue

        # 인용 블록
        if stripped.startswith("> "):
            quote_lines = [stripped[2:]]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            blocks.append({
                "type": "quote",
                "quote": {"rich_text": _parse_rich_text("\n".join(quote_lines))}
            })
            continue

        # 불렛 리스트
        if stripped.startswith("- "):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _parse_rich_text(stripped[2:])}
            })
            i += 1
            continue

        # 일반 텍스트
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": _parse_rich_text(stripped)}
        })
        i += 1

    return blocks


def _parse_rich_text(text: str) -> list:
    """마크다운 볼드(**text**)를 노션 rich_text로 변환"""
    import re
    parts = re.split(r'(\*\*[^*]+\*\*)', text)
    rich_text = []

    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            rich_text.append({
                "type": "text",
                "text": {"content": part[2:-2]},
                "annotations": {"bold": True}
            })
        else:
            rich_text.append({
                "type": "text",
                "text": {"content": part}
            })

    result = rich_text if rich_text else [{"type": "text", "text": {"content": text}}]

    # 노션 API 2000자 제한 대응: 긴 텍스트를 분할
    split_result = []
    for item in result:
        content = item["text"]["content"]
        if len(content) <= 2000:
            split_result.append(item)
        else:
            bold = item.get("annotations", {}).get("bold", False)
            for i in range(0, len(content), 2000):
                chunk = {"type": "text", "text": {"content": content[i:i+2000]}}
                if bold:
                    chunk["annotations"] = {"bold": True}
                split_result.append(chunk)
    return split_result


def upload_to_notion(result: dict, recording_date: str = None) -> str:
    """정리 결과를 노션 데이터베이스에 페이지로 생성. 페이지 URL 반환.
    recording_date: ISO 형식 날짜 문자열 (예: '2026-03-18')
    """
    if not config.NOTION_API_TOKEN or not config.NOTION_DATABASE_ID:
        return ""

    # 메타데이터 파싱
    metadata = result.get("metadata", "")
    title = result.get("subject", "음성메모")
    tags = ""
    topic = ""
    for line in metadata.strip().split("\n"):
        line = line.strip()
        if line.startswith("태그:"):
            tags = line.split(":", 1)[1].strip()
        elif line.startswith("주제:"):
            topic = line.split(":", 1)[1].strip()

    # DB 속성 설정
    properties = {
        "이름": {"title": [{"text": {"content": title}}]},
    }
    if topic:
        properties["주제"] = {"rich_text": [{"text": {"content": topic}}]}
    if recording_date:
        properties["날짜"] = {"date": {"start": recording_date}}

    # 페이지 본문 마크다운 조립
    body_parts = []

    if tags:
        body_parts.append(f"**태그**: {tags}")

    body_parts.append("---")

    if result.get("briefing", "").strip():
        body_parts.append("## 채널 관점 브리핑")
        body_parts.append(result["briefing"].strip())
        body_parts.append("---")

    if result.get("summary", "").strip():
        body_parts.append("## 핵심 요약")
        body_parts.append(result["summary"].strip())
        body_parts.append("---")

    if result.get("edu_sales", "").strip():
        body_parts.append("## 교육 및 세일즈 포인트")
        body_parts.append(result["edu_sales"].strip())
        body_parts.append("---")

    if result.get("action_items", "").strip():
        body_parts.append("## 할 일")
        body_parts.append(result["action_items"].strip())
        body_parts.append("---")

    original = result.get("formatted_original", "").strip()
    if not original:
        original = result.get("original", "")
    if original:
        body_parts.append("## 전문 (원문)")
        body_parts.append(original)

    body_md = "\n\n".join(body_parts)
    blocks = _markdown_to_blocks(body_md)

    # 노션 블록 100개 제한 → 청크로 나눠서 전송
    # 첫 번째 청크는 페이지 생성 시 포함
    first_chunk = blocks[:100]
    remaining = blocks[100:]

    page = client.pages.create(
        parent={"database_id": config.NOTION_DATABASE_ID},
        properties=properties,
        children=first_chunk,
    )

    page_id = page["id"]

    # 나머지 블록 100개씩 추가
    while remaining:
        chunk = remaining[:100]
        remaining = remaining[100:]
        client.blocks.children.append(block_id=page_id, children=chunk)

    return page.get("url", "")


def test_connection() -> bool:
    """노션 연결 테스트"""
    try:
        client.databases.retrieve(database_id=config.NOTION_DATABASE_ID)
        return True
    except Exception as e:
        print(f"노션 연결 실패: {e}")
        return False
