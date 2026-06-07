# Multi Modal OCR

여기에서는 multi model을 이용해 OCR (Optical Character Recognition)을 수행합니다. 

### Operation Architecture

전체 애플리케이션은 Streamlit UI(`application/app.py`)를 진입점으로 하며, 모드에 따라 일반 대화/RAG/Agent/OCR Agent로 분기합니다. Agent 계열은 LangGraph(`langgraph_agent.py`) 위에서 Built-in 도구, Anthropic Agent Skills 스펙(`skill.py`), MCP 서버(`mcp_config.py`)를 결합해 동작합니다.

```mermaid
flowchart TB
  subgraph UI["Streamlit UI (application/app.py)"]
    MODE["모드: 일상적인 대화 / RAG / Agent / OCR Agent / 이미지 분석"]
    SEL["Skill 선택 · MCP 선택 · 모델 선택 · PDF 업로드"]
  end

  subgraph Chat["chat.py"]
    GC[general_conversation]
    RAG[run_rag_with_knowledge_base]
    SUM[summarize_image]
    GTB[get_chat / ChatBedrock]
    UPS[upload_to_s3]
  end

  subgraph LLM["Amazon Bedrock"]
    BR[Bedrock Runtime]
    KB[(Knowledge Base / retrieve)]
  end

  subgraph LG["LangGraph Agent (application/langgraph_agent.py)"]
    RLA[run_langgraph_agent]
    ROA[run_ocr_agent]
    BCA[buildChatAgent / WithHistory]
    CM[call_model 노드]
    TN[ToolNode]
    BT["Built-in tools: execute_code, bash, write_file, read_file, upload_file_to_s3, get_current_time"]
    MCPA[langchain-mcp-adapters · MultiServerMCPClient]
  end

  subgraph Skills["Agent Skills (application/skill.py · application/skills/)"]
    SM[SkillManager]
    BSP[build_skill_prompt]
    GSI[get_skill_instructions tool]
    SK1["pdf2img/SKILL.md"]
    SK2["img2text/SKILL.md"]
    SK3["skill-creator/SKILL.md"]
  end

  subgraph MCPServers["MCP Servers (mcp_config.py)"]
    KBM["knowledge base (mcp_server_retrieve.py)"]
    AWSD["aws_documentation (awslabs)"]
    WF["web_fetch (mcp-server-fetch-typescript)"]
    TX["text_extraction (mcp_server_text_extraction.py)"]
    OBS["obsidian (obsidian-mcp)"]
    USR["사용자 설정 (user_defined_mcp.json)"]
  end

  subgraph Storage["Artifacts / S3"]
    ART["application/artifacts/"]
    S3[(Amazon S3)]
  end

  subgraph Standalone["Standalone CLI"]
    P2I["pdf2img/pdf2img.py"]
    I2T["img2txt/img2txt.py"]
  end

  MODE -->|일상적인 대화| GC
  MODE -->|RAG| RAG
  MODE -->|이미지 분석| SUM
  MODE -->|Agent| RLA
  MODE -->|OCR Agent| ROA
  SEL -->|skill_list| RLA
  SEL -->|mcp_servers| RLA
  SEL -->|PDF 업로드| RLA

  GC --> GTB
  RAG --> GTB
  RAG --> KB
  SUM --> GTB
  GTB --> BR

  RLA --> BCA
  ROA --> BCA
  BCA --> CM
  BCA --> TN
  CM --> GTB
  TN --> BT
  TN --> MCPA
  TN --> GSI

  BSP -->|system_prompt| CM
  GSI --> SM
  SM --> SK1
  SM --> SK2
  SM --> SK3

  MCPA --> MCPServers
  KBM --> KB

  BT --> ART
  BT --> S3
  SUM --> UPS --> S3
```

| 모드 | 진입 함수 | 설명 |
|------|-----------|------|
| 일상적인 대화 | `chat.general_conversation` | 대화 이력 + Bedrock Runtime 스트리밍 응답 |
| RAG | `chat.run_rag_with_knowledge_base` | Bedrock Knowledge Base `retrieve` 후 Bedrock Runtime으로 답변 생성 |
| Agent | `langgraph_agent.run_langgraph_agent` | LangGraph + Built-in tools + Agent Skills + MCP (사용자 선택) |
| OCR Agent | `langgraph_agent.run_ocr_agent` | `pdf2img` → `img2text` Skill을 자동 오케스트레이션해 PDF를 Markdown으로 변환 |
| 이미지 분석 | `chat.summarize_image` | ChatBedrock 멀티모달(이미지 + 텍스트) 분석 후 Markdown 아티팩트를 S3에 업로드 |

#### 주요 구성 요소

- **Built-in Tools** (`langgraph_agent.get_builtin_tools`): `execute_code`, `bash`, `write_file`, `read_file`, `get_current_time`, 그리고 `sharing_url`이 설정된 경우 `upload_file_to_s3`.
- **Agent Skills** (`application/skills/`): Anthropic Agent Skills 스펙을 따르는 `SKILL.md`를 자동 탐색합니다. 현재 번들된 스킬은 `pdf2img`(PDF → 페이지 이미지), `img2text`(이미지 폴더 → 통합 Markdown), `skill-creator`(스킬 생성 도우미)입니다.
- **MCP Servers** (`mcp_config.load_config`): `knowledge base`, `aws_documentation`, `web_fetch`, `text_extraction`, `obsidian`, `사용자 설정`(`user_defined_mcp.json`).
- **아티팩트 저장소**: 도구 실행 산출물은 `application/artifacts/`에 저장되며, `upload_file_to_s3`를 통해 S3 및 `sharing_url`(예: CloudFront)로 공유됩니다.


## PDF to Image

OCR을 하기 위해서 아래와 같이 PDF에서 각 페이지를 이미지로 추출합니다. 상세한 코드는 [pdf2img.py](./pdf2img/pdf2img.py)을 참조합니다.

```python
import fitz
doc = fitz.open(pdf_path)
total = len(doc)
saved = []
zoom = dpi / 72  # 72 dpi is the PDF default
mat = fitz.Matrix(zoom, zoom)

for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=mat, alpha=False)
    filename = f"page_{i:03d}.png"
    out_path = os.path.join(output_dir, filename)
    pix.save(out_path)
    saved.append(out_path)
    print(f"  [{i}/{total}] Saved → {out_path}")

doc.close()
````


아래와 같이 실행하면 이미지를 추출할 수 있습니다.


```bash
python pdf2img/pdf2img.py contents/2017-NEC-Code.pdf
```

## Image to Text

아래와 같이 이미지를 읽어서 Base64로 변환한 후에 Multimodal LLM으로 text를 추출합니다. LLM 활용을 위해 markdown 형태로 저장합니다. 상세한 코드는 [img2txt.py](./img2txt/img2txt.py)을 참조합니다.

```python
def extract_one(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        raw = f.read()
    b64 = _prepare_image_base64(raw)
    raw_text = _extract_text_with_llm(b64, LLM_PROMPT)
    return _parse_result(raw_text).strip()
```

이때 사용하는 prompt는 아래와 같습니다.

```python
LLM_PROMPT = (
    "페이지 내용을 Markdown 형식으로 변환합니다. 평문이 아니라 제목(#·##)·목록·강조·코드 블록 등 "
    "Markdown 문법을 적절히 써서 구조화해 주세요. 문장 단위로 읽기 쉽게 구분합니다. "
    "상단의 header와 하단의 footer는 출력에서 제외합니다. 상단 header는 주로 현재 페이지 제목이고, "
    "footer에는 페이지 번호 등이 있는데, 변환 결과에는 포함하지 않습니다.\n\n"
    "페이지에 그림·도표·사진·스크린샷·다이어그램·캡처 등 시각적 요소가 있으면, 그 이미지가 무엇을 보여주는지·"
    "본문과 어떤 관계인지·어떤 정보를 전달하는지를 빠짐없이 상세히 풀어서 서술합니다."
)
````

아래와 같이 Base64로 변환한 이미지를 Prompt와 함께 전달하여 text를 추출합니다.

```python
query = LLM_PROMPT

multimodal = _get_chat()
messages = [
    HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_base64}"},
            },
            {"type": "text", "text": query},
        ]
    )
]

result = multimodal.invoke(messages)
extracted_text = result.content
```

이를 실행할때에는 아래와 같이 수행합니다.


```bash
python img2txt/img2txt.py contents/page_040.png
```

[추출한 이미지](./contents/page_040.png)에 대한 결과는 [추출된 Text](./contents/image_summary_4039b0fb54aa4bb8b46f48b4e219f0b3.md)와 같습니다.

## OCR 결과

### 표안의 표

표안의 표가 있는 경우는 대표적인 복잡한 OCR 케이스입니다. 이때 비어있는 항목이 있으면 RAG등에서 활용할 때에 적절한 값을 얻지 못할 수 있습니다.

[complex_parsing_hotel_info.png](./contents/complex_parsing_hotel_info.png)을 분석하면 아래와 같습니다.

<img width="800" alt="image" src="./contents/complex_parsing_hotel_info.png" />

이때의 결과는 아래와 같습니다. 표안의 표가 있는 복잡한 경우이지만 아래처럼 표가 적절히 분석되었습니다.

<img width="764" height="798" alt="image" src="https://github.com/user-attachments/assets/12eb9547-757a-4768-8b9e-9d564f581a29" />

[example-table.png](./contents/example-table.png)에 대해 OCR을 수행합니다.


### Table

아래 Table의 경우에 왼쪽에 Success / Failure로 구분되어 있고 Capture이 밑에 있습니다. Caption으 함께 보지 않으면 Success/Failure의 의미를 파악하기 어려운 케이스입니다.

<img width="800" alt="image" src="./contents/example-table.png" />

이때의 결과는 아래와 같습니다. Table 제목 아래에 Success / Failure가 구분되어 있으므로 이해하기 좋습니다. 

<img width="934" height="714" alt="image" src="https://github.com/user-attachments/assets/565c7333-02dc-46c5-aab9-05ce860aece7" />

[example-table-and-image.png](./contents/example-table-and-image.png)에 대해 OCR을 수행합니다.

### 표과 이미지

아래와 같이 페이지에 표와 이미지가 같이 있는 경우에 표와 이미지를 구분하여 처리하는것은 매우 어려운 OCR 주제입니다.

<img width="800" alt="image" src="./contents/example-table-and-image.png" />

이때의 Table 결과는 아래와 같습니다. Table에 별도로 결과를 주고 있습니다.

<img width="752" height="437" alt="image" src="https://github.com/user-attachments/assets/acee1dc0-9469-463b-8430-534fcd9d9c1f" />

아래는 그림에 대한 OCR 결과입니다. 그림을 해석하여 풀어쓰므로써 LLM이 그림을 활용할 수 있도록 해줍니다.

<img width="941" height="699" alt="image" src="https://github.com/user-attachments/assets/c483660f-5c91-435a-bd78-70d153976f92" />






