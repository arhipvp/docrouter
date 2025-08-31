import { refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';

let form: HTMLFormElement;
let progress: HTMLProgressElement;
let sent: HTMLElement;
let received: HTMLElement;
let missingModal: HTMLElement;
let missingList: HTMLElement;
let missingConfirm: HTMLElement;
let suggestedPath: HTMLElement;
let imageInput: HTMLInputElement;
let imageDropArea: HTMLElement;
let imageList: HTMLElement;
let uploadImagesBtn: HTMLElement;
let imageEditModal: HTMLElement;
let editCanvas: HTMLCanvasElement;
let rotateLeftBtn: HTMLElement | null;
let rotateRightBtn: HTMLElement | null;
let saveBtn: HTMLElement | null;
let cropper: any = null;
let currentImageIndex = -1;
let imageFiles: Array<{ blob: Blob; name: string }> = [];

export function setupUpload() {
  form = document.querySelector('form') as HTMLFormElement;
  progress = document.getElementById('upload-progress') as HTMLProgressElement;
  sent = document.getElementById('ai-sent')!;
  received = document.getElementById('ai-received')!;
  missingModal = document.getElementById('missing-modal')!;
  missingList = document.getElementById('missing-list')!;
  missingConfirm = document.getElementById('missing-confirm')!;
  suggestedPath = document.getElementById('suggested-path')!;
  imageInput = document.getElementById('image-files') as HTMLInputElement;
  imageDropArea = document.getElementById('image-drop-area')!;
  imageList = document.getElementById('selected-images')!;
  uploadImagesBtn = document.getElementById('upload-images-btn')!;
  imageEditModal = document.getElementById('edit-modal')!;
  editCanvas = document.getElementById('edit-canvas') as HTMLCanvasElement;
  rotateLeftBtn = document.getElementById('rotate-left-btn');
  rotateRightBtn = document.getElementById('rotate-right-btn');
  saveBtn = document.getElementById('save-btn');

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
    });
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
            } catch {
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

  imageInput.addEventListener('change', (e) => {
    const files = Array.from((e.target as HTMLInputElement).files || []).filter(f => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      renderImageList();
      openImageEditModal(imageFiles[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(evt => {
    imageDropArea.addEventListener(evt, (e) => {
      e.preventDefault();
      imageDropArea.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(evt => {
    imageDropArea.addEventListener(evt, (e) => {
      e.preventDefault();
      imageDropArea.classList.remove('dragover');
    });
  });

  imageDropArea.addEventListener('drop', (e: DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer?.files || []).filter((f: File) => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      renderImageList();
      openImageEditModal(imageFiles[0]);
    }
  });
  imageDropArea.addEventListener('click', () => imageInput.click());
  uploadImagesBtn.addEventListener('click', () => uploadEditedImages());

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (imageEditModal.style.display === 'flex') {
      imageEditModal.style.display = 'none';
    }
    if (missingModal.style.display === 'flex') {
      missingModal.style.display = 'none';
    }
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
    const CropperCtor = (window as any).Cropper || (globalThis as any).Cropper;
    cropper = new CropperCtor(editCanvas, { viewMode: 1 });
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
