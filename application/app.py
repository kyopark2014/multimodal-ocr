import streamlit as st 
import streamlit_paste_button as spb
import utils
import chat
import json
import mcp_config 
import logging
import sys
import os
import uuid
import asyncio
import io
import urllib.request
from urllib.parse import urlparse, unquote
import langgraph_agent
import skill
from notification_queue import NotificationQueue

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("streamlit")

config = utils.load_config()
sharing_url = config.get("sharing_url")

# title
st.set_page_config(page_title='agent-skills', page_icon=None, layout="centered", initial_sidebar_state="auto", menu_items=None)

mode_descriptions = {
    "일상적인 대화": [
        "대화이력을 바탕으로 챗봇과 일상의 대화를 편안히 즐길수 있습니다."
    ],
    "RAG": [
        "Bedrock Knowledge Base를 이용해 구현한 RAG로 필요한 정보를 검색합니다."
    ],
    "Agent": [
        "SKILL과 MCP를 활용한 Agent를 이용합니다. 왼쪽 메뉴에서 필요한 MCP를 선택하세요."
    ],
    "OCR Agent": [
        "SKILL을 이용해 OCR Agent를 활용합니다. pdf를 선택하면 markdown 형태로 변환할 수 있습니다."
    ]
}

with st.sidebar:
    st.title("🔮 Menu")
    
    st.markdown(
        "Amazon Bedrock을 이용해 다양한 형태의 대화를 구현합니다." 
        "여기에서는 SKILL을 이용해 OCR agent의 기능을 구현합니다." 
        "주요 코드는 LangGraph를 이용해 구현되었습니다.\n"
        "상세한 코드는 [Github](https://github.com/kyopark2014/multi-modal-ocr)을 참조하세요."
    )

    st.subheader("🐱 대화 형태")
    
    # radio selection
    mode = st.radio(
        label="원하는 대화 형태를 선택하세요. ",options=["일상적인 대화", "RAG", "Agent", "OCR Agent"], index=2
    )   
    st.info(mode_descriptions[mode][0])
    
    # mcp selection    
    mcp_options = [
        "knowledge base", 
        "aws_documentation", 
        "web_fetch",
        "text_extraction",
        "obsidian",
        "사용자 설정"
    ]    
    if mode=='Agent':
        # Skill Config JSON input
        st.subheader("⚙️ Skill Config")

        skill_selections = {}
        default_skill_selections, default_mcp_selections = utils.get_initial_tool_defaults()
        logger.info(f"default_skill_selections: {default_skill_selections}")
        with st.expander("Skill 옵션 선택", expanded=True):
            available_skill_info = skill.available_skill_info("base")
            for s in available_skill_info:
                default_value = s["name"] in default_skill_selections
                skill_selections[s["name"]] = st.checkbox(s["name"], key=f"skill_{s['name']}", value=default_value, help=s["description"], disabled=False)
    
        selected_skills = [name for name, is_selected in skill_selections.items() if is_selected]
        logger.info(f"selected_skills: {selected_skills}")

        # MCP Config JSON input
        st.subheader("⚙️ MCP Config")

        # Change radio to checkbox        
        mcp_selections = {}
        with st.expander("MCP 옵션 선택", expanded=True):
            for option in mcp_options:
                default_value = option in default_mcp_selections
                mcp_selections[option] = st.checkbox(option, key=f"mcp_{option}", value=default_value)
                
        if mcp_selections["사용자 설정"]:
            mcp = {}
            try:
                with open("user_defined_mcp.json", "r", encoding="utf-8") as f:
                    mcp = json.load(f)
                    logger.info(f"loaded user defined mcp: {mcp}")
            except FileNotFoundError:
                logger.info("user_defined_mcp.json not found")
                pass
            
            mcp_json_str = json.dumps(mcp, ensure_ascii=False, indent=2) if mcp else ""
            
            mcp_info = st.text_area(
                "MCP 설정을 JSON 형식으로 입력하세요",
                value=mcp_json_str,
                height=150
            )
            logger.info(f"mcp_info: {mcp_info}")

            if mcp_info:
                try:
                    mcp_config.mcp_user_config = json.loads(mcp_info)
                    logger.info(f"mcp_user_config: {mcp_config.mcp_user_config}")                    
                    st.success("JSON 설정이 성공적으로 로드되었습니다.")                    
                except json.JSONDecodeError as e:
                    st.error(f"JSON 파싱 오류: {str(e)}")
                    st.error("올바른 JSON 형식으로 입력해주세요.")
                    logger.error(f"JSON 파싱 오류: {str(e)}")
                    mcp_config.mcp_user_config = {}
            else:
                mcp_config.mcp_user_config = {}
                
            with open("user_defined_mcp.json", "w", encoding="utf-8") as f:
                json.dump(mcp_config.mcp_user_config, f, ensure_ascii=False, indent=4)
            logger.info("save to user_defined_mcp.json")
        
        mcp_servers = [server for server, is_selected in mcp_selections.items() if is_selected]
        if (
            selected_skills != default_skill_selections
            or mcp_servers != default_mcp_selections
        ):
            utils.save_favorite_tools(skills=selected_skills, mcp_servers=mcp_servers)


    else:
        mcp_servers = []

    # model selection box
    modelName = st.selectbox(
        '🖊️ 사용 모델을 선택하세요',
        (
            "Claude 4.6 Sonnet",
            "Claude 4.7 Opus",            
            "Claude 4.6 Opus"
        ), index=1
    )

    # skill checkbox
    select_skillMode = st.checkbox('Skill Mode', value=True)
    skillMode = 'Enable' if select_skillMode else 'Disable'    

    # debug checkbox
    select_debugMode = st.checkbox('Debug Mode', value=True)
    debugMode = 'Enable' if select_debugMode else 'Disable'
    #print('debugMode: ', debugMode)

    uploaded_file = None
    pasted_image = None

    def safe_paste_button(label, key):
        """streamlit-paste-button 래퍼: 내부 이미지 디코딩 실패 시 안전하게 처리"""
        try:
            result = spb.paste_image_button(label, key=key, errors="ignore")
            if result.image_data is not None:
                return result.image_data
        except Exception as e:
            logger.warning(f"clipboard paste error: {e}")
        return None

    if mode=='이미지 분석':
        st.subheader("🌇 이미지 업로드")
        uploaded_file = st.file_uploader("이미지 분석을 위한 파일을 선택합니다.", type=["png", "jpg", "jpeg"])
        
        st.markdown("**또는** 화면 캡처를 붙여넣으세요:")
        pasted_image = safe_paste_button("📋 클립보드에서 붙여넣기", key="paste_image")
    elif mode=='Agent' or mode=='OCR Agent':
        st.subheader("🌇 파일 선택")
        uploaded_file = st.file_uploader("OCR 처리를 위한 파일을 선택합니다.", type=["pdf"])

        if uploaded_file:
            file_name = uploaded_file.name
            file_bytes = uploaded_file.getvalue()
            logger.info(f"uploaded_file: {file_name}, size={len(file_bytes)} bytes")
        
    chat.update(modelName, debugMode, skillMode)    

    st.success(f"Connected to {modelName}", icon="💚")
    clear_button = st.button("대화 초기화", key="clear")
    # logger.info(f"clear_button: {clear_button}")

st.title('🔮 '+ mode)

if clear_button==True:    
    chat.map_chain = dict() 
    chat.checkpointers = dict() 
    chat.memorystores = dict() 
    chat.initiate()

# Preview the uploaded image in the sidebar
file_name = ""
file_bytes = None
state_of_code_interpreter = False

# Handle pasted image from clipboard
if pasted_image is not None and clear_button==False:
    buf = io.BytesIO()
    pasted_image.save(buf, format="PNG")
    file_bytes = buf.getvalue()
    file_name = "pasted_screenshot.png"
    logger.info(f"pasted image: {file_name}, size={len(file_bytes)} bytes")

    if mode == '이미지 분석':
        st.image(pasted_image, caption="붙여넣은 이미지 미리보기", use_container_width=True)

if uploaded_file is not None and clear_button==False:
    logger.info(f"uploaded_file.name: {uploaded_file.name}")
    if uploaded_file.name:
        logger.info(f"csv type? {uploaded_file.name.lower().endswith(('.csv'))}")

    if uploaded_file and uploaded_file.name and not mode == '이미지 분석':
        chat.initiate()

        if debugMode=='Enable':
            status_msg = f'선택한 {uploaded_file.name} 파일을 OCR합니다.'
            logger.info(f"status: {status_msg}")
            st.info(status_msg)

        file_name = uploaded_file.name
        logger.info(f"uploading... file: {file_name}")

        artifacts_dir = langgraph_agent.ARTIFACTS_DIR
        os.makedirs(artifacts_dir, exist_ok=True)
        saved_pdf_path = os.path.join(artifacts_dir, file_name)
        with open(saved_pdf_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        logger.info(f"saved uploaded file to: {saved_pdf_path}")

        with st.status("thinking...", expanded=True, state="running") as status:
            notification_queue = NotificationQueue(container=status)

            response, artifacts = asyncio.run(langgraph_agent.run_langgraph_agent(
                query=(
                    f"OCR 처리를 위한 파일을 선택했습니다. "
                    f"pdf2img skill을 이용해 아래 PDF 파일에서 OCR을 위해 이미지를 추출합니다.\n"
                    f"- pdf_path: {saved_pdf_path}\n"
                    f"- output_dir: {os.path.join(artifacts_dir, os.path.splitext(file_name)[0])}"
                ),
                mcp_servers=mcp_servers, 
                skill_list=["pdf2img"],
                history_mode="Disable", 
                notification_queue=notification_queue))
            
            response, artifacts = asyncio.run(langgraph_agent.run_langgraph_agent(
                query=(
                    f"OCR 처리를 위해 이미지를 추출했습니다."
                    f"img2text skill을 이용해 아래 폴더의 이미지들을 텍스트로 변환합니다.\n"
                    f"- image_dir: {os.path.join(artifacts_dir, os.path.splitext(file_name)[0])}"
                    "생성된 markdown 파일을 S3에 업로드 하지 않습니다."
                ),
                mcp_servers=mcp_servers, 
                skill_list=["img2text"],
                history_mode="Disable", 
                notification_queue=notification_queue))
        st.write(response)

        # markdown 파일 미리보기
        pdf_stem = os.path.splitext(file_name)[0]
        md_path = os.path.join(artifacts_dir, pdf_stem, f"{pdf_stem}.md")

        md_paths = []
        if os.path.isfile(md_path):
            md_paths.append(md_path)
        for artifact in artifacts:
            if isinstance(artifact, str) and artifact.endswith(".md") and os.path.isfile(artifact) and artifact not in md_paths:
                md_paths.append(artifact)

        if md_paths:
            for path in md_paths:
                with open(path, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
                st.markdown(f"### 📄 {os.path.basename(path)}")
                st.caption(path)
                st.markdown(markdown_content)
                st.markdown("---")
        else:
            st.warning(f"Markdown 결과 파일을 찾지 못했습니다: {md_path}")

        logger.info(f"response: {response}")


    if uploaded_file and clear_button==False and mode == '이미지 분석':
        st.image(uploaded_file, caption="이미지 미리보기", use_container_width=True)

        file_name = uploaded_file.name
        file_bytes = uploaded_file.getvalue()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.greetings = False

# Display chat messages from history on app rerun
def display_chat_messages() -> None:
    """Print message history
    @returns None
    """
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if "images" in message:                
                for url in message["images"]:
                    logger.info(f"url: {url}")

                    file_name = url[url.rfind('/')+1:]
                    st.image(url, caption=file_name, use_container_width=True)
            st.markdown(message["content"])

display_chat_messages()

def show_references(reference_docs):
    if debugMode == "Enable" and reference_docs:
        with st.expander(f"답변에서 참조한 {len(reference_docs)}개의 문서입니다."):
            for i, doc in enumerate(reference_docs):
                st.markdown(f"**{doc.metadata['name']}**: {doc.page_content}")
                st.markdown("---")

# Greet user
if not st.session_state.greetings:
    with st.chat_message("assistant"):
        intro = "아마존 베드락을 이용하여 주셔서 감사합니다. 편안한 대화를 즐기실수 있으며, 파일을 업로드하면 요약을 할 수 있습니다."
        st.markdown(intro)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": intro})
        st.session_state.greetings = True

if clear_button or "messages" not in st.session_state:
    st.session_state.messages = []        
    uploaded_file = None
    
    st.session_state.greetings = False
    chat.clear_chat_history()
    st.rerun()    

# Always show the chat input
if prompt := st.chat_input("메시지를 입력하세요."):
    with st.chat_message("user"):  # display user message in chat message container
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})  # add user message to chat history
    prompt = prompt.replace('"', "").replace("'", "")
    logger.info(f"prompt: {prompt}")

    with st.chat_message("assistant"):
        if mode == '일상적인 대화':
            stream = chat.general_conversation(prompt)            
            response = st.write_stream(stream)
            logger.info(f"response: {response}")
            st.session_state.messages.append({"role": "assistant", "content": response})

            chat.save_chat_history(prompt, response)

        elif mode == 'RAG':
            with st.status("running...", expanded=True, state="running") as status:
                response, reference_docs = chat.run_rag_with_knowledge_base(prompt, st)                           
                st.write(response)
                logger.info(f"response: {response}")

                st.session_state.messages.append({"role": "assistant", "content": response})

                chat.save_chat_history(prompt, response)
            
            show_references(reference_docs) 
                
        elif mode == 'Agent':            
            sessionState = ""

            with st.status("thinking...", expanded=True, state="running") as status:
                notification_queue = NotificationQueue(container=status)

                skill_list = selected_skills if selected_skills else []
                logger.info(f"skill_list: {skill_list}")

                response, artifacts = asyncio.run(langgraph_agent.run_langgraph_agent(
                    query=prompt, 
                    mcp_servers=mcp_servers, 
                    skill_list=skill_list,
                    history_mode="Enable", 
                    notification_queue=notification_queue))

            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "artifacts": artifacts if artifacts else []
            })

            for url in artifacts:
                logger.info(f"url: {url}")
                file_name = url[url.rfind('/')+1:]
                st.image(url, caption=file_name, use_container_width=True)

        elif mode == 'OCR Agent':            
            sessionState = ""

            with st.status("thinking...", expanded=True, state="running") as status:
                notification_queue = NotificationQueue(container=status)

                response, artifacts = asyncio.run(langgraph_agent.run_ocr_agent(
                    query=prompt, 
                    notification_queue=notification_queue))

            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "artifacts": artifacts if artifacts else []
            })

            for url in artifacts:
                logger.info(f"url: {url}")
                if not isinstance(url, str):
                    continue
                file_name = url[url.rfind('/') + 1:]

                if url.lower().endswith(".md"):
                    markdown_content = None
                    try:
                        if url.startswith("http://") or url.startswith("https://"):
                            rel_path = unquote(urlparse(url).path).lstrip("/")
                            local_candidate = os.path.join(langgraph_agent.WORKING_DIR, rel_path)
                            if os.path.isfile(local_candidate):
                                with open(local_candidate, "r", encoding="utf-8") as f:
                                    markdown_content = f.read()
                            else:
                                with urllib.request.urlopen(url, timeout=15) as r:
                                    markdown_content = r.read().decode("utf-8", errors="replace")
                        elif os.path.isfile(url):
                            with open(url, "r", encoding="utf-8") as f:
                                markdown_content = f.read()
                    except Exception as e:
                        logger.warning(f"failed to load markdown {url}: {e}")

                    if markdown_content is not None:
                        st.markdown(f"### 📄 {file_name}")
                        st.caption(url)
                        st.markdown(markdown_content)
                        st.markdown("---")
                    else:
                        st.warning(f"Markdown 파일을 불러오지 못했습니다: {url}")
                else:
                    st.image(url, caption=file_name, use_container_width=True)

                
        else:
            with st.status("thinking...", expanded=True, state="running") as status:
                summary = chat.summarize_image(file_bytes, prompt, st)
                st.write(summary)

                artifacts_dir = langgraph_agent.ARTIFACTS_DIR
                os.makedirs(artifacts_dir, exist_ok=True)
                artifact_name = f"image_summary_{uuid.uuid4().hex}.md"
                artifact_path = os.path.join(artifacts_dir, artifact_name)
                md_body = summary if isinstance(summary, str) else str(summary)
                with open(artifact_path, "w", encoding="utf-8") as f:
                    f.write(md_body)

                artifact_url = chat.upload_to_s3(md_body.encode("utf-8"), artifact_name)
                if artifact_url:
                    st.markdown(
                        f"마크다운 artifact가 저장되었습니다. "
                        f"[S3 링크]({artifact_url}) · 로컬: `{artifact_path}`"
                    )
                    assistant_content = (
                        f"{md_body}\n\n---\n\n"
                        f"[이미지 분석 요약 (markdown artifact)]({artifact_url})"
                    )
                else:
                    st.warning(
                        f"S3 업로드에 실패했거나 버킷/공유 URL이 설정되지 않았습니다. "
                        f"로컬 artifact: `{artifact_path}`"
                    )
                    assistant_content = md_body

                chat.save_chat_history("이미지를 내용을 분석합니다.", assistant_content)

                st.session_state.messages.append({"role": "assistant", "content": assistant_content})

def main():
    """Entry point for the application."""
    # This function is used as an entry point when running as a package
    # The code above is already running the Streamlit app
    pass


if __name__ == "__main__":
    # This is already handled by Streamlit
    pass
