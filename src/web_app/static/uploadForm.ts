import { refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';

export let sent: HTMLElement;
export let received: HTMLElement;

export function setupUploadForm() {
  const form = document.querySelector('form') as HTMLFormElement;
  const progress = document.getElementById('upload-progress') as HTMLProgressElement;
  sent = document.getElementById('ai-sent')!;
  received = document.getElementById('ai-received')!;
  const missingModal = document.getElementById('missing-modal')!;
  const missingList = document.getElementById('missing-list')!;
  const missingConfirm = document.getElementById('missing-confirm')!;
  const suggestedPath = document.getElementById('suggested-path')!;

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

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && missingModal.style.display === 'flex') {
      missingModal.style.display = 'none';
    }
  });
}
