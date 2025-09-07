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
let rotateHandler = null;
function autoCropImage() {
    if (!cropper)
        return;
    const ctx = editCanvas.getContext('2d');
    if (!ctx)
        return;
    const { width, height } = editCanvas;
    if (!width || !height)
        return;
    const { data } = ctx.getImageData(0, 0, width, height);
    const bgR = data[0];
    const bgG = data[1];
    const bgB = data[2];
    const threshold = 30;
    let left = width, right = -1, top = height, bottom = -1;
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const idx = (y * width + x) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const b = data[idx + 2];
            const diff = Math.abs(r - bgR) + Math.abs(g - bgG) + Math.abs(b - bgB);
            if (diff > threshold) {
                if (x < left)
                    left = x;
                if (x > right)
                    right = x;
                if (y < top)
                    top = y;
                if (y > bottom)
                    bottom = y;
            }
        }
    }
    if (right >= left && bottom >= top) {
        cropper.setData({ x: left, y: top, width: right - left + 1, height: bottom - top + 1 });
    }
}
export function setupImageEditor() {
    imageEditModal = document.getElementById('edit-modal');
    editCanvas = document.getElementById('edit-canvas');
    rotateLeftBtn = document.getElementById('rotate-left-btn');
    rotateRightBtn = document.getElementById('rotate-right-btn');
    saveBtn = document.getElementById('save-btn');
    rotateLeftBtn === null || rotateLeftBtn === void 0 ? void 0 : rotateLeftBtn.addEventListener('click', () => {
        if (!cropper)
            return;
        if (rotateHandler) {
            editCanvas.removeEventListener('cropend', rotateHandler);
        }
        rotateHandler = () => {
            autoCropImage();
            editCanvas.removeEventListener('cropend', rotateHandler);
            rotateHandler = null;
        };
        editCanvas.addEventListener('cropend', rotateHandler);
        cropper.rotate(-90);
    });
    rotateRightBtn === null || rotateRightBtn === void 0 ? void 0 : rotateRightBtn.addEventListener('click', () => {
        if (!cropper)
            return;
        if (rotateHandler) {
            editCanvas.removeEventListener('cropend', rotateHandler);
        }
        rotateHandler = () => {
            autoCropImage();
            editCanvas.removeEventListener('cropend', rotateHandler);
            rotateHandler = null;
        };
        editCanvas.addEventListener('cropend', rotateHandler);
        cropper.rotate(90);
    });
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
        cropper = new CropperCtor(editCanvas, {
            viewMode: 1,
            ready: autoCropImage,
        });
        URL.revokeObjectURL(url);
    };
    img.src = url;
    imageEditModal.style.display = 'flex';
}
function closeEditor() {
    imageEditModal.style.display = 'none';
    if (rotateHandler) {
        editCanvas.removeEventListener('cropend', rotateHandler);
        rotateHandler = null;
    }
    cropper === null || cropper === void 0 ? void 0 : cropper.destroy();
    cropper = null;
}
