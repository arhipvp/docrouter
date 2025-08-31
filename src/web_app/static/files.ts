import { openChatModal } from './chat.js';
import { showError } from './notifications.js';

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

  displayLangSelect?.addEventListener('change', () => {
    displayLang = displayLangSelect.value;
    refreshFiles();
  });

  editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentEditId) return;
    const payload: any = {
      metadata: {
        category: editCategory.value.trim(),
        subcategory: editSubcategory.value.trim(),
        issuer: editIssuer.value.trim(),
        date: editDate.value,
        suggested_name: editName.value.trim()
      }
    };
    Object.keys(payload.metadata).forEach(k => {
      if (!payload.metadata[k]) delete payload.metadata[k];
    });
    const resp = await fetch(`/files/${currentEditId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (resp.ok) {
      metadataModal.style.display = 'none';
      currentEditId = null;
      await refreshFiles();
    } else {
      showError('Ошибка обновления');
    }
  });

  list.addEventListener('click', async (e: any) => {
    if (e.target.closest('a.download-link') || e.target.closest('button.edit-btn') || e.target.closest('button.chat-btn')) return;
    const tr = e.target.closest('tr');
    if (!tr) return;
    const id = tr.dataset.id;
    if (!id) return;
    previewFrame.src = `/preview/${id}`;
    previewModal.style.display = 'flex';
    try {
      const resp = await fetch(`/files/${id}/details`);
      if (resp.ok) {
        const data = await resp.json();
        textPreview.textContent = data.extracted_text || '';
      } else {
        textPreview.textContent = '';
      }
    } catch {
      textPreview.textContent = '';
    }
  });

  const previewClose = previewModal.querySelector('.close') as HTMLElement;
  previewClose.addEventListener('click', () => {
    previewModal.style.display = 'none';
    previewFrame.src = '';
  });
  previewModal.addEventListener('click', (e) => {
    if (e.target === previewModal) {
      previewModal.style.display = 'none';
      previewFrame.src = '';
    }
  });

  const metadataClose = metadataModal.querySelector('.close') as HTMLElement;
  metadataClose.addEventListener('click', () => {
    metadataModal.style.display = 'none';
    currentEditId = null;
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (previewModal.style.display === 'flex') {
      previewModal.style.display = 'none';
      previewFrame.src = '';
    }
    if (metadataModal.style.display === 'flex') {
      metadataModal.style.display = 'none';
      currentEditId = null;
    }
  });

  tagLanguage.addEventListener('change', refreshFiles);
  nameOriginalRadio?.addEventListener('change', () => {
    if (nameOriginalRadio.checked) editName.value = nameOriginalRadio.value;
  });
  nameLatinRadio?.addEventListener('change', () => {
    if (nameLatinRadio.checked) editName.value = nameLatinRadio.value;
  });

  refreshFiles();
}

export async function refreshFiles() {
  const resp = await fetch('/files');
  if (!resp.ok) return;
  const files = await resp.json();
  list.innerHTML = '';
  files.forEach((f: any) => {
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
}

function openMetadataModal(file: any) {
  currentEditId = file.id;
  const m = file.metadata || {};
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
  metadataModal.style.display = 'flex';
}
