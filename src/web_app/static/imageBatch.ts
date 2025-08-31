import { refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';
import { openImageEditModal } from './imageEditor.js';
import { aiExchange, renderDialog } from './uploadForm.js';

export let currentImageIndex = -1;
export let imageFiles: Array<{ blob: Blob; name: string }> = [];

let fileInput: HTMLInputElement;
let imageList: HTMLElement;
let uploadImagesBtn: HTMLElement;
let imageBlock: HTMLElement;
let singleUploadBtn: HTMLElement;

export function setupImageBatch() {
  fileInput = document.getElementById('file-input') as HTMLInputElement;
  imageList = document.getElementById('selected-images')!;
  uploadImagesBtn = document.getElementById('upload-images-btn')!;
  imageBlock = document.getElementById('image-upload-block')!;
  singleUploadBtn = document.getElementById('single-upload-btn') as HTMLInputElement;

  fileInput.addEventListener('change', () => {
    const files = Array.from(fileInput.files || []);
    const allJPEG = files.length > 0 && files.every(f => f.type === 'image/jpeg');
    if (allJPEG) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      renderImageList();
      imageBlock.style.display = 'block';
      singleUploadBtn.style.display = 'none';
      openImageEditModal(imageFiles[0]);
    } else {
      imageFiles = [];
      currentImageIndex = -1;
      renderImageList();
      imageBlock.style.display = 'none';
      singleUploadBtn.style.display = '';
      if (files.length > 1) {
        alert('Можно выбрать несколько файлов только в формате JPEG');
        fileInput.value = '';
      }
    }
  });

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
    renderDialog(aiExchange, result.prompt, result.raw_response);
    imageFiles = [];
    currentImageIndex = -1;
    fileInput.value = '';
    imageBlock.style.display = 'none';
    singleUploadBtn.style.display = '';
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
