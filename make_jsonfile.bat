REM  readme 

REM workingdir에  prompt_templates.json 에  프롬프트가 지정되어 있어야 하며, 
REM 동일 폴더에 입력파일이 있어야 한다. 
REM 결과 파일도 같은 폴더에 생성된다. 

REM  python keyextraction.py <workingdir> <inputfilename> <outputfilename.json>

REM  python keyextraction.py <workingdir> <inputfilename> <outputfilename.json>

@echo off
:: ===========================================
:: 문서 요약 배치 스크립트
:: 한글 파일명 처리를 위한 설정
:: ===========================================

:: UTF-8 코드페이지 설정
chcp 65001 > nul
echo 문서 요약 작업을 시작합니다...

:: 현재 디렉토리 확인
echo 현재 작업 디렉토리: %CD%

:: 파일 존재 여부 확인 및 실행
echo.
if exist "data\901-proposal_files" "202505_SH개발공사_인공지능 전환(AX) 활용 정보화전략계획(ISP)_제안서.pdf"  (
    python keyextraction.py "data\901-proposal_files" "202505_SH개발공사_인공지능 전환(AX) 활용 정보화전략계획(ISP)_제안서.pdf" "Abstract_202505_SH_AXISP_Proposal.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - N202505_SH개발공사_인공지능 전환(AX) 활용 정보화전략계획(ISP)_제안서.pdf
)

echo.
if exist "data\901-proposal_files" "202406_법제처_생성형AI_ISP_통합본.pdf"  (
    python keyextraction.py "data\901-proposal_files" "202406_법제처_생성형AI_ISP_통합본.pdf" "Abstract_202505_SH_AXISP_Proposal.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - 202406_법제처_생성형AI_ISP_통합본.pdf
)


echo.
if exist "data\110-Env_files" "NHSB ISP_환경분석서_202405_v1.0.pdf" (
    python keyextraction.py "data\110-Env_files" "NHSB ISP_환경분석서_202405_v1.0.pdf"  "Abstract_202405_NHSB_ISP_Env.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_환경분석서_202405_v1.0.pdf
)

echo.
if exist "data\110-Env_files" "SH_AXISP_환경분석서_20250731_v0.9.pdf" (
    python keyextraction.py "data\110-Env_files" "SH_AXISP_환경분석서_20250731_v0.9.pdf"  "Abstract_202507_SH_AXISP_Env.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_환경분석서_20250731_v0.9.pdf
)

echo.
if exist "data\120-TechEnv_files" "NHSB ISP_Tech환경분석서_202405_v1.0.pdf" (
    python keyextraction.py "data\120-TechEnv_files" "NHSB ISP_Tech환경분석서_202405_v1.0.pdf"  "Abstract_202405_NHSB_ISP_TechEnv.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_Tech환경분석서_202405_v1.0.pdf
)

echo.
if exist "data\120-TechEnv_files" "SH_AXISP_기술환경분석서_20250731_v0.9.pdf" (
    python keyextraction.py "data\120-TechEnv_files" "SH_AXISP_기술환경분석서_20250731_v0.9.pdf"  "Abstract_202507_SH_AXISP_TechEnv.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_기술환경분석서_20250731_v0.9.pdf
)

echo.
if exist "data\130-BizReq_files" "NHSB ISP_현황분석서(BIZ)_v1.0.pdf" (
   python keyextraction.py "data\130-BizReq_files" "NHSB ISP_현황분석서(BIZ)_v1.0.pdf"  "Abstract_202405_NHSB_ISP_BIZAnal.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_현황분석서(BIZ)_v1.0.pdf
)

echo.
if exist "data\130-BizReq_files" "SH_AXISP_업무환경분석-1.공사 사업추진체계 점검_ver1.4.pdf" (
   python keyextraction.py "data\130-BizReq_files" "SH_AXISP_업무환경분석-1.공사 사업추진체계 점검_ver1.4.pdf"  "Abstract_202507_SH_AXISP_BizAnal.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_업무환경분석-1.공사 사업추진체계 점검_ver1.4.pdf
)

echo.
if exist "data\130-BizReq_files" "SH_AXISP_업무환경분석-2. AI 수준진단_ver1.1.pdf" (
   python keyextraction.py "data\130-BizReq_files" "SH_AXISP_업무환경분석-2. AI 수준진단_ver1.1.pdf"  "Abstract_202507_SH_AXISP_AXMaturity.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_업무환경분석-2. AI 수준진단_ver1.1.pdf
)

echo.
if exist "data\130-BizReq_files" "SH_AXISP_업무환경분석-3. AI 서비스 요구사항_ver1.2.pdf" (
   python keyextraction.py "data\130-BizReq_files" "SH_AXISP_업무환경분석-3. AI 서비스 요구사항_ver1.2.pdf"  "Abstract_202507_SH_AXSvcNeeds.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_업무환경분석-3. AI 서비스 요구사항_ver1.2.pdf
)

echo.
if exist "data\140-AI_ITReq_files" "NHSB ISP_현황분석서(IT)_v1.0.pdf" (
   python keyextraction.py "data\140-AI_ITReq_files" "NHSB ISP_현황분석서(IT)_v1.0.pdf"  "Abstract_202405_NHSB_ISP_ITAnal.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_현황분석서(IT)_v1.0.pdf
)

echo.
if exist "data\140-AI_ITReq_files" "SH_AXISP_현황분석서(IT)_20250821_v1.0.pdf" (
   python keyextraction.py "data\140-AI_ITReq_files" "SH_AXISP_현황분석서(IT)_20250821_v1.0.pdf"  "Abstract_202507_SH_AXISP_AXITReq.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_현황분석서(IT)_20250821_v1.0.pdf
)

echo.
if exist "data\210-Vision_files" "SH_AXISP_AX비전및전략수립_20250910_VF.pdf" (
   python keyextraction.py "data\210-Vision_files" "SH_AXISP_AX비전및전략수립_20250910_VF.pdf"  "Abstract_202507_SH_AXISP_visioning.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_AX비전및전략수립_20250910_VF.pdf
)

echo.
if exist "data\220-TargetModel_files" "13_1. NHSB ISP_To-Be_AA 아키텍처 정의서_v1.0.pdf"  (
   python keyextraction.py "data\220-TargetModel_files" "13_1. NHSB ISP_To-Be_AA 아키텍처 정의서_v1.0.pdf"  "Abstract_202405_NHSB_ISP_Targetmodel_AA.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - 13_1. NHSB ISP_To-Be_AA 아키텍처 정의서_v1.0.pdf
)

echo.
if exist "data\220-TargetModel_files" "SH_AXISP_AX개선과제_개요종합_20250904_v0.51.pdf" (
   python keyextraction.py "data\220-TargetModel_files" "SH_AXISP_AX개선과제_개요종합_20250904_v0.51.pdf"  "Abstract_202507_SH_AXISP_initiative_Overview.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_AX개선과제_개요종합_20250904_v0.51.pdf
)

echo.
if exist "data\310-Implementation_files" "NHSB ISP_이행과제정의서_v.1.0.pdf" (
   python keyextraction.py "data\310-Implementation_files" "NHSB ISP_이행과제정의서_v.1.0.pdf"  "Abstract_202405_NHSB_ISP_Impl_task.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_이행과제정의서_v.1.0.pdf
)

echo.
if exist "data\320-roadmap_files" "NHSB ISP_마스터플랜정의서_v.1.0.pdf" (
   python keyextraction.py "data\320-roadmap_files" "NHSB ISP_마스터플랜정의서_v.1.0.pdf"  "Abstract_202405_NHSB_ISP_masterlan.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_마스터플랜정의서_v.1.0.pdf
)

echo.
if exist "data\430-stage-reporting_files" "NHSB ISP_착수보고_20240312_v1.0.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "NHSB ISP_착수보고_20240312_v1.0.pdf"  "Abstract_202405_NHSB_ISP_kickoff.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_착수보고_20240312_v1.0.pd
)

echo.
if exist "data\430-stage-reporting_files" "NHSB ISP_중간보고_v1.0.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "NHSB ISP_중간보고_v1.0.pdf"  "Abstract_202405_NHSB_ISP_interim.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_중간보고_v1.0.pdf
)

echo.
if exist "data\430-stage-reporting_files" "NHSB ISP_완료보고_v1.0.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "NHSB ISP_완료보고_v1.0.pdf"  "Abstract_202405_NHSB_ISP_completion.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_완료보고_v1.0.pdf
)

echo.
if exist "data\430-stage-reporting_files" "SH공사_AXISP_착수보고.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "SH공사_AXISP_착수보고.pdf"  "Abstract_202507_SH_AXISP_kickoff.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH공사_AXISP_착수보고.pdf
)

echo.
if exist "data\430-stage-reporting_files" "SH_AXISP_중간보고_20250915_VF.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "SH_AXISP_중간보고_20250915_VF.pdf"  "Abstract_202507_SH_AXISP_interim.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_중간보고_20250915_VF.pdf
)

echo.
if exist "data\430-stage-reporting_files" "SH_AXISP_임원보고_20250917_v0.81.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "SH_AXISP_임원보고_20250917_v0.81.pdf"  "Abstract_202507_SH_AXISP_progress.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_임원보고_20250917_v0.81.pdf
)

echo.
if exist "data\430-stage-reporting_files" "SH공사_AXISP_착수보고.pdf" (
   python keyextraction.py "data\430-stage-reporting_files" "SH공사_AXISP_착수보고.pdf"  "Abstract_202507_SH_AXISP_kickoff.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH공사_AXISP_착수보고.pdf
)

echo.
if exist "data\440-workshop_files" "NHSB ISP_워크숍_20240419_v1.0.pdf" (
   python keyextraction.py "data\440-workshop_files" "NHSB ISP_워크숍_20240419_v1.0.pdf"  "Abstract_202405_NHSB_ISP_visioningworkshop.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_워크숍_20240419_v1.0.pdf
)

echo.
if exist "data\440-workshop_files" "NHSB ISP_워크숍(BIZ)_20240619_v1.0.pdf" (
   python keyextraction.py "data\440-workshop_files" "NHSB ISP_워크숍(BIZ)_20240619_v1.0.pdf"  "Abstract_202405_NHSB_ISP_implworkshop.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - NHSB ISP_워크숍(BIZ)_20240619_v1.0.pdf
)

echo.
if exist "data\440-workshop_files" "SH_AXISP_워크숍(중간보고)_20250915_VF.pdf" (
   python keyextraction.py "data\440-workshop_files" "SH_AXISP_워크숍(중간보고)_20250915_VF.pdf"  "Abstract_202507_SH_AXISP_visioningworkshop.json"
) else (
    echo 오류: 파일을 찾을 수 없습니다 - SH_AXISP_워크숍(중간보고)_20250915_VF.pdf
)









