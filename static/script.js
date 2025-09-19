// ===================================================================
// 2025-09-19 00:35 KST: 누락된 함수 내용을 모두 복원한 최종 통합 스크립트
// ===================================================================

// 'AX방법론' 트리 UI를 위한 재귀 컴포넌트
const TaskItem = {
  name: 'TaskItem',
  props: ['task', 'selectTask', 'isExpanded', 'selectedTask', 'depth'],
  template: `
    <li class="ax-methodology-item">
      <button class="ax-methodology-item-button" :class="{ 'selected': selectedTask === task.id }" :style="{ paddingLeft: (12 + (depth * 16)) + 'px' }" @click="selectTask(task)">
        <img v-if="task.subTasks && task.subTasks.length > 0" :src="isExpanded(task.id) ? '/static/img/down-arrow.jpg' : '/static/img/right-arrow.jpg'" class="ax-methodology-toggle-icon" alt="toggle">
        <span>{{ task.name }}</span>
      </button>
      <div v-if="task.subTasks && task.subTasks.length > 0" class="ax-methodology-sublist-container" :class="{ 'expanded': isExpanded(task.id) }">
        <ul class="ax-methodology-sublist">
          <task-item v-for="sub in task.subTasks" :key="sub.id" :task="sub" :select-task="selectTask" :is-expanded="isExpanded" :selected-task="selectedTask" :depth="depth + 1" />
        </ul>
      </div>
    </li>
  `
};

const { createApp, ref, reactive, nextTick, watch } = Vue;

const app = createApp({
  components: { 'task-item': TaskItem },
  setup() {
    // --- 1. 상태 변수 정의 ---
    const chatInput = ref('');
    const chatHistory = ref([{ message: '안녕하세요! AX Consulting HUB에 오신 것을 환영합니다. 무엇을 도와드릴까요?', type: 'ai-message' }]);
    const workspaceContent = ref('');
    const agentName = ref('준비 완료');
    const agentDescription = ref('AX Consulting HUB가 준비되었습니다. 질문을 입력해주세요.');
    const sourceInfo = ref([]);
    const llmModelSelect = ref('Gemini');
    const useValidation = ref(false);
    const isLoading = ref(false);
    const activeMenu = ref('ax-methodology');
    const uploadedFiles = reactive([]);
    const showPopup = ref(false);
    const chatInputRef = ref(null);
    const showReferenceMaterials = ref(false);
    const referenceFiles = ref([]);
    const isLoadingReferences = ref(false);
    const leftPanelTitle = ref('AX 방법론');

    const axMethodology = ref([]);
    const selectedTask = ref(null);
    const expandedTasks = reactive({});

    const promptGroups = ref([]);
    const activePromptIndex = ref(null);
    const isLoadingPrompts = ref(false);
    
    const mainTitleMap = {
        'ax-methodology': 'AX 방법론', 'Env_Analysis': '환경분석', 'TechEnv_Analysis': '기술환경분석',
        'Biz_Analysis': 'Biz요건분석', 'AXIT_Analysis': 'AX IT요건분석', 'Visioning': 'AX Visioning', 'Target_Model': 'AX 목표모델',
        'Impl_Tasks': 'AX 이행과제', 'Solutions': '솔루션업체', 'Roadmap': 'AX 로드맵수립',
    };
    const menuIdToFolderMap = {
        'ax-methodology': '901-proposal_files', 'Env_Analysis': '110-Env_files',
        'TechEnv_Analysis': '120-TechEnv_files', 'Biz_Analysis': '130-BizReq_files','AXIT_Analysis': '140-AI_ITReq_files',
        'Visioning': '210-Vision_files', 'Target_Model': '220-TargetModel_files', 'Impl_Tasks': '310-Implementation_files',
        'Solutions': '323-vendor_files', 'Roadmap': '320-roadmap_files',
    };

    // --- 2. 데이터 로드 함수 ---
    const fetchAxMethodology = async () => {
      try {
        const res = await fetch('/api/ax-methodology');
        if (!res.ok) throw new Error('Failed to load AX Methodology');
        axMethodology.value = await res.json();
      } catch (e) { console.error('Failed to load AX Methodology:', e); }
    };

    const fetchPromptGroups = async (menuId) => {
        isLoadingPrompts.value = true;
        promptGroups.value = [];
        activePromptIndex.value = null;
        try {
            const res = await fetch(`/api/prompts/${menuId}`);
            if (!res.ok) throw new Error('Failed to load prompts');
            promptGroups.value = await res.json();
        } catch (e) { console.error(e); } finally { isLoadingPrompts.value = false; }
    };
    
    const fetchReferenceFiles = async (menuId) => {
        const folderName = menuIdToFolderMap[menuId];
        if (!folderName) { referenceFiles.value = []; return; }
        isLoadingReferences.value = true;
        referenceFiles.value = [];
        try {
            const res = await fetch(`/api/reference-materials/${folderName}`);
            if (!res.ok) throw new Error('참고자료를 불러오는 데 실패했습니다.');
            referenceFiles.value = await res.json();
        } catch (e) { console.error(e); } finally { isLoadingReferences.value = false; }
    };
    
    const fetchPromptTemplatesForTask = async (taskId, taskName) => {
        isLoading.value = true;
        workspaceContent.value = '';
        try {
            const res = await fetch(`/api/prompt-templates/${taskId}`);
            if (!res.ok) throw new Error('Failed to load prompt templates for task');
            const templates = await res.json();
            let html = `<div class="p-4"><h3 class="text-xl font-bold mb-4">${taskName}</h3>`;
            if (templates && templates.length > 0) {
                html += `<h4 class="text-lg font-semibold mt-6 mb-4">프롬프트 템플릿</h4><div class="prompt-card-container">`;
                templates.forEach(t => {
                    html += `<div class="prompt-card" data-prompt-template="${t.template}"><h4>${t.title}</h4><p>${t.template}</p></div>`;
                });
                html += `</div>`;
            } else {
                html += `<p class="text-gray-600 mt-4">사용 가능한 프롬프트 템플릿이 없습니다.</p>`;
            }
            workspaceContent.value = html;
            nextTick(() => {
                document.querySelectorAll('.prompt-card').forEach(card => {
                    card.addEventListener('click', e => {
                        chatInput.value = e.currentTarget.dataset.promptTemplate;
                        autoResize();
                        chatInputRef.value.focus();
                    });
                });
            });
        } catch (e) { console.error(e); workspaceContent.value = `<p class="text-red-500 p-4">프롬프트 템플릿 로드 실패</p>`; } 
        finally { isLoading.value = false; }
    };

    // --- 3. 이벤트 핸들러 및 메소드 ---
    const setActiveMenu = async (menuId) => {
      activeMenu.value = menuId;
      leftPanelTitle.value = mainTitleMap[menuId] || 'AX 방법론';
      workspaceContent.value = '';
      sourceInfo.value = [];
      agentName.value = '준비 완료';
      agentDescription.value = `${leftPanelTitle.value} 메뉴가 선택되었습니다.`;
      if (menuId === 'ax-methodology') {
        promptGroups.value = [];
        if (axMethodology.value.length === 0) await fetchAxMethodology();
      } else {
        axMethodology.value = [];
        await fetchPromptGroups(menuIdToFolderMap[menuId]);
      }
      if (showReferenceMaterials.value) {
        await fetchReferenceFiles(menuId);
      }
    };

    const selectTask = async (task) => {
      selectedTask.value = task.id;
      if (!task.subTasks || task.subTasks.length === 0) {
        await fetchPromptTemplatesForTask(task.id, task.name);
      } else {
        expandedTasks[task.id] = !expandedTasks[task.id];
        workspaceContent.value = `<div class="p-4"><h3 class="text-xl font-bold mb-4">${task.name}</h3><p class="text-gray-700 leading-relaxed">${task.description}</p></div>`;
        sourceInfo.value = [];
      }
    };
    const isExpanded = (taskId) => !!expandedTasks[taskId];

    const togglePrompt = (index) => { activePromptIndex.value = activePromptIndex.value === index ? null : index; };
    const highlightEditable = (template) => { return (template || '').replace(/##\s*([^:\n]+)(?::\s*([^\n]+))?/g, '<span class="highlight-editable">$1: $2</span>'); };
    const sendPromptFromPanel = () => {
        const contentDiv = document.querySelector('.prompt-template-content[contenteditable="true"]');
        if (contentDiv) {
            chatInput.value = contentDiv.innerText;
            sendMessage();
        }
    };
    
    const displayReferenceContent = (file) => {
        workspaceContent.value = `<div class="p-4"><h3 class="text-xl font-bold mb-4">${file.original_file_name}</h3><div class="prose max-w-none mt-2">${file.summary_html}</div></div>`;
    };

    const sendMessage = async () => {
      const prompt = chatInput.value.trim();
      if (!prompt && uploadedFiles.length === 0) return;
      chatInput.value = ''; autoResize(); isLoading.value = true;
      workspaceContent.value = ''; agentName.value = 'AI 에이전트';
      agentDescription.value = '응답을 생성 중입니다...';
      try {
        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('llm_model_choice', llmModelSelect.value);
        formData.append('use_validation', useValidation.value);
        const historyForApi = chatHistory.value.map(m => ({
          role: m.type === 'user-message' ? 'user' : 'assistant',
          parts: [{ text: m.message }]
        }));
        formData.append('chat_history', JSON.stringify(historyForApi));
        uploadedFiles.forEach(file => { formData.append('files', file); });
        const res = await fetch('/api/chat', { method: 'POST', body: formData });
        uploadedFiles.splice(0, uploadedFiles.length);
        const result = await res.json();
        if (result.error) throw new Error(result.error);
        agentName.value = result.agent_name;
        agentDescription.value = result.agent_description;
        workspaceContent.value = result.response_content;
        sourceInfo.value = result.source_info;
      } catch (e) {
        workspaceContent.value = `<p class="text-red-500 p-4">오류: ${e.message}</p>`;
        agentName.value = '오류 발생';
      } finally { isLoading.value = false; }
    };
    
    const autoResize = () => {
      const el = chatInputRef.value; if (!el) return;
      el.style.height = 'auto';
      const styles = window.getComputedStyle(el);
      const maxH = parseInt(styles.maxHeight || '320', 10);
      const needed = el.scrollHeight + 4;
      el.style.height = Math.min(needed, maxH) + 'px';
      el.style.overflowY = needed > maxH ? 'auto' : 'hidden';
    };
    const handleInput = () => autoResize();
    window.addEventListener('resize', autoResize);

    const handleFileUpload = (event) => { uploadedFiles.push(...event.target.files); event.target.value = ''; };
    const showFilePopup = () => { showPopup.value = true; };
    const hideFilePopup = () => { showPopup.value = false; };
    const removeFile = (idx) => { uploadedFiles.splice(idx, 1); };
    
    watch(showReferenceMaterials, (newValue) => {
        if (newValue) { fetchReferenceFiles(activeMenu.value); } 
        else { referenceFiles.value = []; }
    });

//-----------------------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {
    const mainMenuContainer = document.getElementById('main-menu-container');
    const workPanel = document.getElementById('work-panel');
    const chatPanel = document.getElementById('chat-panel');
    const sourcePanel = document.getElementById('source-panel');

    // ax_methodology_tasks.json에서 과업 데이터를 불러와 메인 메뉴를 생성합니다.
    fetch('/ax_methodology_tasks.json')
        .then(response => response.json())
        .then(data => {
            createMainMenu(data.tasks);
        });

    /**
     * 메인 메뉴 UI를 생성합니다.
     * @param {Array} tasks - ax_methodology_tasks.json에서 불러온 과업 배열
     */
    function createMainMenu(tasks) {
        tasks.forEach(task => {
            const menuItem = document.createElement('div');
            menuItem.className = 'main-menu-item';
            menuItem.textContent = task.name;
            menuItem.dataset.taskId = task.id;

            menuItem.addEventListener('click', () => {
                // 이전에 선택된 메뉴의 'active' 클래스를 제거합니다.
                document.querySelectorAll('.main-menu-item').forEach(item => {
                    item.classList.remove('active');
                });
                // 현재 클릭된 메뉴에 'active' 클래스를 추가합니다.
                menuItem.classList.add('active');

                // 메뉴 유형에 따라 다른 동작을 수행합니다.
                if (task.id === "0") { // "AX방법론" 메뉴
                    displayMethodologyInfo(task);
                } else { // 다른 모든 컨설팅 단계 메뉴
                    displaySubTasks(task);
                }
            });
            mainMenuContainer.appendChild(menuItem);
        });
    }

    /**
     * "AX방법론" 메뉴의 정보를 work-panel에 표시합니다.
     * @param {object} task - 선택된 메뉴의 과업 객체
     */
    function displayMethodologyInfo(task) {
        workPanel.innerHTML = `
            <h2>${task.name}</h2>
            <p>${task.description}</p>
        `;
        // AX 방법론 선택 시 채팅 및 소스 패널 초기화
        chatPanel.innerHTML = '';
        sourcePanel.innerHTML = '';
    }

    /**
     * 컨설팅 단계별 하위 과업 버튼들을 work-panel에 표시합니다.
     * @param {object} task - 선택된 메뉴의 과업 객체
     */
    function displaySubTasks(task) {
        workPanel.innerHTML = `<h2>${task.name}</h2>`;
        chatPanel.innerHTML = ''; // 새 메뉴 선택 시 채팅 패널 초기화
        sourcePanel.innerHTML = ''; // 새 메뉴 선택 시 소스 패널 초기화

        const subTaskButtonsContainer = document.createElement('div');
        subTaskButtonsContainer.className = 'sub-task-buttons-container';

        task.sub_tasks.forEach(subTask => {
            const button = document.createElement('button');
            button.className = 'sub-task-button';
            button.textContent = subTask.name;
            // 각 버튼에 고유한 sub_task id를 데이터로 저장합니다.
            button.dataset.taskId = subTask.id; 
            subTaskButtonsContainer.appendChild(button);
        });

        const promptContainer = document.createElement('div');
        promptContainer.id = 'prompt-container';

        workPanel.appendChild(subTaskButtonsContainer);
        workPanel.appendChild(promptContainer);

        // 이벤트 위임을 사용하여 하위 과업 버튼 클릭을 처리합니다.
        subTaskButtonsContainer.addEventListener('click', (event) => {
            if (event.target.classList.contains('sub-task-button')) {
                // 모든 버튼의 'active' 상태를 제거합니다.
                subTaskButtonsContainer.querySelectorAll('.sub-task-button').forEach(btn => {
                    btn.classList.remove('active');
                });
                // 현재 클릭된 버튼을 'active' 상태로 만듭니다.
                event.target.classList.add('active');
                
                // 버튼에 저장된 task id를 기반으로 프롬프트 파일 경로를 생성합니다.
                const taskId = event.target.dataset.taskId;
                const promptFile = `data/${taskId}_prompt.json`; 
                
                loadPromptTemplate(promptFile, taskId, promptContainer);
            }
        });
    }

    /**
     * 백엔드에서 프롬프트 템플릿을 불러와 UI에 표시합니다.
     * @param {string} promptFile - 불러올 프롬프트 파일 경로
     * @param {string} taskId - 현재 과업 ID
     * @param {HTMLElement} container - 프롬프트 UI를 표시할 컨테이너 요소
     */
    async function loadPromptTemplate(promptFile, taskId, container) {
        try {
            const response = await fetch('/api/get_prompt_template', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: promptFile })
            });
            if (!response.ok) {
                // 404 Not Found 에러가 발생하면 사용자에게 명확한 메시지를 보여줍니다.
                if (response.status === 404) {
                     container.innerHTML = `<p class="error">해당 과업의 프롬프트 파일(${promptFile})을 찾을 수 없습니다.</p>`;
                     return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const prompts = await response.json();
            displayPromptUI(prompts, taskId, container);
        } catch (error) {
            console.error("Error loading prompt template:", error);
            container.innerHTML = `<p class="error">프롬프트 템플릿을 불러오는 데 실패했습니다.</p>`;
        }
    }

    /**
     * 프롬프트 선택 및 편집 UI를 생성합니다.
     * @param {Array|object} prompts - 불러온 프롬프트 템플릿 데이터
     * @param {string} taskId - 현재 과업 ID
     * @param {HTMLElement} container - 프롬프트 UI를 표시할 컨테이너 요소
     */
    function displayPromptUI(prompts, taskId, container) {
        container.innerHTML = ''; // 이전 내용을 초기화합니다.
        const promptData = Array.isArray(prompts) ? prompts : [prompts];

        const promptWrapper = document.createElement('div');
        promptWrapper.className = 'prompt-wrapper';

        // 프롬프트가 여러 개일 경우 선택 UI를 생성합니다.
        if (promptData.length > 1) {
            const selectLabel = document.createElement('label');
            selectLabel.for = 'prompt-selector';
            selectLabel.textContent = '프롬프트 템플릿 선택: ';

            const select = document.createElement('select');
            select.id = 'prompt-selector';
            promptData.forEach((prompt, index) => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = prompt.name || `템플릿 ${index + 1}`;
                select.appendChild(option);
            });
            
            const selectorWrapper = document.createElement('div');
            selectorWrapper.className = 'prompt-selector-wrapper';
            selectorWrapper.appendChild(selectLabel);
            selectorWrapper.appendChild(select);
            promptWrapper.appendChild(selectorWrapper);

            select.addEventListener('change', (event) => {
                const selectedPrompt = promptData[event.target.value];
                updatePromptContent(selectedPrompt, taskId, promptWrapper);
            });
            // 기본으로 첫 번째 프롬프트를 표시합니다.
             updatePromptContent(promptData[0], taskId, promptWrapper);
        } else {
            // 프롬프트가 하나일 경우 바로 표시합니다.
             updatePromptContent(promptData[0], taskId, promptWrapper);
        }
        
        container.appendChild(promptWrapper);
    }
    
    /**
     * 프롬프트 내용(textarea, 전송 버튼)을 업데이트하거나 생성합니다.
     * @param {object} prompt - 표시할 프롬프트 객체
     * @param {string} taskId - 현재 과업 ID
     * @param {HTMLElement} wrapper - 프롬프트 UI를 감싸는 요소
     */
    function updatePromptContent(prompt, taskId, wrapper) {
        // 기존의 content-area가 있다면 삭제합니다.
        let contentArea = wrapper.querySelector('.prompt-content-area');
        if (contentArea) {
            contentArea.remove();
        }

        // 새로운 content-area를 생성합니다.
        contentArea = document.createElement('div');
        contentArea.className = 'prompt-content-area';

        const textarea = document.createElement('textarea');
        textarea.id = 'prompt-textarea';
        textarea.value = prompt.prompt;

        const executeButton = document.createElement('button');
        executeButton.id = 'execute-prompt-button';
        executeButton.textContent = '전송';
        
        executeButton.addEventListener('click', () => {
             const userPrompt = textarea.value;
             executeTask(taskId, userPrompt);
        });

        contentArea.appendChild(textarea);
        contentArea.appendChild(executeButton);
        wrapper.appendChild(contentArea);
    }


    /**
     * 과업을 실행하고 결과를 각 패널에 표시합니다.
     * @param {string} taskId - 실행할 과업의 ID
     * @param {string} [promptOverride] - 사용자가 수정한 프롬프트 내용
     */
    async function executeTask(taskId, promptOverride = null) {
        chatPanel.innerHTML = '<div class="loader">작업을 처리 중입니다...</div>';
        sourcePanel.innerHTML = '';
        
        try {
            const payload = {
                task_id: taskId,
                prompt: promptOverride
            };

            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const result = await response.json();

            // 채팅 패널 업데이트
            chatPanel.innerHTML = `
                <div class="message user-message">
                    <p><strong>You:</strong> ${result.user_prompt}</p>
                </div>
                <div class="message bot-message">
                    <p><strong>AI:</strong> ${result.response}</p>
                </div>
            `;
            
            // 소스 패널 업데이트 (소스가 있는 경우)
            if (result.sources && result.sources.length > 0) {
                 sourcePanel.innerHTML = `<h3>참조 자료</h3>`;
                 const sourceList = document.createElement('ul');
                 result.sources.forEach(source => {
                     const item = document.createElement('li');
                     item.textContent = source;
                     sourceList.appendChild(item);
                 });
                 sourcePanel.appendChild(sourceList);
            }

        } catch (error) {
            console.error('Error executing task:', error);
            chatPanel.innerHTML = `<p class="error">작업 실행 중 오류가 발생했습니다: ${error.message}</p>`;
        }
    }
});

//-----------------------------------------------------------------------------------------

    // --- 4. 초기화 ---
    fetchAxMethodology();

    return {
      chatInput, chatHistory, workspaceContent, agentName, agentDescription, sourceInfo, llmModelSelect,
      useValidation, isLoading, activeMenu, uploadedFiles, showPopup, chatInputRef, showReferenceMaterials,
      referenceFiles, isLoadingReferences, leftPanelTitle, axMethodology, selectedTask, expandedTasks,
      promptGroups, activePromptIndex, isLoadingPrompts,
      
      sendMessage, handleInput, handleFileUpload, showFilePopup, hideFilePopup, removeFile, setActiveMenu,
      selectTask, isExpanded, displayReferenceContent, togglePrompt, highlightEditable, sendPromptFromPanel
    };
  }
});

app.config.errorHandler = (err, instance, info) => { console.error('Vue error:', err, info); };
app.mount('#app');
