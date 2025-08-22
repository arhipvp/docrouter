document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const list = document.getElementById('files');
  const fileInput = document.querySelector('input[type="file"]');
  const dropZone = document.getElementById('drop-zone');

  async function refreshFiles() {
    const resp = await fetch('/files');
    if (!resp.ok) return;
    const files = await resp.json();
    list.innerHTML = '';
    files.forEach(f => {
      const li = document.createElement('li');
      const link = document.createElement('a');
      link.href = `/download/${f.id}`;
      link.textContent = 'скачать';
      li.innerHTML = `<strong>${f.id}</strong> — ${f.status} `;
      li.appendChild(link);
      list.appendChild(li);
    });
  }

  async function uploadFiles(files) {
    for (const file of files) {
      const data = new FormData();
      data.append('file', file);
      data.append('language', document.getElementById('language').value);
      const resp = await fetch('/upload', { method: 'POST', body: data });
      if (!resp.ok) {
        alert('Ошибка загрузки');
        return;
      }
      await refreshFiles();
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await uploadFiles(fileInput.files);
    form.reset();
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('highlight');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('highlight');
  });

  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('highlight');
    await uploadFiles(e.dataTransfer.files);
    form.reset();
  });

  refreshFiles();
});
