import { refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';
import { openImageEditModal } from './imageEditor.js';
import { sent, received } from './uploadForm.js';

export let currentImageIndex = -1;
export let imageFiles: Array<{ blob: Blob; name: string }> = [];

let imageInput: HTMLInputElement;
let imageDropArea: HTMLElement;
let selectImagesBtn: HTMLElement;
let imageList: HTMLElement;
let uploadImagesBtn: HTMLElement;

export function setupImageBatch() {
  imageInput = document.getElementById('image-files') as HTMLInputElement;
  imageDropArea = document.getElementById('image-drop-area')!;
  selectImagesBtn = document.getElementById('select-images-btn')!;
  imageList = document.getElementById('selected-images')!;
  uploadImagesBtn = document.getElementById('upload-images-btn')!;

  imageInput.addEventListener('change', (e) => {
    const files = Array.from((e.target as HTMLInputElement).files || []).filter(f => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      renderImageList();
      openImageEditModal(imageFiles[0]);
    }
  });

  const isTouchDevice = typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches;

  selectImagesBtn.addEventListener('click', () => imageInput.click());
  selectImagesBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
    imageInput.click();
  });

  if (!isTouchDevice) {
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
  }
  imageDropArea.addEventListener('click', () => imageInput.click());
  uploadImagesBtn.addEventListener('click', () => uploadEditedImages());
}

export function renderImageList() {
  imageList.innerHTML = '';
  imageFiles.forEach(f => {
    const li = document.createElement('li');
    li.textContent = f.name;
    li.addEventListener('click', () => openImageEditModal(f));
    imageList.appendChild(li);
  });
}

export async function uploadEditedImages() {
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

export function setCurrentImageIndex(idx: number) {
  currentImageIndex = idx;
}

export function getCurrentImageIndex() {
  return currentImageIndex;
}
