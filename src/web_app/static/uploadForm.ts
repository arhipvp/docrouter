import { refreshFiles, openMetadataModal, closeModal } from './files.js';
import { refreshFolderTree } from './folders.js';
import type { FileInfo } from './types.js';

export let aiExchange: HTMLElement;
let metadataModal: HTMLElement;
let editForm: HTMLFormElement;
let previewDialog: HTMLElement;
let textPreview: HTMLTextAreaElement;
let buttonsWrap: HTMLElement;
let regenerateBtn: HTMLButtonElement;
let editBtn: HTMLButtonElement;
let finalizeBtn: HTMLButtonElement;
let currentId: string | null = null;
let inputs: NodeListOf<HTMLInputElement | HTMLTextAreaElement>;
const fieldMap: Record<string, string> = {
  'edit-category': 'category',
  'edit-subcategory': 'subcategory',
  'edit-issuer': 'issuer',
  'edit-date': 'date',
  'edit-name': 'suggested_name',
  'edit-description': 'description',
  'edit-summary': 'summary',
};

export function renderDialog(
  container: HTMLElement,
  prompt?: string,
  response?: string
) {
  container.innerHTML = '';
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
}

export function setupUploadForm() {
  const form = document.querySelector('form') as HTMLFormElement;
  const progress = document.getElementById('upload-progress') as HTMLProgressElement;
  aiExchange = document.getElementById('ai-exchange')!;
  const missingModal = document.getElementById('missing-modal')!;
  const missingList = document.getElementById('missing-list')!;
  const missingConfirm = document.getElementById('missing-confirm')!;
  const missingCancel = document.getElementById('missing-cancel')!;
  const missingDialog = document.getElementById('missing-dialog')!;
  const suggestedPath = document.getElementById('suggested-path')!;
  metadataModal = document.getElementById('metadata-modal')!;
  editForm = document.getElementById('edit-form') as HTMLFormElement;
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
  };
  const metadataClose = metadataModal.querySelector('.modal__close') as HTMLElement;
  metadataClose.addEventListener('click', hidePreview);

  regenerateBtn.addEventListener('click', async () => {
    if (!currentId) return;
    try {
      const resp = await fetch(`/files/${currentId}/regenerate`, {
        method: 'POST',
      });
      if (!resp.ok) throw new Error();
      const data = await resp.json();
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

  finalizeBtn.addEventListener('click', async () => {
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
      closeModal(metadataModal);
      hidePreview();
      form.reset();
      progress.value = 0;
      refreshFiles();
      refreshFolderTree();
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
        const result = JSON.parse(xhr.responseText);
        if (result.status === 'pending') {
          suggestedPath.textContent = result.suggested_path || '';
          missingList.innerHTML = '';
          (result.missing || []).forEach((path: string) => {
            const li = document.createElement('li');
            li.textContent = path;
            missingList.appendChild(li);
          });
          renderDialog(missingDialog, result.prompt, result.raw_response);
          missingModal.style.display = 'flex';
          missingConfirm.onclick = async () => {
            try {
              const resp = await fetch(`/files/${result.id}/finalize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ missing: result.missing || [], confirm: true }),
              });
              if (!resp.ok) throw new Error();
              const finalData = await resp.json();
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
                body: JSON.stringify({ status: 'rejected' }),
              });
            } catch {
              // ignore errors, просто закрываем модалку
            }
            missingModal.style.display = 'none';
            refreshFiles();
          };
        } else {
          openPreviewModal(result);
        }
      } else {
        alert('Ошибка загрузки');
      }
    };
    xhr.send(data);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && missingModal.style.display === 'flex') {
      missingModal.style.display = 'none';
    }
  });
}

function openPreviewModal(result: any) {
  currentId = result.id;
  openMetadataModal({ id: result.id, metadata: result.metadata } as FileInfo);
  previewDialog.style.display = 'block';
  textPreview.style.display = 'block';
  buttonsWrap.style.display = 'flex';
  renderDialog(previewDialog, result.prompt, result.raw_response);
  textPreview.value = result.metadata?.extracted_text || '';
  const saveBtn = editForm.querySelector('button[type="submit"]') as HTMLButtonElement;
  saveBtn.style.display = 'none';
  inputs.forEach((el) => (el.disabled = true));
}
