var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';
import { openImageEditModal } from './imageEditor.js';
import { aiExchange, renderDialog } from './uploadForm.js';
export let currentImageIndex = -1;
export let imageFiles = [];
let fileInput;
let imageList;
let uploadImagesBtn;
let imageBlock;
let singleUploadBtn;
export function setupImageBatch() {
    fileInput = document.getElementById('file-input');
    imageList = document.getElementById('selected-images');
    uploadImagesBtn = document.getElementById('upload-images-btn');
    imageBlock = document.getElementById('image-upload-block');
    singleUploadBtn = document.getElementById('single-upload-btn');
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
        }
        else {
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
export function uploadEditedImages() {
    return __awaiter(this, void 0, void 0, function* () {
        if (!imageFiles.length)
            return;
        const data = new FormData();
        imageFiles.forEach(f => {
            const file = new File([f.blob], f.name, { type: 'image/jpeg' });
            data.append('files', file);
        });
        const resp = yield fetch('/upload/images', { method: 'POST', body: data });
        if (resp.ok) {
            const result = yield resp.json();
            renderDialog(aiExchange, result.prompt, result.raw_response);
            imageFiles = [];
            currentImageIndex = -1;
            fileInput.value = '';
            imageBlock.style.display = 'none';
            singleUploadBtn.style.display = '';
            renderImageList();
            refreshFiles();
            refreshFolderTree();
        }
        else {
            alert('Ошибка загрузки');
        }
    });
}
export function setCurrentImageIndex(idx) {
    currentImageIndex = idx;
}
export function getCurrentImageIndex() {
    return currentImageIndex;
}
