import { imageFiles, renderImageList, uploadEditedImages, getCurrentImageIndex, setCurrentImageIndex } from './imageBatch.js';

let imageEditModal: HTMLElement;
let editCanvas: HTMLCanvasElement;
let rotateLeftBtn: HTMLElement | null;
let rotateRightBtn: HTMLElement | null;
let saveBtn: HTMLElement | null;
let cropper: any = null;

export function setupImageEditor() {
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
      const idx = getCurrentImageIndex();
      if (blob && idx >= 0) {
        const name = imageFiles[idx]?.name || 'cropped.jpg';
        imageFiles[idx] = { blob, name };
        renderImageList();
      }
      closeEditor();
      const nextIndex = getCurrentImageIndex() + 1;
      if (nextIndex < imageFiles.length) {
        setCurrentImageIndex(nextIndex);
        openImageEditModal(imageFiles[nextIndex]);
      } else {
        await uploadEditedImages();
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && imageEditModal.style.display === 'flex') {
      closeEditor();
    }
  });
}

export function openImageEditModal(fileObj: { blob: Blob; name: string }) {
  if (!fileObj) return;
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

function closeEditor() {
  imageEditModal.style.display = 'none';
  cropper?.destroy();
  cropper = null;
}
