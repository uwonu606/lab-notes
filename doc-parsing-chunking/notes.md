---
tech: Document parsing → structure-aware chunking
slug: doc-parsing-chunking
status: cycling
task: ""
sessions: [2026-10-07, 2026-10-08]
---

## 정리

2026-10-07 세션은 준비만 하고 끊었다. 회차는 아직 없다.

- 의심한 것: AutoSchemaKG 같은 방식도 "작은 단위의 문장만 분할할 수 있다" → 지난 노트 기록으로는 문장이 아니라 8192자로 자른다(체크리스트 9 에서 코드로 다시 확인)
- 한 것: 키워드·서지 수집, 다섯 형식 표본의 속 출력(#형식 개관), 체크리스트
- 다음: 체크리스트 1번(docx)부터 하나씩. 줄기 추측(10)은 아직 받지 않았다

다시 돌리는 법: `cd lab && uv venv -q --python 3.12 .venv && uv pip install -q --python .venv/bin/python python-docx openpyxl python-pptx pymupdf && .venv/bin/python -I 00_formats.py runs/00-samples`

## 체크리스트

체크한 항목은 끝낸 것이다. 사용자가 하나씩 고른다 (2026-10-07: "하나씩 알아볼거야").

### 준비

- [x] 키워드 수집 — 서지 36건 arXiv 확인 (`lab/sources/INDEX.md`)
- [x] 형식 개관 한 번 훑기 — 다섯 형식 표본의 속 출력 (`lab/00_formats.py`, #형식 개관)

### 변환 — 형식별

- [ ] 1. docx — 문단의 줄, 스타일 이름 → `#`. 병합 칸, 스타일 없이 꾸민 제목. 번호 목록(`numbering.xml`)
- [ ] 2. xlsx — 셀 격자에서 표 영역·머리행 찾기, 날짜·수식 값. SpreadsheetLLM (2407.09025)
- [ ] 3. pptx — 도형 좌표로 읽기 순서, 제목 placeholder, 연결선 → Mermaid, 차트 데이터. Meet Your New Client (2508.15817)
- [ ] 4. pdf — 글리프 좌표에서 줄·문단·제목·표 복원 (Layout Analysis). DocLayNet, TableFormer, Docling, MinerU
- [ ] 5. OCR (스캔) — 파이프라인 OCR vs end-to-end VLM. GOT-OCR2.0, olmOCR, MinerU2.5, PaddleOCR-VL, DeepSeek-OCR. OCR 출력 실제로 보기(미검증)
- [ ] 6. 이미지 속 차트·다이어그램 — DePlot (2212.10505), FlowLearn (2407.05183), Flowchart2Mermaid (2512.02170)
- [ ] 7. 변환 건너뛰기 — 페이지 그림을 그대로 검색. ColPali (2407.01449)
- [ ] 8. 변환 도구 비교 — OmniDocBench (2412.07626), From PDF to RAG-Ready (2604.04948)

### 쪼개기 — 줄기

- [ ] 9. 전제 확인 — AutoSchemaKG 는 문장이 아니라 8192자로 자른다 (코드에서 다시 확인)
- [ ] 10. 줄기 추측 — structure-aware chunking 이 왜 생겼나, 지금도 있나, 대안, 과제 한 문장
- [ ] 11. 출처 대조 — Financial Report Chunking (2402.05131) 의 빈틈 문장
- [ ] 12. 첫 실험 — 같은 문서를 8192자로 자른 것과 요소 경계로 자른 것 비교 (Docling)

### 쪼개기 — 다른 갈래

- [ ] 13. 문장 단위 — Segment Any Text (2406.16678)
- [ ] 14. 명제 단위 — Dense X Retrieval (2312.06648)
- [ ] 15. 의미 단위 — semantic chunking (2410.13070), LumberChunker (2406.17526), Meta-Chunking (2410.12788)
- [ ] 16. 그림을 보고 쪼개기 — Vision-Guided Chunking (2506.16035)
- [ ] 17. 맥락 붙이기 — Late Chunking (2409.04701), Contextual Retrieval (Anthropic 블로그)
- [ ] 18. 계층 — RAPTOR (2401.18059)
- [ ] 19. 비교 연구 — 2603.06976 (방법 36개), 2606.00881

### 열린 확인거리

- [ ] 20. pptx 도형 목록 순서 = 그리는 순서인가 (ECMA-376 확인)
- [ ] 21. ToUnicode 없는 PDF 에서 글자가 깨지는가 (표본 만들어 보기)
- [ ] 22. VLM OCR 이 없는 글자를 지어내는가 (OmniDocBench 오류 유형)
- [ ] 23. Word·PPT 를 다룬 학술 연구가 PDF 보다 적은가 (추가 검색)
- [ ] 24. 과제 시험 — 실제 문서 하나를 변환·쪼개서 llm wiki 에 넣기

## 줄기

### 출발 (2026-10-07)

- 부른 물음: "excel, word, ppt diagram, image와 같이 다양한 파일이 존재한다고 했을 때 이를 markdown으로 어떻게 변환하고, 변환한 것을 적절하게 문장단위로 쪼개개 나눌 수 있을지에 대해 조사해보고 싶어."
- 앞선 노트: `../autoschemakg-kg-construction/notes.md` 지도 #2 ("청크를 나는 것 자체를 어떻게 나누는거야? markdown 문서를 어떻게 만드는지도 중요할거 같은데..")
- 키워드 수집: `lab/sources/INDEX.md`
- 방향 (사용자): "제안대로 진행해줘. 그리고 pdf도 필요해. OCR도 넣어줘." → 줄기는 structure-aware chunking, 변환은 그 입구로 다룬다
- 방향 (사용자): 형식마다 구조 → markdown 으로 바꾸는 법 → 대표 논문 순으로 먼저 이해하고 시작한다 → #형식 개관

### 추측 (출처를 읽기 전에)

- 어떤 문제 때문에 생겼나:
- 그 문제는 지금도 있나:
- 그때의 대안은:

## 과제

- 하려는 것:

## 형식 개관

실험 `lab/00_formats.py`. 같은 내용(제목·문단·표·목록)을 docx·xlsx·pptx·pdf·png 로 만들고 속을 출력했다. 출력은 `lab/runs/00-formats.txt`, 표본 파일은 `lab/runs/00-samples/`.

| 형식 | 안에 든 것 | markdown 까지 할 일 | 대표 |
|---|---|---|---|
| docx | 문단의 줄. 제목은 스타일 이름(`Heading1`) | 스타일 이름 → `#`, 표는 그대로 | 규칙 변환기(MarkItDown, Docling) |
| xlsx | 주소 붙은 셀의 격자. 표·머리행 표시 없음 | 표 영역·머리행 찾기, 값 해석 | SpreadsheetLLM 2407.09025 |
| pptx | 슬라이드마다 좌표에 놓인 도형 | 읽기 순서 정하기, 연결선 → 그래프 | Meet Your New Client 2508.15817 |
| pdf | 좌표에 글리프를 찍는 명령 | 줄·문단·제목·표 복원 | DocLayNet, TableFormer, Docling, MinerU |
| 스캔·이미지 | 픽셀 | 글자부터 찾기(OCR), 그다음 pdf 와 같음 | GOT-OCR2.0, olmOCR, PaddleOCR-VL, MinerU2.5 |

## 지도

| # | 기제 | 숨은 상태 | 관측할 것 | 상태 |
|---|---|---|---|---|
| 1 | docx 변환기가 무엇을 보고 제목(`#`)을 정하나 | 문단의 스타일 이름(`w:pStyle`), run 서식(굵기·크기·색) | 둘을 엇갈린 문단의 markdown 출력 | 도는 중 |

## 회차

### 1. 기제 1 (체크리스트 1, docx) — 2026-10-08

- 실험: `lab/01_docx_heading.py`, 변환기 MarkItDown 0.1.8(docx 는 mammoth 1.11.0). 제목처럼 보이는 문단 셋을 엇갈리게 둔다 — 3번 `Regional Results` 는 스타일 `Normal` 에 Heading 1 겉모양(굵게·14pt·파랑), 5번 `Outlook` 은 스타일 `Heading 1` 에 본문 겉모양(안 굵게·12pt·검정)
- 없으면: "어디부터 어디까지가 맥락인지 말하는 docx의 의도가 사라질거라고 생각해."
- 예측: "1,5만 마크다운 줄로 나오고 3은 안 나올거 같아." — 3은 글자는 나오되 `#` 제목 줄이 아니라는 뜻("가") · 높음
- 결과: 1 `# Q3 Report`, 3 `**Regional Results**`, 5 `# Outlook`. 예측과 맞음. 3은 겉모양 가운데 굵게만 `**` 로 남고 크기·색은 사라졌다. 출력 `lab/runs/01-docx-heading.txt`
- 설명: "옷을 입힌 건 강조하는 표현이고 헤딩을 붙인 건 글을 구성하는 단위니까"
- 되물음: "변환기는 어떤 문단이 '구성 단위'라는 걸 파일의 어디를 보고 아나" → "헤딩이나 글자 크기?" · "3·5번 줄을 '글자 크기' 가설로 설명할 수 있나" → "크기로 지정하는 사람도 있지 않을까? 나는 헤딩을 안 달았던거 같아" · "헤딩 없이 크기로만 제목을 만든 docx 를 MarkItDown 에 넣으면 무엇이 나오고, 그러면 무엇이 깨지나" →
