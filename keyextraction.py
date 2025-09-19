# keyextraction.py
import os
import sys
import json
import asyncio
import fitz  # PyMuPDF
from dotenv import load_dotenv
import google.generativeai as genai

# --- 유틸리티 함수 ---
def get_api_key(api_name):
    """ .env 파일에서 API 키를 가져옵니다. (스크립트와 같은 위치에 .env 파일이 있어야 함) """
    load_dotenv()
    return os.getenv(api_name)

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
        elif file_extension in ['.txt', '.md', '.json', '.csv', '.py', '.html', '.css', '.js']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            print(f"지원하지 않는 파일 형식입니다: {file_extension}")
            return None
        
        # API 토큰 제한을 고려하여 콘텐츠 길이 제한
        return content[:15000] if len(content) > 15000 else content
    except Exception as e:
        print(f"파일을 읽는 중 오류가 발생했습니다 ({file_path}): {e}")
        return None

# ===================================================================
# 2025-09-17 23:45 KST: workingdir 인자를 받도록 함수 시그니처 수정
# ===================================================================
async def summarize_document(working_dir, input_filename, output_filename):
    """지정된 작업 디렉토리 내의 문서를 요약하고 결과를 JSON 파일로 저장합니다."""
    
    print(f"작업 디렉토리: {working_dir}")

    # 1. 경로 설정
    if not os.path.isdir(working_dir):
        print(f"오류: 작업 디렉토리를 찾을 수 없습니다 - {working_dir}")
        return
        
    input_file_path = os.path.join(working_dir, input_filename)
    if not os.path.exists(input_file_path):
        print(f"오류: 입력 파일을 찾을 수 없습니다 - {input_file_path}")
        return

    # 2. 프롬프트 템플릿 로드
    prompt_template_path = os.path.join(working_dir, 'prompt_templates.json')
    if not os.path.exists(prompt_template_path):
        print(f"오류: 'prompt_templates.json' 파일을 다음 위치에서 찾을 수 없습니다 - {working_dir}")
        return
        
    try:
        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
            if isinstance(templates, list) and len(templates) > 0 and 'template' in templates[0]:
                prompt_template = templates[0]['template']
            else:
                raise ValueError("프롬프트 템플릿 형식이 올바르지 않습니다.")
    except Exception as e:
        print(f"프롬프트 템플릿 파일을 읽는 중 오류 발생: {e}")
        return

    # 3. 입력 파일 내용 읽기
    file_content = read_file_content(input_file_path)
    if not file_content:
        return

    # 4. Gemini API 설정 및 호출
    api_key = get_api_key("GEMINI_API_KEY")
    if not api_key:
        print("오류: .env 파일에 GEMINI_API_KEY가 설정되지 않았습니다.")
        return

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        final_prompt = f"다음은 '{input_filename}' 파일의 내용입니다.\n\n---\n{file_content}\n---\n\n위 내용을 바탕으로 아래 요청사항을 따라 JSON 형식으로 요약해줘:\n{prompt_template}"
        
        print(f"Gemini API로 '{input_filename}' 파일 요약 요청 중...")
        response = await model.generate_content_async(final_prompt)
        
        summary_text = response.text
        if summary_text.strip().startswith("```json"):
            summary_text = summary_text.strip()[7:-3].strip()

        summary_json = json.loads(summary_text)

    except Exception as e:
        print(f"Gemini API 호출 또는 결과 처리 중 오류 발생: {e}")
        return

    # 5. 결과 JSON 파일로 저장
    final_output = {
        "original_file_name": input_filename,
        **summary_json
    }
    
    output_path = os.path.join(working_dir, output_filename)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        print(f"\n요약 완료! 결과가 다음 파일에 저장되었습니다: {output_path}")
    except Exception as e:
        print(f"결과 파일을 저장하는 중 오류 발생: {e}")


if __name__ == "__main__":
    # ===================================================================
    # 2025-09-17 23:45 KST: 명령어 인자 3개(작업폴더, 입력, 출력)를 받도록 수정
    # ===================================================================
    if len(sys.argv) != 4:
        print("사용법: python keyextraction.py <working_dir> <input_filename> <output_filename.json>")
        sys.exit(1)
    
    work_dir = sys.argv[1]
    in_file = sys.argv[2]
    out_file = sys.argv[3]
    asyncio.run(summarize_document(work_dir, in_file, out_file))