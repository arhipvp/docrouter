document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const list = document.getElementById('files');
  const progress = document.getElementById('upload-progress');

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
      const category = f.metadata && f.metadata.category ? f.metadata.category : '';
      li.innerHTML = `<strong>${f.filename}</strong> — ${category} — ${f.status} `;
      li.appendChild(link);
      list.appendChild(li);
    });
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
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
        form.reset();
        progress.value = 0;
        refreshFiles();
      } else {
        alert('Ошибка загрузки');
      }
    };
    xhr.send(data);
  });

  refreshFiles();
});
