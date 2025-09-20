// static/script.js
// 2025-01-16 15:30 KST: 3단 레이아웃 구조에 맞춘 전면 개편
// 2025-01-17 11:00 KST: UI/UX 개선 - 자유 프롬프트 지원, 메뉴별 동작 통일
// 2025-01-17 12:00 KST: AX방법론 메뉴에서 프롬프트 입력창 제거
// 2025-01-17 15:00 KST: 프롬프트 전송 후 유지 및 명시적 지우기 버튼 추가

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
    // 2025-01-16 16:00 KST: 상태 변수 정의
    const chatInput = ref('');
    const workspaceContent = ref('');
    const agentName = ref('준비 완료');
    const agentDescription = ref('AX Consulting HUB가 준비되었습니다.');
    const sourceInfo = ref([]);
    const llmModelSelect = ref('Gemini');
    const useValidation = ref(false);
    const isLoading = ref(false);
    const activeMenu = ref('ax-methodology');
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
      'ax-methodology': 'AX 방법론',
      'Env_Analysis': '환경분석',
      'TechEnv_Analysis': '기술환경분석',
      'Biz_Analysis': 'Biz요건분석',
      'AXIT_Analysis': 'IT요건분석',
      'Visioning': 'Visioning',
      'Target_Model': '목표모델',
      'Impl_Tasks': '이행과제',
      'Solutions': '솔루션업체',
      'Roadmap': '로드맵수립'
    };

    const menuIdToFolderMap = {
      'ax-methodology': '901-proposal_files',
      'Env_Analysis': '110-Env_files',
      'TechEnv_Analysis': '120-TechEnv_files',
      'Biz_Analysis': '130-BizReq_files',
      'AXIT_Analysis': '140-AI_ITReq_files',
      'Visioning': '210-Vision_files',
      'Target_Model': '220-TargetModel_files',
      'Impl_Tasks': '310-Implementation_files',
      'Solutions': '323-vendor_files',
      'Roadmap': '320-roadmap_files'
    };

    // 2025-01-16 16:30 KST: 데이터 로드 함수들
    const fetchAxMethodology = async () => {
      try {
        const res = await fetch('/api/ax-methodology');
        if (!res.ok) throw new Error('Failed to load AX Methodology');
        axMethodology.value = await res.json();
      } catch (e) {
        console.error('Failed to load AX Methodology:', e);
      }
    };

    const fetchPromptGroups = async (menuId) => {
      isLoadingPrompts.value = true;
      promptGroups.value = [];
      activePromptIndex.value = null;
      
      try {
        const res = await fetch(`/static/prompts/${menuId}.json`);
        if (!res.ok) throw new Error('Failed to load prompts');
        
        const templates = await res.json();
        promptGroups.value = templates.map(t => ({
          title: t.title,
          template: t.template
        }));
      } catch (e) {
        console.error('Failed to load prompt templates:', e);
      } finally {
        isLoadingPrompts.value = false;
      }
    };

    const fetchReferenceFiles = async (menuId) => {
      const folderName = menuIdToFolderMap[menuId];
      if (!folderName) {
        referenceFiles.value = [];
        return;
      }

      isLoadingReferences.value = true;
      referenceFiles.value = [];

      try {
        const res = await fetch(`/api/reference-materials/${folderName}`);
        if (!res.ok) throw new Error('참고자료를 불러오는 데 실패했습니다.');
        referenceFiles.value = await res.json();
      } catch (e) {
        console.error('Failed to load reference materials:', e);
      } finally {
        isLoadingReferences.value = false;
      }
    };

    const fetchPromptTemplatesForTask = async (taskId, taskName) => {
      isLoading.value = true;
      workspaceContent.value = '';

      try {
        const res = await fetch(`/api/prompt-templates/${taskId}`);
        if (!res.ok) throw new Error('Failed to load prompt templates');
        
        const templates = await res.json();
        let html = `<div class="p-4"><h3 class="text-xl font-bold mb-4">${taskName}</h3>`;
        
        if (templates && templates.length > 0) {
          html += `<h4 class="text-lg font-semibold mt-6 mb-4">프롬프트 템플릿</h4><div class="prompt-card-container">`;
          templates.forEach(t => {
            html += `<div class="prompt-card" data-prompt-template="${t.template}">
              <h4>${t.title}</h4>
              <p>${t.template}</p>
            </div>`;
          });
          html += `</div>`;
        } else {
          html += `<p class="text-gray-600 mt-4">사용 가능한 프롬프트 템플릿이 없습니다.</p>`;
        }

        workspaceContent.value = html;

        nextTick(() => {
          document.querySelectorAll('.prompt-card').forEach(card => {
            card.addEventListener('click', (e) => {
              if (activeMenu.value === 'ax-methodology') {
                alert('AX방법론에서는 템플릿을 클릭하여 직접 사용하실 수 있습니다.\n다른 메뉴에서 프롬프트를 입력해주세요.');
                return;
              }
              chatInput.value = e.currentTarget.dataset.promptTemplate;
              chatInputRef.value?.focus();
            });
          });
        });
      } catch (e) {
        console.error('Failed to load prompt templates:', e);
        workspaceContent.value = `<p class="text-red-500 p-4">프롬프트 템플릿 로드 실패</p>`;
      } finally {
        isLoading.value = false;
      }
    };

    // 2025-01-16 17:00 KST: 이벤트 핸들러들
    // 2025-01-17 15:00 KST: 메뉴 변경시 프롬프트 유지하도록 수정
    const setActiveMenu = async (menuId) => {
      activeMenu.value = menuId;
      leftPanelTitle.value = mainTitleMap[menuId] || 'AX 방법론';
      workspaceContent.value = '';
      sourceInfo.value = [];
      // chatInput.value = ''; // 2025-01-17 15:00 KST: 제거

      if (menuId === 'ax-methodology') {
        promptGroups.value = [];
        activePromptIndex.value = null;
        if (axMethodology.value.length === 0) {
          await fetchAxMethodology();
        }
      } else {
        selectedTask.value = null;
        await fetchPromptGroups(menuId);
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
        workspaceContent.value = `<div class="p-4">
          <h3 class="text-xl font-bold mb-4">${task.name}</h3>
          <p class="text-gray-700 leading-relaxed">${task.description}</p>
        </div>`;
        sourceInfo.value = [];
      }
    };

    const isExpanded = (taskId) => !!expandedTasks[taskId];

    const selectPromptGroup = (index) => {
      if (activePromptIndex.value === index) {
        activePromptIndex.value = null;
        chatInput.value = '';
      } else {
        activePromptIndex.value = index;
        if (promptGroups.value[index]) {
          chatInput.value = promptGroups.value[index].template;
          nextTick(() => {
            chatInputRef.value?.focus();
            if (chatInputRef.value) {
              chatInputRef.value.scrollTop = 0;
            }
          });
        }
      }
    };

    const displayReferenceContent = (file) => {
      workspaceContent.value = `<div class="p-4">
        <h3 class="text-xl font-bold mb-4">${file.original_file_name}</h3>
        <div class="prose max-w-none mt-2">${file.summary_html}</div>
      </div>`;
    };

    // 2025-01-17 15:00 KST: 프롬프트 전송 후 자동 지우기 제거
    const sendMessage = async () => {
      const prompt = chatInput.value.trim();
      if (!prompt) return;

      const originalPrompt = chatInput.value;
      // chatInput.value = ''; // 2025-01-17 15:00 KST: 제거
      isLoading.value = true;
      workspaceContent.value = '';

      try {
        const formData = new FormData();
        formData.append('prompt', originalPrompt);
        formData.append('llm_model_choice', llmModelSelect.value);
        formData.append('use_validation', useValidation.value);
        formData.append('chat_history', JSON.stringify([]));

        const res = await fetch('/api/chat', { method: 'POST', body: formData });
        const result = await res.json();
        
        if (result.error) throw new Error(result.error);

        agentName.value = result.agent_name;
        agentDescription.value = result.agent_description;
        workspaceContent.value = result.response_content;
        sourceInfo.value = result.source_info || [];
      } catch (e) {
        workspaceContent.value = `<p class="text-red-500 p-4">오류: ${e.message}</p>`;
        agentName.value = '오류 발생';
      } finally {
        isLoading.value = false;
      }
    };

    // 2025-01-17 15:00 KST: 새로 추가 - 명시적 프롬프트 지우기 함수
    const clearInput = () => {
      chatInput.value = '';
      activePromptIndex.value = null;
      nextTick(() => {
        chatInputRef.value?.focus();
      });
    };

    const handleInput = () => {
      // 필요시 추가 기능 구현
    };

    watch(showReferenceMaterials, (newValue) => {
      if (newValue) {
        fetchReferenceFiles(activeMenu.value);
      } else {
        referenceFiles.value = [];
      }
    });

    // 초기화
    fetchAxMethodology();

    return {
      chatInput, workspaceContent, agentName, agentDescription, sourceInfo,
      llmModelSelect, useValidation, isLoading, activeMenu,
      chatInputRef, showReferenceMaterials, referenceFiles,
      isLoadingReferences, leftPanelTitle, axMethodology, selectedTask,
      expandedTasks, promptGroups, activePromptIndex, isLoadingPrompts,
      
      sendMessage, handleInput, setActiveMenu, selectTask, isExpanded,
      displayReferenceContent, selectPromptGroup, clearInput // 2025-01-17 15:00 KST: 추가
    };
  }
});

app.config.errorHandler = (err, instance, info) => {
  console.error('Vue error:', err, info);
};

app.mount('#app');
