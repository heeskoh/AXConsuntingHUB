import os
import json
import logging
import asyncio
import aiohttp
import tempfile
import markdown
import fitz
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
# from werkzeug.utils import secure_filename # 파일 이름 유지를 위해 사용 안 함

# 내부 모듈 임포트
from utils.exceptions import APIException
from utils.config import get_api_key, setup_logging
from agents.router import AgentRouter
from agents.gemini_agent import GeminiAgent

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 경로 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Flask 앱 초기화
app = Flask(__name__, static_folder=STATIC_FOLDER, template_folder=BASE_DIR)
CORS(app)

# 로깅 설정 초기화
setup_logging()
logger = logging.getLogger(__name__)

# 업로드 폴더 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 라우터 에이전트 초기화
try:
    router = AgentRouter()
except Exception as e:
    logger.error(f"Failed to initialize AgentRouter: {e}")
    router = None


# --- 헬퍼 함수 ---
def read_file_content(file_path):
    """파일 경로를 받아 확장자에 따라 텍스트 내용을 추출합니다."""
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    content = ""
    try:
        if file_extension == '.pdf':
            doc = fitz.open(file_path)
            for page in doc:
                content += page.get_text()
            doc.close()
            return content[:15000]
        elif file_extension in ['.txt', '.md', '.json', '.csv', '.py', '.html', '.css', '.js']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()[:15000]
        else:
            return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"파일('{os.path.basename(file_path)}')을 읽는 중 오류가 발생했습니다."


# --- 기본 및 채팅 API 라우트 ---
@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/api/chat', methods=['POST'])
async def chat_endpoint():
    # 이 함수의 내용은 변경되지 않았습니다.
    if not router:
        return jsonify({"error": "서비스 준비 중입니다. 잠시 후 다시 시도해주세요."}), 503
    if 'prompt' not in request.form:
        return jsonify({"error": "프롬프트가 비어있습니다."}), 400
    try:
        # ... (기존 채팅 처리 로직은 그대로 유지) ...
        data = request.form
        prompt = data.get('prompt', '')
        use_validation = data.get('use_validation', 'false').lower() == 'true'
        chat_history_str = data.get('chat_history', '[]')
        chat_history = json.loads(chat_history_str)
        llm_model_choice = data.get('llm_model_choice', 'openai')
        files = request.files.getlist('files')

        file_contents = []
        temp_files = []

        if files:
            for file in files:
                if file.filename == '': continue
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, file.filename)
                file.save(temp_path)
                temp_files.append((temp_path, temp_dir))
                content = read_file_content(temp_path)
                file_contents.append(f"--- 파일: {file.filename} ---\n{content or '(내용을 읽을 수 없음)'}\n--- 파일 끝 ---")

        prompt_with_context = "\n".join(file_contents) + "\n\n" + prompt if file_contents else prompt

        agent_name, agent_description, response_data = await router.handle_request(
            prompt_with_context, chat_history, llm_model_choice, use_validation
        )

        for path, dir_path in temp_files:
            try:
                os.remove(path); os.rmdir(dir_path)
            except OSError as e:
                logger.error(f"Error cleaning up temp file {path}: {e}")

        return jsonify({
            "agent_name": agent_name,
            "agent_description": agent_description,
            "response_content": response_data.get("response_content", ""),
            "source_info": response_data.get("source_info", [])
        })

    except APIException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        logger.exception("Internal server error")
        return jsonify({"error": f"내부 서버 오류가 발생했습니다: {str(e)}"}), 500


# --- AX 방법론 관련 API 라우트 (복원된 부분) ---
@app.route('/api/ax-methodology')
def get_ax_methodology():
    filepath = os.path.join(BASE_DIR, 'ax_methodology_tasks.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "AX Methodology tasks file not found"}), 404

# ===================================================================
# 2025-09-18 09:45 KST: 누락되었던 API 라우트 복원
# ===================================================================
@app.route('/api/prompt-templates/<string:task_id>')
def get_prompt_templates_for_task(task_id):
    """최하위 Task에 대한 프롬프트 템플릿 JSON 파일을 반환합니다."""
    filename = f"{task_id}_prompt.json"
    filepath = os.path.join(DATA_FOLDER, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        return jsonify(templates)
    except FileNotFoundError:
        logger.warning(f"Prompt template file not found for task {task_id}: {filepath}")
        return jsonify([])
    except Exception as e:
        logger.error(f"Error reading prompt template file for task {task_id}: {e}")
        return jsonify({"error": "Error reading prompt template file"}), 500

@app.route('/api/task-files/<string:task_id>')
def get_task_files(task_id):
    """2단계 Task와 관련된 파일 목록을 반환합니다."""
    folder_name = f"{task_id}_files"
    folder_path = os.path.join(DATA_FOLDER, folder_name)
    if not os.path.isdir(folder_path):
        return jsonify([])
    
    files_info = []
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith('.json'):
                filepath = os.path.join(folder_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        files_info.append({
                            "type": "Reference File",
                            "info": content.get("title", filename),
                            "summary": content.get("summary", ""),
                            "url": f"/data/{folder_name}/{filename}"
                        })
                except Exception as e:
                    logger.error(f"Error reading file {filepath}: {e}")
        return jsonify(files_info)
    except Exception as e:
        return jsonify({"error": "Error listing task files"}), 500

# ===================================================================
# 2025-09-18 23:10 KST: API 반환 키 값을 original_file_name으로 통일
# ===================================================================
@app.route('/api/reference-materials/<string:folder_name>')
def get_reference_materials(folder_name):
    """지정된 폴더 내의 Abstract_*.json 파일 목록과 내용을 반환합니다."""
    folder_path = os.path.join(DATA_FOLDER, folder_name)
    if not os.path.isdir(folder_path):
        return jsonify([])

    materials = []
    try:
        for filename in os.listdir(folder_path):
            if filename.startswith('Abstract_') and filename.endswith('.json'):
                filepath = os.path.join(folder_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        materials.append({
                            "json_name": filename,
                            # FIX: 키 이름을 'original_file_name'으로 수정
                            "original_file_name": content.get("original_file_name", filename), 
                            "summary_html": content.get("summary_html", "<p>요약 내용이 없습니다.</p>")
                        })
                except Exception as e:
                    logger.error(f"참고자료 파일을 읽는 중 오류 발생 {filepath}: {e}")
        
        return jsonify(materials)
    except Exception as e:
        logger.error(f"참고자료 목록을 가져오는 중 오류 발생 {folder_name}: {e}")
        return jsonify({"error": "참고자료 목록을 가져오는 중 오류 발생"}), 500
    

# --- 데이터 파일 직접 서빙 라우트 ---
@app.route('/data/<path:subpath>')
def serve_data_files(subpath):
    return send_from_directory(DATA_FOLDER, subpath)

if __name__ == '__main__':
    app.run(debug=True, port=5000)