var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { imageFiles, renderImageList, uploadEditedImages, getCurrentImageIndex, setCurrentImageIndex } from './imageBatch.js';
let imageEditModal;
let editCanvas;
let rotateLeftBtn;
let rotateRightBtn;
let saveBtn;
let cropper = null;
export function setupImageEditor() {
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
            const idx = getCurrentImageIndex();
            if (blob && idx >= 0) {
                const name = ((_a = imageFiles[idx]) === null || _a === void 0 ? void 0 : _a.name) || 'cropped.jpg';
                imageFiles[idx] = { blob, name };
                renderImageList();
            }
            closeEditor();
            const nextIndex = getCurrentImageIndex() + 1;
            if (nextIndex < imageFiles.length) {
                setCurrentImageIndex(nextIndex);
                openImageEditModal(imageFiles[nextIndex]);
            }
            else {
                yield uploadEditedImages();
            }
        }));
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && imageEditModal.style.display === 'flex') {
            closeEditor();
        }
    });
}
export function openImageEditModal(fileObj) {
    if (!fileObj)
        return;
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
function closeEditor() {
    imageEditModal.style.display = 'none';
    cropper === null || cropper === void 0 ? void 0 : cropper.destroy();
    cropper = null;
}
