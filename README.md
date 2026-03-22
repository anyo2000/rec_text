# 회의록 자동 정리

보험업계 회의/교육 음성 녹음을 자동으로 텍스트 전사 + 분석 + 노션 업로드하는 도구.
음성 파일을 폴더에 넣고 더블클릭하면, 화자 구분된 회의록이 노션에 자동 생성된다.

## 주요 기능

- **음성 → 텍스트 전사** (Gemini 2.5 Flash)
  - 화자 구분 (화자1, 화자2 라벨링)
  - 보험 용어 문맥 기반 보정
  - 불명확한 음성 전후맥락 보정, 추임새 자동 제거

- **텍스트 분석 및 구조화**
  - 영업 현장 관점 브리핑 (유리한 점 / 불리한 점 / 공지사항 / 리스크)
  - 핵심 요약, 교육 포인트, 할 일 추출
  - 주제 구간별 원문 정리 (구간마다 핵심 요약 포함)

- **자동 출력**
  - 노션 데이터베이스 자동 업로드 (제목, 주제, 날짜 속성 포함)
  - 마크다운 파일 로컬 저장
  - 1시간 초과 녹음은 주제 기준으로 자동 분리

## 사용법

1. iCloud 회의록 폴더에 음성 파일 저장 (.mp3, .m4a, .aac 등)
2. `회의록정리.command` 더블클릭
3. 노션에서 결과 확인

```
[1/3] Gemini: 음성 → 텍스트 (화자구분 + 용어보정)
[2/3] Gemini: 분석 (브리핑 + 요약 + 교육포인트 + 할일 + 원문정리)
[3/3] 마크다운 저장 + 노션 자동 업로드
```

## 설치 및 설정

```bash
pip install -r requirements.txt
```

`.env` 파일 설정:
```
GEMINI_API_KEY=your_gemini_api_key
NOTION_API_TOKEN=your_notion_api_token
NOTION_DATABASE_ID=your_notion_database_id
```

- Gemini API 키: https://aistudio.google.com/apikey
- Notion 통합: https://www.notion.so/my-integrations

## 기술 스택

- **STT + 분석**: Google Gemini 2.5 Flash
- **노션 연동**: Notion API
- **언어**: Python 3.9+
