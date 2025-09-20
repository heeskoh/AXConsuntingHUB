# backend.py
# 2025-01-17 02:00 KST: 참고자료 상세 표시 기능 완전 구현
# 2025-01-17 14:00 KST: 참고자료 표시 기능 대폭 개선 - 문서 유형별 최적화된 HTML 생성

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

# 내부 모듈 임포트
from utils.exceptions import APIException
from utils.config import get_api_key, setup_logging
from agents.router import AgentRouter
from agents.gemini_agent import GeminiAgent

# .env 파일에서 환경 변수 로드
load_dotenv()

# 경로 설정
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
    if not router:
        return jsonify({"error": "서비스 준비 중입니다. 잠시 후 다시 시도해주세요."}), 503
    if 'prompt' not in request.form:
        return jsonify({"error": "프롬프트가 비어있습니다."}), 400
    
    try:
        data = request.form
        prompt = data.get('prompt', '')
        use_validation = data.get('use_validation', 'false').lower() == 'true'
        chat_history_str = data.get('chat_history', '[]')
        chat_history = json.loads(chat_history_str)
        llm_model_choice = data.get('llm_model_choice', 'Gemini')
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
                os.remove(path)
                os.rmdir(dir_path)
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


# --- AX 방법론 관련 API 라우트 ---
@app.route('/api/ax-methodology')
def get_ax_methodology():
    filepath = os.path.join(BASE_DIR, 'ax_methodology_tasks.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "AX Methodology tasks file not found"}), 404


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


# 2025-01-17 02:30 KST: 참고자료 API - 전체 내용 표시
# 2025-01-17 14:00 KST: 참고자료 표시 기능 대폭 개선 - 문서 유형별 최적화된 렌더링
@app.route('/api/reference-materials/<string:folder_name>')
def get_reference_materials(folder_name):
    """지정된 폴더 내의 Abstract_*.json 파일 목록과 전체 내용을 반환합니다."""
    folder_path = os.path.join(DATA_FOLDER, folder_name)
    
    if not os.path.isdir(folder_path):
        logger.warning(f"Reference folder not found: {folder_path}")
        return jsonify([])

    materials = []
    try:
        for filename in os.listdir(folder_path):
            if filename.startswith('Abstract_') and filename.endswith('.json'):
                filepath = os.path.join(folder_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        
                        original_name = content.get('original_file_name', 
                                                   content.get('원본이름', filename))
                        
                        summary_html = content.get('summary_html', '')
                        if not summary_html:
                            # 2025-01-17 14:00 KST: 기존 generate_comprehensive_summary_html을 
                            # generate_enhanced_summary_html로 대체하여 문서 유형별 최적화
                            summary_html = generate_enhanced_summary_html(content)
                        
                        materials.append({
                            "json_name": filename,
                            "original_file_name": original_name,
                            "summary_html": summary_html
                        })
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in {filepath}: {e}")
                except Exception as e:
                    logger.error(f"Error reading reference file {filepath}: {e}")
        
        materials.sort(key=lambda x: x['json_name'])
        return jsonify(materials)
    
    except Exception as e:
        logger.error(f"Error listing reference materials in {folder_name}: {e}")
        return jsonify({"error": "참고자료 목록 조회 실패"}), 500


# 2025-01-17 14:00 KST: 새로 추가 - 향상된 문서 유형별 HTML 생성 함수
def generate_enhanced_summary_html(content):
    """JSON 내용을 문서 유형에 따라 최적화된 HTML로 생성합니다."""
    
    # 문서 유형 감지
    doc_type = detect_document_type(content)
    
    html = '<div class="reference-content">'
    
    # 공통 헤더 정보
    html += generate_header_section(content)
    
    # 문서 유형별 본문 생성
    if doc_type == 'proposal':
        html += generate_proposal_content(content)
    elif doc_type == 'kickoff':
        html += generate_kickoff_content(content)
    elif doc_type == 'environment':
        html += generate_environment_content(content)
    elif doc_type == 'it_analysis':
        html += generate_it_analysis_content(content)
    else:
        html += generate_generic_content(content)
    
    html += '</div>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 문서 유형 감지 함수
def detect_document_type(content):
    """JSON 내용을 분석하여 문서 유형을 감지합니다."""
    if '제안' in content.get('프로젝트 이름', '') or '제안' in content.get('original_file_name', ''):
        return 'proposal'
    elif '착수' in content.get('original_file_name', '') or 'kickoff' in content.get('original_file_name', '').lower():
        return 'kickoff'
    elif '환경분석' in content.get('original_file_name', '') or 'Env' in content.get('original_file_name', ''):
        return 'environment'
    elif 'IT' in content.get('original_file_name', '') or 'IT' in content.get('프로젝트_이름', ''):
        return 'it_analysis'
    else:
        return 'generic'


# 2025-01-17 14:00 KST: 새로 추가 - 공통 헤더 섹션 생성 함수
def generate_header_section(content):
    """공통 헤더 섹션을 생성합니다."""
    html = ''
    
    # 문서 제목
    title = (content.get('프로젝트 이름') or 
             content.get('프로젝트이름') or 
             content.get('프로젝트_이름') or 
             content.get('reportTitle') or
             content.get('original_file_name', '문서'))
    html += f'<h1 class="document-title">{title}</h1>'
    
    # 원본 파일명
    original_name = content.get('original_file_name') or content.get('원본이름')
    if original_name:
        html += f'<div class="file-info"><strong>원본 파일:</strong> {original_name}</div>'
    
    # 핵심 키워드
    keywords = (content.get('핵심키워드') or 
                content.get('핵심_키워드') or 
                content.get('주요 키워드 10개') or 
                content.get('keywords', []))
    if keywords:
        html += '<div class="keywords-section">'
        html += '<h3>핵심 키워드</h3>'
        html += '<div class="keywords-container">'
        for keyword in keywords[:15]:
            html += f'<span class="keyword-tag">{keyword}</span>'
        html += '</div></div>'
    
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 제안서 유형 컨텐츠 생성 함수
def generate_proposal_content(content):
    """제안서 유형의 컨텐츠를 생성합니다."""
    html = ''
    
    # 프로젝트 개요
    html += '<section class="project-overview">'
    html += '<h2>프로젝트 개요</h2>'
    
    if content.get('고객사 이름'):
        html += f'<div class="info-item"><strong>고객사:</strong> {content["고객사 이름"]}</div>'
    
    # 배경, 범위, 목적
    sections = [
        ('프로젝트(제안)의 배경', '프로젝트 배경'),
        ('프로젝트(제안)의 범위', '프로젝트 범위'),
        ('프로젝트(제안)의 목적', '프로젝트 목적')
    ]
    
    for key, title in sections:
        if content.get(key):
            html += f'<div class="subsection">'
            html += f'<h4>{title}</h4>'
            html += f'<p>{content[key]}</p>'
            html += '</div>'
    
    html += '</section>'
    
    # 제안 전략 및 특장점
    html += '<section class="proposal-strategy">'
    html += '<h2>제안 전략 및 특장점</h2>'
    
    if content.get('제안 전략 혹은 컨설팅 전략'):
        html += f'<div class="subsection">'
        html += f'<h4>컨설팅 전략</h4>'
        html += f'<p>{content["제안 전략 혹은 컨설팅 전략"]}</p>'
        html += '</div>'
    
    if content.get('제안의 특장점'):
        html += f'<div class="subsection">'
        html += f'<h4>제안의 특장점</h4>'
        html += f'<p>{content["제안의 특장점"]}</p>'
        html += '</div>'
    
    if content.get('기대효과'):
        html += f'<div class="subsection">'
        html += f'<h4>기대 효과</h4>'
        html += f'<p>{content["기대효과"]}</p>'
        html += '</div>'
    
    html += '</section>'
    
    # 수행 방안
    if content.get('수행방안 혹은 컨설팅 방안'):
        html += generate_implementation_plan(content['수행방안 혹은 컨설팅 방안'])
    
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 착수보고서 유형 컨텐츠 생성 함수
def generate_kickoff_content(content):
    """착수보고서 유형의 컨텐츠를 생성합니다."""
    html = ''
    
    # 보고서 목표
    if content.get('보고서목표'):
        html += '<section class="report-objectives">'
        html += '<h2>프로젝트 목표</h2>'
        html += '<ul class="objectives-list">'
        for objective in content['보고서목표']:
            html += f'<li>{objective}</li>'
        html += '</ul>'
        html += '</section>'
    
    # 보고서 목차
    if content.get('보고서목차'):
        html += generate_table_of_contents(content['보고서목차'])
    
    # 본문 요약
    if content.get('본문요약'):
        html += generate_content_summary(content['본문요약'])
    
    # 개선기회 및 Key Finding
    if content.get('개선기회키파인딩'):
        html += generate_key_findings(content['개선기회키파인딩'])
    
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 환경분석서 유형 컨텐츠 생성 함수
def generate_environment_content(content):
    """환경분석서 유형의 컨텐츠를 생성합니다."""
    html = ''
    
    # 보고서 목표
    if content.get('보고서목표'):
        html += '<section class="report-objectives">'
        html += '<h2>분석 목표</h2>'
        html += '<ul class="objectives-list">'
        for objective in content['보고서목표']:
            html += f'<li>{objective}</li>'
        html += '</ul>'
        html += '</section>'
    
    # 보고서 목차
    if content.get('보고서목차'):
        html += '<section class="table-of-contents">'
        html += '<h2>보고서 목차</h2>'
        html += '<div class="toc-container">'
        for key, value in content['보고서목차'].items():
            html += f'<div class="toc-item"><strong>{key}.</strong> {value}</div>'
        html += '</div>'
        html += '</section>'
    
    # 본문 요약
    if content.get('본문요약'):
        html += '<section class="content-summary">'
        html += '<h2>상세 분석 내용</h2>'
        for key, value in content['본문요약'].items():
            if key != '수행단계' and key != '환경분석프로세스':
                html += f'<div class="analysis-item">'
                html += f'<h4>{key.replace("_", " ")}</h4>'
                html += f'<p>{value}</p>'
                html += '</div>'
        html += '</section>'
    
    # 개선기회
    if content.get('개선기회'):
        html += generate_improvement_opportunities(content['개선기회'])
    
    return html


# 2025-01-17 14:00 KST: 새로 추가 - IT 현황분석서 유형 컨텐츠 생성 함수
def generate_it_analysis_content(content):
    """IT 현황분석서 유형의 컨텐츠를 생성합니다."""
    html = ''
    
    # 보고서 목표
    if content.get('보고서의_목표'):
        html += '<section class="report-objectives">'
        html += '<h2>분석 목표</h2>'
        html += '<ul class="objectives-list">'
        for objective in content['보고서의_목표']:
            html += f'<li>{objective}</li>'
        html += '</ul>'
        html += '</section>'
    
    # 보고서 목차 (계층 구조)
    if content.get('보고서_목차'):
        html += generate_hierarchical_toc(content['보고서_목차'])
    
    # 본문 요약
    if content.get('본문_요약'):
        html += '<section class="content-summary">'
        html += '<h2>IT 현황 분석 결과</h2>'
        for key, value in content['본문_요약'].items():
            html += f'<div class="analysis-item">'
            html += f'<h4>{key.replace("_", " ")}</h4>'
            html += f'<p>{value}</p>'
            html += '</div>'
        html += '</section>'
    
    # 개선기회
    if content.get('개선기회_key_finding'):
        html += generate_key_findings(content['개선기회_key_finding'])
    
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 목차 정보 HTML 생성 함수
def generate_table_of_contents(toc_data):
    """목차 정보를 HTML로 생성합니다."""
    html = '<section class="table-of-contents">'
    html += '<h2>보고서 목차</h2>'
    html += '<div class="toc-container">'
    
    if isinstance(toc_data, list):
        for item in toc_data:
            if isinstance(item, dict):
                html += f'<div class="toc-major">{item.get("대분류", "")}</div>'
                if item.get("소분류"):
                    for sub_item in item["소분류"]:
                        html += f'<div class="toc-minor">• {sub_item}</div>'
            else:
                html += f'<div class="toc-item">{item}</div>'
    
    html += '</div>'
    html += '</section>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 계층적 목차 HTML 생성 함수
def generate_hierarchical_toc(toc_data):
    """계층적 목차를 HTML로 생성합니다."""
    html = '<section class="table-of-contents">'
    html += '<h2>보고서 목차</h2>'
    html += '<div class="toc-hierarchical">'
    
    for key, value in toc_data.items():
        level = len(key.split('.'))
        indent_class = f'toc-level-{min(level, 4)}'
        html += f'<div class="{indent_class}"><strong>{key}</strong> {value}</div>'
    
    html += '</div>'
    html += '</section>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 본문 요약 HTML 생성 함수
def generate_content_summary(summary_data):
    """본문 요약을 HTML로 생성합니다."""
    html = '<section class="content-summary">'
    html += '<h2>상세 내용</h2>'
    
    if isinstance(summary_data, list):
        for item in summary_data:
            if isinstance(item, dict):
                html += f'<div class="summary-item">'
                html += f'<h4>{item.get("세부목차", "")}</h4>'
                html += f'<p>{item.get("내용", "")}</p>'
                html += '</div>'
    elif isinstance(summary_data, dict):
        for key, value in summary_data.items():
            html += f'<div class="summary-item">'
            html += f'<h4>{key.replace("_", " ")}</h4>'
            html += f'<p>{value}</p>'
            html += '</div>'
    
    html += '</section>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - Key Finding 및 개선기회 HTML 생성 함수
def generate_key_findings(findings_data):
    """개선기회 및 Key Finding을 HTML로 생성합니다."""
    html = '<section class="key-findings">'
    html += '<h2>핵심 발견사항 및 개선기회</h2>'
    
    for item in findings_data:
        html += '<div class="finding-item">'
        
        # 유형별 아이콘 추가
        finding_type = item.get('유형') or item.get('구분', '')
        icon = '💡' if '개선기회' in finding_type else '🔍' if 'Key Finding' in finding_type else '📋'
        
        html += f'<div class="finding-header">'
        html += f'<span class="finding-icon">{icon}</span>'
        html += f'<span class="finding-type">{finding_type}</span>'
        html += f'<span class="finding-title">{item.get("장표제목", "")}</span>'
        html += '</div>'
        
        content = item.get('요약내용') or item.get('내용', '')
        html += f'<div class="finding-content">{content}</div>'
        
        html += '</div>'
    
    html += '</section>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 개선기회 HTML 생성 함수
def generate_improvement_opportunities(opportunities):
    """개선기회를 HTML로 생성합니다."""
    html = '<section class="improvement-opportunities">'
    html += '<h2>개선기회</h2>'
    
    for opportunity in opportunities:
        html += '<div class="opportunity-item">'
        html += f'<h4>💡 {opportunity.get("세부목차", "")}</h4>'
        html += f'<div class="opportunity-content">{opportunity.get("요약내용", "")}</div>'
        html += '</div>'
    
    html += '</section>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 수행방안 HTML 생성 함수
def generate_implementation_plan(plan_data):
    """수행방안을 HTML로 생성합니다."""
    html = '<section class="implementation-plan">'
    html += '<h2>수행 방안</h2>'
    
    for key, value in plan_data.items():
        html += f'<div class="plan-section">'
        html += f'<h3>{key}</h3>'
        
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                html += f'<div class="plan-subsection">'
                html += f'<h4>{sub_key}</h4>'
                html += f'<p>{sub_value}</p>'
                html += '</div>'
        else:
            html += f'<p>{value}</p>'
        
        html += '</div>'
    
    html += '</section>'
    return html


# 2025-01-17 14:00 KST: 새로 추가 - 일반 문서 유형 컨텐츠 생성 함수
def generate_generic_content(content):
    """일반적인 문서 유형의 컨텐츠를 생성합니다."""
    html = ''
    
    # 기본 정보들을 순서대로 표시
    skip_keys = {'original_file_name', '원본이름', '핵심키워드', '핵심_키워드', '주요 키워드 10개', 'keywords'}
    
    for key, value in content.items():
        if key in skip_keys:
            continue
            
        html += f'<section class="content-section">'
        html += f'<h2>{key.replace("_", " ")}</h2>'
        
        if isinstance(value, list):
            html += '<ul>'
            for item in value:
                html += f'<li>{item}</li>'
            html += '</ul>'
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                html += f'<h4>{sub_key}</h4>'
                html += f'<p>{sub_value}</p>'
        else:
            html += f'<p>{value}</p>'
        
        html += '</section>'
    
    return html


# 2025-01-17 03:00 KST: 전체 내용을 포함하는 HTML 생성 (기존 함수 제거됨)
# 2025-01-17 14:00 KST: 위의 새로운 함수들로 대체되어 더 이상 사용하지 않음


# --- 데이터 파일 서빙 ---
@app.route('/data/<path:subpath>')
def serve_data_files(subpath):
    return send_from_directory(DATA_FOLDER, subpath)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
