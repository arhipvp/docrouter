import { openChatModal, closeChat } from './chat';
import { refreshFolderTree } from './folders';

let form: HTMLFormElement;
let list: HTMLElement;
let textPreview: HTMLElement;
let tagLanguage: HTMLSelectElement;
let progress: HTMLProgressElement;
let sent: HTMLElement;
let received: HTMLElement;
let missingModal: HTMLElement;
let missingList: HTMLElement;
let missingConfirm: HTMLElement;
let suggestedPath: HTMLElement;
let previewModal: HTMLElement;
let previewFrame: HTMLIFrameElement;
let displayLangSelect: HTMLSelectElement;
let imageInput: HTMLInputElement;
let imageDropArea: HTMLElement;
let imageList: HTMLElement;
let uploadImagesBtn: HTMLElement;
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
let imageEditModal: HTMLElement;
let editCanvas: HTMLCanvasElement;
let rotateLeftBtn: HTMLElement | null;
let rotateRightBtn: HTMLElement | null;
let saveBtn: HTMLElement | null;
let currentEditId: string | null = null;
let cropper: any = null;
let currentImageIndex = -1;
let imageFiles: Array<{ blob: Blob; name: string }> = [];
let displayLang = '';

export function setupUpload() {
  form = document.querySelector('form') as HTMLFormElement;
  list = document.getElementById('files')!;
  textPreview = document.getElementById('text-preview')!;
  tagLanguage = document.getElementById('tag-language') as HTMLSelectElement;
  progress = document.getElementById('upload-progress') as HTMLProgressElement;
  sent = document.getElementById('ai-sent')!;
  received = document.getElementById('ai-received')!;
  missingModal = document.getElementById('missing-modal')!;
  missingList = document.getElementById('missing-list')!;
  missingConfirm = document.getElementById('missing-confirm')!;
  suggestedPath = document.getElementById('suggested-path')!;
  previewModal = document.getElementById('preview-modal')!;
  previewFrame = document.getElementById('preview-frame') as HTMLIFrameElement;
  displayLangSelect = document.getElementById('display-lang') as HTMLSelectElement;
  imageInput = document.getElementById('image-files') as HTMLInputElement;
  imageDropArea = document.getElementById('image-drop-area')!;
  imageList = document.getElementById('selected-images')!;
  uploadImagesBtn = document.getElementById('upload-images-btn')!;
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
  imageEditModal = document.getElementById('edit-modal')!;
  editCanvas = document.getElementById('edit-canvas') as HTMLCanvasElement;
  rotateLeftBtn = document.getElementById('rotate-left-btn');
  rotateRightBtn = document.getElementById('rotate-right-btn');
  saveBtn = document.getElementById('save-btn');

  nameOriginalRadio?.addEventListener('change', () => {
    if (nameOriginalRadio.checked) editName.value = nameOriginalRadio.value;
  });
  nameLatinRadio?.addEventListener('change', () => {
    if (nameLatinRadio.checked) editName.value = nameLatinRadio.value;
  });

  displayLangSelect?.addEventListener('change', () => {
    displayLang = displayLangSelect.value;
    refreshFiles();
  });

  document.querySelectorAll('.modal .close').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = (btn as HTMLElement).dataset.close;
      if (target) {
        const modal = document.getElementById(target)!;
        modal.style.display = 'none';
        if (target === 'chat-modal') closeChat();
        if (target === 'metadata-modal') currentEditId = null;
      }
    });
  });

  rotateLeftBtn?.addEventListener('click', () => cropper?.rotate(-90));
  rotateRightBtn?.addEventListener('click', () => cropper?.rotate(90));

  saveBtn?.addEventListener('click', () => {
    if (!cropper) return;
    cropper.getCroppedCanvas().toBlob(async (blob: Blob) => {
      if (blob && currentImageIndex >= 0) {
        const name = imageFiles[currentImageIndex]?.name || 'cropped.jpg';
        imageFiles[currentImageIndex] = { blob, name };
        renderImageList();
      }
      imageEditModal.style.display = 'none';
      cropper.destroy();
      cropper = null;
      const nextIndex = currentImageIndex + 1;
      if (nextIndex < imageFiles.length) {
        currentImageIndex = nextIndex;
        openImageEditModal(imageFiles[currentImageIndex]);
      } else {
        await uploadEditedImages();
      }
    }, 'image/jpeg');
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
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
          missingModal.style.display = 'flex';
          missingConfirm.onclick = async () => {
            try {
              const resp = await fetch(`/files/${result.id}/finalize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ missing: result.missing || [] })
              });
              if (!resp.ok) throw new Error();
              const finalData = await resp.json();
              missingModal.style.display = 'none';
              sent.textContent = finalData.prompt || '';
              received.textContent = finalData.raw_response || '';
              form.reset();
              progress.value = 0;
              refreshFiles();
              refreshFolderTree();
            } catch (err) {
              alert('Ошибка обработки');
            }
          };
        } else {
          sent.textContent = result.prompt || '';
          received.textContent = result.raw_response || '';
          form.reset();
          progress.value = 0;
          refreshFiles();
          refreshFolderTree();
        }
      } else {
        alert('Ошибка загрузки');
      }
    };
    xhr.send(data);
  });

  imageInput?.addEventListener('change', (e) => {
    const files = Array.from((e.target as HTMLInputElement).files || []).filter(f => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      renderImageList();
      openImageEditModal(imageFiles[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(evt => {
    imageDropArea?.addEventListener(evt, (e) => {
      e.preventDefault();
      imageDropArea.classList.add('dragover');
    });
  });
  ['dragleave', 'drop'].forEach(evt => {
    imageDropArea?.addEventListener(evt, (e) => {
      e.preventDefault();
      imageDropArea.classList.remove('dragover');
    });
  });
  imageDropArea?.addEventListener('drop', (e: any) => {
    const files = Array.from(e.dataTransfer.files).filter((f: File) => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      renderImageList();
      openImageEditModal(imageFiles[0]);
    }
  });
  imageDropArea?.addEventListener('click', () => imageInput?.click());
  uploadImagesBtn?.addEventListener('click', () => uploadEditedImages());

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
      alert('Ошибка обновления');
    }
  });

  list.addEventListener('click', async (e: any) => {
    if (e.target.closest('a.download-link') || e.target.closest('button.edit-btn') || e.target.closest('button.chat-btn')) return;
    const li = e.target.closest('li');
    if (!li) return;
    const id = li.dataset.id;
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

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (previewModal.style.display === 'flex') {
      previewModal.style.display = 'none';
      previewFrame.src = '';
    }
    if (metadataModal && metadataModal.style.display === 'flex') {
      metadataModal.style.display = 'none';
      currentEditId = null;
    }
    if (imageEditModal && imageEditModal.style.display === 'flex') {
      imageEditModal.style.display = 'none';
    }
    if (missingModal.style.display === 'flex') {
      missingModal.style.display = 'none';
    }
  });

  tagLanguage.addEventListener('change', refreshFiles);
  refreshFiles();
}

export async function refreshFiles() {
  const resp = await fetch('/files');
  if (!resp.ok) return;
  const files = await resp.json();
  list.innerHTML = '';
  files.forEach((f: any) => {
    const li = document.createElement('li');
    li.dataset.id = f.id;

    const category = f.metadata?.category ?? '';
    const lang = tagLanguage.value;
    const tags = f.metadata ? (lang === 'ru' ? f.metadata.tags_ru : f.metadata.tags_en) : [];
    const tagsText = Array.isArray(tags) ? tags.join(', ') : '';
    li.innerHTML = `<strong>${f.filename}</strong> — ${category} — ${tagsText} — ${f.status} `;

    const link = document.createElement('a');
    const langParam = displayLang ? `?lang=${encodeURIComponent(displayLang)}` : '';
    link.href = `/download/${f.id}${langParam}`;
    link.textContent = 'скачать';
    link.classList.add('download-link');
    li.appendChild(link);

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.textContent = 'Редактировать';
    editBtn.classList.add('edit-btn');
    editBtn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openMetadataModal(f);
    });
    li.appendChild(editBtn);

    const chatBtn = document.createElement('button');
    chatBtn.type = 'button';
    chatBtn.textContent = 'Чат';
    chatBtn.classList.add('chat-btn');
    chatBtn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openChatModal(f);
    });
    li.appendChild(chatBtn);

    list.appendChild(li);
  });
}

function renderImageList() {
  imageList.innerHTML = '';
  imageFiles.forEach(f => {
    const li = document.createElement('li');
    li.textContent = f.name;
    li.addEventListener('click', () => openImageEditModal(f));
    imageList.appendChild(li);
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

function openImageEditModal(fileObj: { blob: Blob; name: string }) {
  if (!fileObj) return;
  currentImageIndex = imageFiles.indexOf(fileObj);
  const ctx = editCanvas.getContext('2d')!;
  const img = new Image();
  const url = URL.createObjectURL(fileObj.blob);
  img.onload = () => {
    editCanvas.width = img.width;
    editCanvas.height = img.height;
    ctx.clearRect(0, 0, editCanvas.width, editCanvas.height);
    ctx.drawImage(img, 0, 0);
    cropper?.destroy();
    cropper = new (window as any).Cropper(editCanvas, { viewMode: 1 });
    URL.revokeObjectURL(url);
  };
  img.src = url;
  imageEditModal.style.display = 'flex';
}

async function uploadEditedImages() {
  if (!imageFiles.length) return;
  const data = new FormData();
  imageFiles.forEach(f => {
    const file = new File([f.blob], f.name, { type: 'image/jpeg' });
    data.append('files', file);
  });
  const resp = await fetch('/upload/images', { method: 'POST', body: data });
  if (resp.ok) {
    const result = await resp.json();
    sent.textContent = result.prompt || '';
    received.textContent = result.raw_response || '';
    imageFiles = [];
    currentImageIndex = -1;
    imageInput.value = '';
    renderImageList();
    refreshFiles();
    refreshFolderTree();
  } else {
    alert('Ошибка загрузки');
  }
}
