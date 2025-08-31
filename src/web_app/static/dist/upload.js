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
let form;
let progress;
let sent;
let received;
let missingModal;
let missingList;
let missingConfirm;
let suggestedPath;
let imageInput;
let imageDropArea;
let selectImagesBtn;
let imageList;
let uploadImagesBtn;
let imageEditModal;
let editCanvas;
let rotateLeftBtn;
let rotateRightBtn;
let saveBtn;
let cropper = null;
let currentImageIndex = -1;
let imageFiles = [];
export function setupUpload() {
    form = document.querySelector('form');
    progress = document.getElementById('upload-progress');
    sent = document.getElementById('ai-sent');
    received = document.getElementById('ai-received');
    missingModal = document.getElementById('missing-modal');
    missingList = document.getElementById('missing-list');
    missingConfirm = document.getElementById('missing-confirm');
    suggestedPath = document.getElementById('suggested-path');
    imageInput = document.getElementById('image-files');
    imageDropArea = document.getElementById('image-drop-area');
    selectImagesBtn = document.getElementById('select-images-btn');
    imageList = document.getElementById('selected-images');
    uploadImagesBtn = document.getElementById('upload-images-btn');
    imageEditModal = document.getElementById('edit-modal');
    editCanvas = document.getElementById('edit-canvas');
    rotateLeftBtn = document.getElementById('rotate-left-btn');
    rotateRightBtn = document.getElementById('rotate-right-btn');
    saveBtn = document.getElementById('save-btn');
    rotateLeftBtn === null || rotateLeftBtn === void 0 ? void 0 : rotateLeftBtn.addEventListener('click', () => cropper === null || cropper === void 0 ? void 0 : cropper.rotate(-90));
    rotateRightBtn === null || rotateRightBtn === void 0 ? void 0 : rotateRightBtn.addEventListener('click', () => cropper === null || cropper === void 0 ? void 0 : cropper.rotate(90));
    saveBtn === null || saveBtn === void 0 ? void 0 : saveBtn.addEventListener('click', () => {
        if (!cropper)
            return;
        cropper.getCroppedCanvas().toBlob((blob) => __awaiter(this, void 0, void 0, function* () {
            var _a;
            if (blob && currentImageIndex >= 0) {
                const name = ((_a = imageFiles[currentImageIndex]) === null || _a === void 0 ? void 0 : _a.name) || 'cropped.jpg';
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
            }
            else {
                yield uploadEditedImages();
            }
        }));
    });
    form.addEventListener('submit', (e) => {
        var _a;
        e.preventDefault();
        const fileInput = form.querySelector('input[type="file"]');
        const file = (_a = fileInput === null || fileInput === void 0 ? void 0 : fileInput.files) === null || _a === void 0 ? void 0 : _a[0];
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
                    (result.missing || []).forEach((path) => {
                        const li = document.createElement('li');
                        li.textContent = path;
                        missingList.appendChild(li);
                    });
                    missingModal.style.display = 'flex';
                    missingConfirm.onclick = () => __awaiter(this, void 0, void 0, function* () {
                        try {
                            const resp = yield fetch(`/files/${result.id}/finalize`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ missing: result.missing || [] })
                            });
                            if (!resp.ok)
                                throw new Error();
                            const finalData = yield resp.json();
                            missingModal.style.display = 'none';
                            sent.textContent = finalData.prompt || '';
                            received.textContent = finalData.raw_response || '';
                            form.reset();
                            progress.value = 0;
                            refreshFiles();
                            refreshFolderTree();
                        }
                        catch (_a) {
                            alert('Ошибка обработки');
                        }
                    });
                }
                else {
                    sent.textContent = result.prompt || '';
                    received.textContent = result.raw_response || '';
                    form.reset();
                    progress.value = 0;
                    refreshFiles();
                    refreshFolderTree();
                }
            }
            else {
                alert('Ошибка загрузки');
            }
        };
        xhr.send(data);
    });
    imageInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files || []).filter(f => f.type === 'image/jpeg');
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
        imageDropArea.addEventListener('drop', (e) => {
            var _a;
            e.preventDefault();
            const files = Array.from(((_a = e.dataTransfer) === null || _a === void 0 ? void 0 : _a.files) || []).filter((f) => f.type === 'image/jpeg');
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
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape')
            return;
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
function openImageEditModal(fileObj) {
    if (!fileObj)
        return;
    currentImageIndex = imageFiles.indexOf(fileObj);
    const ctx = editCanvas.getContext('2d');
    const img = new Image();
    const url = URL.createObjectURL(fileObj.blob);
    img.onload = () => {
        editCanvas.width = img.width;
        editCanvas.height = img.height;
        ctx.clearRect(0, 0, editCanvas.width, editCanvas.height);
        ctx.drawImage(img, 0, 0);
        cropper === null || cropper === void 0 ? void 0 : cropper.destroy();
        const CropperCtor = window.Cropper || globalThis.Cropper;
        cropper = new CropperCtor(editCanvas, { viewMode: 1 });
        URL.revokeObjectURL(url);
    };
    img.src = url;
    imageEditModal.style.display = 'flex';
}
function uploadEditedImages() {
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
            sent.textContent = result.prompt || '';
            received.textContent = result.raw_response || '';
            imageFiles = [];
            currentImageIndex = -1;
            imageInput.value = '';
            renderImageList();
            refreshFiles();
            refreshFolderTree();
        }
        else {
            alert('Ошибка загрузки');
        }
    });
}
