import sys
sys.path.insert(0, '/Users/hyosungahn/Desktop/workspace/rec_text')

import httpx
import config

headers = {
    'Authorization': f'Bearer {config.NOTION_API_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28',
}

PAGES = [
    ("33bfcec3-4295-80a2-a38c-d261db185e4a", "LINK 영남 지점장교육"),
    ("311fcec3-4295-806d-9c5f-e1e2acb5491a", "LINK 파일럿 은계지점"),
    ("300fcec3-4295-80c1-9789-e807fa5070b0", "LINK 컨설팅 링크 파일럿 충북지역단"),
    ("348fcec3-4295-8190-b84d-f0a1aad42556", "Link SFP 1교시"),
    ("348fcec3-4295-81ce-a3ed-c0e8f363f853", "LINK SFP 2교시"),
    ("345fcec3-4295-8127-80fb-d62310b810fc", "LINK 육성팀장 1교시"),
    ("345fcec3-4295-8160-a630-d28fec78908a", "LINK 육성팀장 2교시"),
    ("33cfcec3-4295-81a4-a56b-dc2af8c7a79f", "LINK 서울 지점장 2교시"),
    ("33cfcec3-4295-81c7-9f24-e22813a13f5d", "LINK 서울 지점장 1교시"),
]


def extract_text(block):
    """블록에서 텍스트 추출"""
    btype = block.get('type', '')
    content = block.get(btype, {})
    rich_text = content.get('rich_text', [])
    text = ''.join(rt.get('plain_text', '') for rt in rich_text)
    return text


def fetch_all_blocks(page_id):
    """페이지의 모든 블록을 페이징해서 가져오기"""
    blocks = []
    url = f'https://api.notion.com/v1/blocks/{page_id}/children?page_size=100'
    while url:
        resp = httpx.get(url, headers=headers, timeout=60.0)
        if resp.status_code != 200:
            print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
            return blocks
        data = resp.json()
        blocks.extend(data.get('results', []))
        if data.get('has_more') and data.get('next_cursor'):
            url = f'https://api.notion.com/v1/blocks/{page_id}/children?page_size=100&start_cursor={data["next_cursor"]}'
        else:
            url = None
    return blocks


def fetch_page_title(page_id):
    """페이지 제목 가져오기"""
    resp = httpx.get(f'https://api.notion.com/v1/pages/{page_id}', headers=headers, timeout=60.0)
    if resp.status_code != 200:
        return "(제목 조회 실패)"
    data = resp.json()
    props = data.get('properties', {})
    # title 속성 찾기
    for key, val in props.items():
        if val.get('type') == 'title':
            rich_text = val.get('title', [])
            return ''.join(rt.get('plain_text', '') for rt in rich_text)
    return "(제목 없음)"


def process_page(page_id, label):
    print(f"\n{'='*70}")
    print(f"[{label}]")

    title = fetch_page_title(page_id)
    print(f"제목: {title}")
    print(f"Page ID: {page_id}")

    blocks = fetch_all_blocks(page_id)
    print(f"전체 블록 수: {len(blocks)}")

    # heading_2 목록 출력
    headings = []
    for b in blocks:
        if b.get('type') == 'heading_2':
            headings.append(extract_text(b))

    print(f"\n--- heading_2 섹션 목록 ---")
    for h in headings:
        print(f"  • {h}")

    # 핵심 요약 섹션 찾기
    print(f"\n--- 핵심 요약 ---")
    in_summary = False
    summary_count = 0
    for i, b in enumerate(blocks):
        btype = b.get('type', '')
        text = extract_text(b)

        # 핵심 요약 헤딩 감지
        if btype in ('heading_1', 'heading_2', 'heading_3') and '핵심 요약' in text:
            in_summary = True
            print(f"[{btype}] {text}")
            continue

        # 다음 heading_2/1 만나면 핵심 요약 종료
        if in_summary and btype in ('heading_1', 'heading_2') and '핵심 요약' not in text:
            in_summary = False

        if in_summary and text.strip():
            prefix = {
                'bulleted_list_item': '  • ',
                'numbered_list_item': '  1. ',
                'paragraph': '  ',
                'heading_3': '  ### ',
            }.get(btype, f'  [{btype}] ')
            print(f"{prefix}{text}")
            summary_count += 1

    if summary_count == 0:
        print("  (핵심 요약 섹션 없음 또는 내용 없음)")

    # 전문 (원문) 섹션 앞부분
    print(f"\n--- 전문 (원문) - 첫 50개 블록 ---")
    in_full = False
    full_count = 0
    for i, b in enumerate(blocks):
        btype = b.get('type', '')
        text = extract_text(b)

        # 전문 헤딩 감지
        if btype in ('heading_1', 'heading_2', 'heading_3') and ('전문' in text or '원문' in text):
            in_full = True
            print(f"[{btype}] {text}")
            continue

        # 다음 heading_1/2 만나면 종료
        if in_full and btype in ('heading_1', 'heading_2') and '전문' not in text and '원문' not in text:
            in_full = False

        if in_full:
            if full_count >= 50:
                print(f"  ... (이후 생략, 총 블록 계속)")
                break
            if text.strip():
                prefix = {
                    'bulleted_list_item': '  • ',
                    'numbered_list_item': '  N. ',
                    'paragraph': '  ',
                    'heading_3': '  ### ',
                }.get(btype, f'  [{btype}] ')
                print(f"{prefix}{text}")
                full_count += 1

    if full_count == 0 and not in_full:
        print("  (전문/원문 섹션 없음)")


if __name__ == '__main__':
    import sys
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for page_id, label in PAGES[start:]:
        process_page(page_id, label)
    print(f"\n{'='*70}")
    print("완료")
