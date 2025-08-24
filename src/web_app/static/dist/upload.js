let form;
let imageInput;
let rotateLeftBtn;
let rotateRightBtn;
let saveBtn;
let imageEditModal;
let editCanvas;
let imageFiles = [];
let cropper = null;
let currentImageIndex = -1;

export function setupUpload() {
  form = document.querySelector('form');
  imageInput = document.getElementById('image-files');
  rotateLeftBtn = document.getElementById('rotate-left-btn');
  rotateRightBtn = document.getElementById('rotate-right-btn');
  saveBtn = document.getElementById('save-btn');
  imageEditModal = document.getElementById('edit-modal');
  editCanvas = document.getElementById('edit-canvas');

  imageInput?.addEventListener('change', (e) => {
    const files = Array.from(e.target.files).filter(f => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files.map(f => ({ blob: f, name: f.name }));
      currentImageIndex = 0;
      openImageEditModal(imageFiles[0]);
    }
  });

  rotateLeftBtn?.addEventListener('click', () => cropper && cropper.rotate(-90));
  rotateRightBtn?.addEventListener('click', () => cropper && cropper.rotate(90));
  saveBtn?.addEventListener('click', () => {
    if (!cropper) return;
    cropper.getCroppedCanvas().toBlob((blob) => {
      if (blob) {
        imageFiles[currentImageIndex] = { blob, name: imageFiles[currentImageIndex].name };
      }
      imageEditModal.style.display = 'none';
      cropper.destroy();
      cropper = null;
    }, 'image/jpeg');
  });
}

export function refreshFiles() {}

function openImageEditModal(fileObj) {
  const ctx = editCanvas.getContext('2d');
  const img = new Image();
  const url = URL.createObjectURL(fileObj.blob);
  img.onload = () => {
    editCanvas.width = img.width;
    editCanvas.height = img.height;
    ctx.clearRect(0, 0, editCanvas.width, editCanvas.height);
    ctx.drawImage(img, 0, 0);
    if (cropper) cropper.destroy();
    cropper = new Cropper(editCanvas, { viewMode: 1 });
    URL.revokeObjectURL(url);
  };
  img.src = url;
  imageEditModal.style.display = 'flex';
}
