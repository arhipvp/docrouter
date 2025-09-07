import { imageFiles, renderImageList, uploadEditedImages, getCurrentImageIndex, setCurrentImageIndex } from './imageBatch.js';

let imageEditModal: HTMLElement;
let editCanvas: HTMLCanvasElement;
let rotateLeftBtn: HTMLElement | null;
let rotateRightBtn: HTMLElement | null;
let saveBtn: HTMLElement | null;
let cropper: any = null;
let rotateHandler: ((e: Event) => void) | null = null;

function autoCropImage() {
  if (!cropper) return;
  const ctx = editCanvas.getContext('2d');
  if (!ctx) return;
  const { width, height } = editCanvas;
  if (!width || !height) return;
  const { data } = ctx.getImageData(0, 0, width, height);
  let left = width, right = -1, top = height, bottom = -1;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const alpha = data[(y * width + x) * 4 + 3];
      if (alpha !== 0) {
        if (x < left) left = x;
        if (x > right) right = x;
        if (y < top) top = y;
        if (y > bottom) bottom = y;
      }
    }
  }
  if (right >= left && bottom >= top) {
    cropper.setData({ x: left, y: top, width: right - left + 1, height: bottom - top + 1 });
  }
}

export function setupImageEditor() {
  imageEditModal = document.getElementById('edit-modal')!;
  editCanvas = document.getElementById('edit-canvas') as HTMLCanvasElement;
  rotateLeftBtn = document.getElementById('rotate-left-btn');
  rotateRightBtn = document.getElementById('rotate-right-btn');
  saveBtn = document.getElementById('save-btn');

  rotateLeftBtn?.addEventListener('click', () => {
    if (!cropper) return;
    if (rotateHandler) {
      editCanvas.removeEventListener('cropend', rotateHandler);
    }
    rotateHandler = () => {
      autoCropImage();
      editCanvas.removeEventListener('cropend', rotateHandler!);
      rotateHandler = null;
    };
    editCanvas.addEventListener('cropend', rotateHandler);
    cropper.rotate(-90);
  });
  rotateRightBtn?.addEventListener('click', () => {
    if (!cropper) return;
    if (rotateHandler) {
      editCanvas.removeEventListener('cropend', rotateHandler);
    }
    rotateHandler = () => {
      autoCropImage();
      editCanvas.removeEventListener('cropend', rotateHandler!);
      rotateHandler = null;
    };
    editCanvas.addEventListener('cropend', rotateHandler);
    cropper.rotate(90);
  });
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
  cropper?.destroy();
  cropper = null;
}
