import { openChatModal } from './chat.js';
import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
import { refreshFolderTree } from './folders.js';
import type { FileInfo, FileMetadata } from './types.js';

let list: HTMLElement;
let textPreview: HTMLElement;
let tagLanguage: HTMLSelectElement;
let displayLangSelect: HTMLSelectElement;
let previewModal: HTMLElement;
let previewFrame: HTMLIFrameElement;
let metadataModal: HTMLElement;
let editForm: HTMLFormElement;
let editCategory: HTMLInputElement;
let editSubcategory: HTMLInputElement;
let editIssuer: HTMLInputElement;
let editDate: HTMLInputElement;
let editName: HTMLInputElement;
let nameOriginalRadio: HTMLInputElement | null;
let nameLatinRadio: HTMLInputElement | null;
let nameOriginalLabel: HTMLElement | null;
let nameLatinLabel: HTMLElement | null;
let currentEditId: string | null = null;
let displayLang = '';
let lastFocused: HTMLElement | null = null;

export function setupFiles() {
  list = document.getElementById('files')!;
  textPreview = document.getElementById('text-preview')!;
  tagLanguage = document.getElementById('tag-language') as HTMLSelectElement;
  displayLangSelect = document.getElementById('display-lang') as HTMLSelectElement;
  previewModal = document.getElementById('preview-modal')!;
  previewFrame = document.getElementById('preview-frame') as HTMLIFrameElement;
  metadataModal = document.getElementById('metadata-modal')!;
  editForm = document.getElementById('edit-form') as HTMLFormElement;
  editCategory = document.getElementById('edit-category') as HTMLInputElement;
  editSubcategory = document.getElementById('edit-subcategory') as HTMLInputElement;
  editIssuer = document.getElementById('edit-issuer') as HTMLInputElement;
  editDate = document.getElementById('edit-date') as HTMLInputElement;
  editName = document.getElementById('edit-name') as HTMLInputElement;
  nameOriginalRadio = document.getElementById('name-original') as HTMLInputElement;
  nameLatinRadio = document.getElementById('name-latin') as HTMLInputElement;
  nameOriginalLabel = document.getElementById('name-original-label');
  nameLatinLabel = document.getElementById('name-latin-label');
  const refreshBtn = document.getElementById('refresh-btn');

  displayLangSelect?.addEventListener('change', () => {
    displayLang = displayLangSelect.value;
    refreshFiles();
  });

  editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentEditId) return;

    const payload: { metadata: FileMetadata } = {
      metadata: {
        category: editCategory.value.trim(),
        subcategory: editSubcategory.value.trim(),
        issuer: editIssuer.value.trim(),
        date: editDate.value,
        suggested_name: editName.value.trim(),
      },
    };
    (Object.keys(payload.metadata) as (keyof FileMetadata)[]).forEach((k) => {
      if (!payload.metadata[k]) delete payload.metadata[k];
    });

    try {
      const resp = await apiRequest(`/files/${currentEditId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error();
      closeModal(metadataModal);
      currentEditId = null;
      await refreshFiles();
    } catch {
      showNotification('Ошибка обновления');
    }
  });

  list.addEventListener('click', async (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (
      target.closest('a.download-link') ||
      target.closest('button.edit-btn') ||
      target.closest('button.chat-btn')
    )
      return;

    const tr = target.closest('tr');
    if (!tr) return;
    const id = (tr as HTMLElement).dataset.id;
    if (!id) return;

    previewFrame.src = `/preview/${id}`;
    openModal(previewModal);

    try {
      const resp = await apiRequest(`/files/${id}/details`);
      if (!resp.ok) throw new Error();
      const data: FileInfo = await resp.json();
      textPreview.textContent = data.extracted_text || '';
    } catch {
      textPreview.textContent = '';
      showNotification('Не удалось получить содержимое файла');
    }
  });

  const previewClose = previewModal.querySelector('.modal__close') as HTMLElement;
  previewClose.addEventListener('click', () => {
    closeModal(previewModal);
    previewFrame.src = '';
  });
  previewModal.addEventListener('click', (e) => {
    if (e.target === previewModal) {
      closeModal(previewModal);
      previewFrame.src = '';
    }
  });

  const metadataClose = metadataModal.querySelector('.modal__close') as HTMLElement;
  metadataClose.addEventListener('click', () => {
    closeModal(metadataModal);
    currentEditId = null;
  });

  tagLanguage.addEventListener('change', () => refreshFiles());
  nameOriginalRadio?.addEventListener('change', () => {
    if (nameOriginalRadio.checked) editName.value = nameOriginalRadio.value;
  });
  nameLatinRadio?.addEventListener('change', () => {
    if (nameLatinRadio.checked) editName.value = nameLatinRadio.value;
  });

  refreshBtn?.addEventListener('click', () => {
    refreshFiles(true);
    refreshFolderTree();
  });

  refreshFiles();
}

export async function refreshFiles(force = false) {
  try {
    const resp = await apiRequest(`/files${force ? '?force=1' : ''}`);
    if (!resp.ok) throw new Error();
    const files: FileInfo[] = await resp.json();

    list.innerHTML = '';
    files.forEach((f: FileInfo) => {
      const tr = document.createElement('tr');
      tr.dataset.id = f.id;

      const pathTd = document.createElement('td');
      pathTd.textContent = f.path || '';
      tr.appendChild(pathTd);

      const categoryTd = document.createElement('td');
      const category = f.metadata?.category ?? '';
      categoryTd.textContent = category;
      tr.appendChild(categoryTd);

      const tagsTd = document.createElement('td');
      const lang = tagLanguage.value;
      const tags = f.metadata ? (lang === 'ru' ? f.metadata.tags_ru : f.metadata.tags_en) : [];
      const tagsText = Array.isArray(tags) ? tags.join(', ') : '';
      tagsTd.textContent = tagsText;
      tr.appendChild(tagsTd);

      const statusTd = document.createElement('td');
      statusTd.textContent = f.status;
      tr.appendChild(statusTd);

      const actionsTd = document.createElement('td');
      const langParam = displayLang ? `?lang=${encodeURIComponent(displayLang)}` : '';

      const link = document.createElement('a');
      link.href = `/download/${f.id}${langParam}`;
      link.textContent = 'скачать';
      link.classList.add('download-link');
      actionsTd.appendChild(link);

      const jsonLink = document.createElement('a');
      jsonLink.href = `/files/${f.id}/details`;
      jsonLink.textContent = 'json';
      jsonLink.target = '_blank';
      actionsTd.appendChild(document.createTextNode(' '));
      actionsTd.appendChild(jsonLink);

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.textContent = 'Редактировать';
      editBtn.classList.add('edit-btn');
      editBtn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        openMetadataModal(f);
      });
      actionsTd.appendChild(editBtn);

      const chatBtn = document.createElement('button');
      chatBtn.type = 'button';
      chatBtn.textContent = 'Чат';
      chatBtn.classList.add('chat-btn');
      chatBtn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        openChatModal(f);
      });
      actionsTd.appendChild(chatBtn);

      tr.appendChild(actionsTd);
      list.appendChild(tr);
    });
  } catch {
    showNotification('Не удалось загрузить список файлов');
  }
}

function openMetadataModal(file: FileInfo) {
  currentEditId = file.id;
  const m: FileMetadata = file.metadata || {};
  editCategory.value = m.category || '';
  editSubcategory.value = m.subcategory || '';
  editIssuer.value = m.issuer || '';
  editDate.value = m.date || '';
  const orig = m.suggested_name || '';
  const latin = m.suggested_name_translit || orig;
  editName.value = orig;

  if (nameOriginalRadio) {
    nameOriginalRadio.value = orig;
    nameOriginalRadio.checked = true;
  }
  if (nameLatinRadio) {
    nameLatinRadio.value = latin;
    nameLatinRadio.checked = false;
  }
  if (nameOriginalLabel) nameOriginalLabel.textContent = orig;
  if (nameLatinLabel) nameLatinLabel.textContent = latin;

  openModal(metadataModal);
}

function openModal(modal: HTMLElement) {
  lastFocused = document.activeElement as HTMLElement;
  modal.style.display = 'flex';
  const focusable = modal.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = (focusable[0] || modal) as HTMLElement;
  if (typeof (first as any).focus === 'function') (first as any).focus();

  const handleKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Tab') {
      const items = modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!items.length) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];

      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    } else if (e.key === 'Escape') {
      closeModal(modal);
      if (modal === previewModal) previewFrame.src = '';
      if (modal === metadataModal) currentEditId = null;
    }
  };
  modal.addEventListener('keydown', handleKeydown);
  (modal as any)._handleKeydown = handleKeydown;
}

function closeModal(modal: HTMLElement) {
  modal.style.display = 'none';
  const handler = (modal as any)._handleKeydown;
  if (handler && typeof (modal as any).removeEventListener === 'function') {
    modal.removeEventListener('keydown', handler);
  }
  (modal as any)._handleKeydown = null;
  lastFocused?.focus();
  lastFocused = null;
}
