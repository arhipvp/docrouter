import { refreshFiles, openMetadataModal, openModal, closeModal } from './files.js';
import { refreshFolderTree } from './folders.js';
import { openChatModal } from './chat.js';
import type { FileInfo, ChatHistory, UploadResponse, FileStatus } from './types.js';

export let aiExchange: HTMLElement;
let metadataModal: HTMLElement;
let editForm: HTMLFormElement;
let previewDialog: HTMLElement;
let textPreview: HTMLTextAreaElement;
let buttonsWrap: HTMLElement;
let regenerateBtn: HTMLButtonElement;
let editBtn: HTMLButtonElement;
let finalizeBtn: HTMLButtonElement;
let askAiBtn: HTMLButtonElement;
let currentId: string | null = null;
let currentFile: FileInfo | null = null;
let inputs: NodeListOf<HTMLInputElement | HTMLTextAreaElement>;
let stepIndicator: HTMLElement;
let finalizeModal: HTMLElement;
let finalizeConfirm: HTMLButtonElement;
let finalizeCancel: HTMLButtonElement;
let currentStep = 1;
const fieldMap: Record<string, string> = {
  'edit-category': 'category',
  'edit-subcategory': 'subcategory',
  'edit-issuer': 'issuer',
  'edit-date': 'date',
  'edit-name': 'suggested_name',
  'edit-description': 'description',
  'edit-summary': 'summary',
};

function updateStep(step: number) {
  currentStep = step;
  if (!stepIndicator) return;
  const steps = stepIndicator.querySelectorAll<HTMLElement>('.step');
  steps.forEach((el) => {
    const s = Number(el.dataset.step || '0');
    el.classList.toggle('active', s === step);
    el.classList.toggle('completed', s < step);
  });
}

export function renderDialog(
  container: HTMLElement,
  prompt?: string,
  response?: string,
  history?: ChatHistory[],
  reviewComment?: string,
  createdPath?: string
) {
  container.innerHTML = '';
  if (history && history.length) {
    history.forEach((msg) => {
      const div = document.createElement('div');
      div.className = `ai-message ${msg.role === 'user' ? 'user' : 'assistant'}`;
      div.textContent = msg.message;
      container.appendChild(div);
    });
    if (reviewComment) {
      const commentDiv = document.createElement('div');
      commentDiv.className = 'ai-message reviewer';
      commentDiv.textContent = reviewComment;
      container.appendChild(commentDiv);
    }
    if (createdPath) {
      const pathDiv = document.createElement('div');
      pathDiv.className = 'ai-message system';
      pathDiv.textContent = createdPath;
      container.appendChild(pathDiv);
    }
    return;
  }
  if (prompt) {
    const userDiv = document.createElement('div');
    userDiv.className = 'ai-message user';
    userDiv.textContent = prompt;
    container.appendChild(userDiv);
  }
  if (response) {
    const aiDiv = document.createElement('div');
    aiDiv.className = 'ai-message assistant';
    aiDiv.textContent = response;
    container.appendChild(aiDiv);
  }
  if (reviewComment) {
    const commentDiv = document.createElement('div');
    commentDiv.className = 'ai-message reviewer';
    commentDiv.textContent = reviewComment;
    container.appendChild(commentDiv);
  }
  if (createdPath) {
    const pathDiv = document.createElement('div');
    pathDiv.className = 'ai-message system';
    pathDiv.textContent = createdPath;
    container.appendChild(pathDiv);
  }
}

export function setupUploadForm() {
  const form = document.querySelector('form') as HTMLFormElement;
  const progress = document.getElementById('upload-progress') as HTMLProgressElement;
  aiExchange = document.getElementById('ai-exchange')!;
  const container =
    (document.querySelector('.app__container') || document.querySelector('.container')) as HTMLElement;
  if (container) {
    stepIndicator = document.createElement('div');
    stepIndicator.className = 'step-indicator';
    ['Выбор файлов', 'Предпросмотр', 'Финализация'].forEach((t, i) => {
      const el = document.createElement('div');
      el.className = 'step';
      el.dataset.step = String(i + 1);
      el.textContent = `${i + 1}. ${t}`;
      stepIndicator.appendChild(el);
    });
    container.insertBefore(stepIndicator, form);
    updateStep(1);
  }
  const missingModal = document.getElementById('missing-modal')!;
  const missingList = document.getElementById('missing-list')!;
  const missingConfirm = document.getElementById('missing-confirm')!;
  const missingCancel = document.getElementById('missing-cancel')!;
  const missingDialog = document.getElementById('missing-dialog')!;
  const suggestedPath = document.getElementById('suggested-path')!;
  metadataModal = document.getElementById('metadata-modal')!;
  editForm = document.getElementById('edit-form') as HTMLFormElement;
  finalizeModal = document.createElement('div');
  finalizeModal.id = 'finalize-modal';
  finalizeModal.className = 'modal confirm-modal';
  finalizeModal.innerHTML = `
    <div class="modal__content">
      <p>Финализировать документ?</p>
      <div class="modal__buttons">
        <button id="finalize-confirm">Да</button>
        <button id="finalize-cancel" type="button">Отмена</button>
      </div>
    </div>`;
  (document.body || container)?.appendChild(finalizeModal);
  finalizeConfirm = finalizeModal.querySelector('#finalize-confirm') as HTMLButtonElement;
  finalizeCancel = finalizeModal.querySelector('#finalize-cancel') as HTMLButtonElement;
  finalizeCancel.addEventListener('click', () => closeModal(finalizeModal));
  const modalContent = metadataModal.querySelector('.modal__content')!;
  previewDialog = document.createElement('div');
  previewDialog.className = 'ai-dialog';
  previewDialog.style.display = 'none';
  modalContent.insertBefore(previewDialog, editForm);
  textPreview = document.createElement('textarea');
  textPreview.readOnly = true;
  textPreview.style.display = 'none';
  modalContent.insertBefore(textPreview, editForm);
  buttonsWrap = document.createElement('div');
  buttonsWrap.className = 'modal__buttons';
  buttonsWrap.style.display = 'none';
  modalContent.appendChild(buttonsWrap);
  askAiBtn = document.createElement('button');
  askAiBtn.type = 'button';
  askAiBtn.textContent = 'Спросить ИИ';
  buttonsWrap.appendChild(askAiBtn);
  regenerateBtn = document.createElement('button');
  regenerateBtn.type = 'button';
  regenerateBtn.textContent = 'Перегенерировать';
  buttonsWrap.appendChild(regenerateBtn);
  editBtn = document.createElement('button');
  editBtn.type = 'button';
  editBtn.textContent = 'Редактировать';
  buttonsWrap.appendChild(editBtn);
  finalizeBtn = document.createElement('button');
  finalizeBtn.type = 'button';
  finalizeBtn.textContent = 'Финализировать';
  buttonsWrap.appendChild(finalizeBtn);
  inputs = editForm.querySelectorAll('input, textarea');

  const saveBtn = editForm.querySelector('button[type="submit"]') as HTMLButtonElement;
  const hidePreview = () => {
    previewDialog.style.display = 'none';
    textPreview.style.display = 'none';
    buttonsWrap.style.display = 'none';
    saveBtn.style.display = '';
    inputs.forEach((el) => (el.disabled = false));
    currentId = null;
    currentFile = null;
  };
  const metadataClose = metadataModal.querySelector('.modal__close') as HTMLElement;
  metadataClose.addEventListener('click', () => {
    hidePreview();
    updateStep(1);
  });

  regenerateBtn.addEventListener('click', async () => {
    if (!currentId) return;
    try {
      const resp = await fetch(`/files/${currentId}/regenerate`, {
        method: 'POST',
      });
      if (!resp.ok) throw new Error();
      const data: FileInfo = await resp.json();
      openPreviewModal(data);
    } catch {
      alert('Ошибка генерации');
    }
  });

  editBtn.addEventListener('click', () => {
    const disabled = inputs[0]?.disabled;
    inputs.forEach((el) => {
      if (!(el.id === 'edit-summary')) el.disabled = !disabled;
    });
  });

  finalizeBtn.addEventListener('click', () => {
    if (!currentId) return;
    openModal(finalizeModal);
  });

  finalizeConfirm.addEventListener('click', async () => {
    if (!currentId) return;
    const meta: Record<string, string> = {};
    inputs.forEach((el) => {
      const key = fieldMap[el.id];
      if (!key || key === 'summary') return;
      const v = el.value.trim();
      if (v) meta[key] = v;
    });
    try {
      const resp = await fetch(`/files/${currentId}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metadata: meta, confirm: true }),
      });
      if (!resp.ok) throw new Error();
      closeModal(finalizeModal);
      closeModal(metadataModal);
      hidePreview();
      form.reset();
      progress.value = 0;
      refreshFiles();
      refreshFolderTree();
      updateStep(3);
      setTimeout(() => updateStep(1), 500);
    } catch {
      alert('Ошибка финализации');
    }
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const fileInput = form.querySelector('input[type="file"]') as HTMLInputElement;
    const file = fileInput?.files?.[0];
    if (!file || !file.name) {
      alert('Файл должен иметь имя');
      return;
    }
    const data = new FormData(form);
    progress.value = 0;
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.upload.addEventListener('progress', (ev) => {
      if (ev.lengthComputable) {
        progress.max = ev.total;
        progress.value = ev.loaded;
      }
    });
    xhr.onload = () => {
      if (xhr.status === 200) {
        const result: UploadResponse = JSON.parse(xhr.responseText);
        if (result.status === 'pending') {
          suggestedPath.textContent = result.suggested_path || '';
          missingList.innerHTML = '';
          (result.missing || []).forEach((path: string) => {
            const li = document.createElement('li');
            li.textContent = path;
            missingList.appendChild(li);
          });
          renderDialog(
            missingDialog,
            result.prompt,
            result.raw_response,
            result.chat_history,
            result.review_comment,
            result.created_path
          );
          missingModal.style.display = 'flex';
          updateStep(2);
          missingConfirm.onclick = async () => {
            try {
              const resp = await fetch(`/files/${result.id}/finalize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ missing: result.missing || [], confirm: true }),
              });
              if (!resp.ok) throw new Error();
              const finalData: FileInfo = await resp.json();
              missingModal.style.display = 'none';
              openPreviewModal(finalData);
            } catch {
              alert('Ошибка обработки');
            }
          };
          missingCancel.onclick = async () => {
            try {
              await fetch(`/files/${result.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'rejected' as FileStatus }),
              });
            } catch {
              // ignore errors, просто закрываем модалку
            }
            missingModal.style.display = 'none';
            refreshFiles();
            updateStep(1);
          };
        } else {
          openPreviewModal(result as FileInfo);
        }
      } else {
        alert('Ошибка загрузки');
      }
    };
    xhr.send(data);
  });
  askAiBtn.addEventListener('click', () => {
    if (!currentId) return;
    openChatModal(currentId, currentFile?.chat_history);
  });

  document.addEventListener('chat-updated', (ev) => {
    const detail = (ev as CustomEvent<{ id: string; history: ChatHistory[] }>).detail;
    if (detail?.id === currentId && currentFile) {
      currentFile.chat_history = detail.history;
      const last = detail.history[detail.history.length - 1];
      if (last?.role === 'assistant') {
        try {
          const suggested = JSON.parse(last.message);
          inputs.forEach((el) => {
            const key = fieldMap[el.id];
            if (key && suggested[key]) {
              el.value = suggested[key];
              currentFile!.metadata = currentFile!.metadata || {};
              (currentFile!.metadata as any)[key] = suggested[key];
            }
          });
        } catch {
          // ответ не содержит JSON с метаданными
        }
      }
      renderDialog(
        previewDialog,
        undefined,
        undefined,
        detail.history,
        currentFile.review_comment,
        currentFile.created_path
      );
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && missingModal.style.display === 'flex') {
      missingModal.style.display = 'none';
      updateStep(1);
    }
  });
}

function openPreviewModal(result: FileInfo) {
  currentFile = result;
  currentId = result.id;
  openMetadataModal(result);
  previewDialog.style.display = 'block';
  textPreview.style.display = 'block';
  buttonsWrap.style.display = 'flex';
  updateStep(2);
  renderDialog(
    previewDialog,
    result.prompt,
    result.raw_response,
    result.chat_history,
    result.review_comment,
    result.created_path
  );
  textPreview.value = result.metadata?.extracted_text || '';
  const saveBtn = editForm.querySelector('button[type="submit"]') as HTMLButtonElement;
  saveBtn.style.display = 'none';
  inputs.forEach((el) => (el.disabled = true));
}
