# keyextraction.py
import os
import sys
import json
import asyncio
import anthropic
import fitz  # PyMuPDF
from dotenv import load_dotenv
import re  # ⭐ 추가: 정규식을 위해 필요


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

# ⭐ 추가: JSON 검증 및 수정 함수
def validate_and_fix_json(text):
    """JSON 텍스트를 검증하고 간단한 오류를 수정합니다."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print("JSON 자동 수정을 시도합니다...")
        
        # 간단한 수정 시도
        text = text.strip()
        
        # 끝나지 않은 객체나 배열 처리
        if text.count('{') > text.count('}'):
            text += '}'
        if text.count('[') > text.count(']'):
            text += ']'
        if text.count('"') % 2 == 1:
            text += '"'
            
        try:
            return json.loads(text)
        except:
            print("JSON 자동 수정 실패. 원본 텍스트를 반환합니다.")
            raise

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

    # 4. ANTHROPIC API 설정 및 호출
    api_key = get_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        print("오류: .env 파일에 ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        return

    try:
        # Claude 비동기 클라이언트 생성
        client = anthropic.AsyncAnthropic(api_key=api_key)

        # ⭐ 수정: 더 명확한 JSON 요청 프롬프트
        final_prompt = f"""다음은 '{input_filename}' 파일의 내용입니다.

---
{file_content}
---

위 내용을 바탕으로 아래 요청사항을 따라 요약해줘:
{prompt_template}

중요: 
1. 응답은 반드시 유효한 JSON 형식으로만 작성하세요.
2. JSON 외의 다른 설명이나 텍스트는 절대 포함하지 마세요.
3. JSON 객체가 완전히 닫혀있는지 확인하세요.
4. 문자열 값에는 이스케이프 문자를 올바르게 사용하세요."""
     
        print(f"Claude API로 '{input_filename}' 파일 요약 요청 중...")
        
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,  # ⭐ 수정: 토큰 수를 늘려서 응답이 잘리지 않도록
            messages=[
                {"role": "user", "content": final_prompt}
            ]
        )
        
        summary_text = response.content[0].text.strip()
        
        # ⭐ 추가: 디버깅을 위한 원본 응답 출력
        print("=== Claude 원본 응답 ===")
        print(summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
        print("=====================")
        
        # ⭐ 수정: 더 강력한 JSON 추출 로직
        if summary_text.startswith("```json"):
            # ```json과 ``` 사이의 내용 추출
            json_match = re.search(r'```json\s*(.*?)\s*```', summary_text, re.DOTALL)
            if json_match:
                summary_text = json_match.group(1).strip()
        elif summary_text.startswith("```"):
            # 일반 코드블록 처리
            json_match = re.search(r'```\s*(.*?)\s*```', summary_text, re.DOTALL)
            if json_match:
                summary_text = json_match.group(1).strip()
        
        # ⭐ 추가: JSON이 {로 시작하지 않으면 찾아서 추출
        if not summary_text.startswith('{'):
            json_match = re.search(r'\{.*\}', summary_text, re.DOTALL)
            if json_match:
                summary_text = json_match.group(0)
        
        print("=== 추출된 JSON ===")
        print(summary_text)
        print("==================")

        # ⭐ 수정: 강화된 JSON 파싱 로직
        try:
            summary_json = validate_and_fix_json(summary_text)
            print("JSON 파싱 성공!")
        except Exception as json_error:
            print(f"JSON 파싱 실패: {json_error}")
            print("응답 텍스트:")
            print(summary_text)
            return

    except Exception as e:
        print(f"Claude API 호출 또는 결과 처리 중 오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")  # ⭐ 추가: 오류 타입 출력
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
