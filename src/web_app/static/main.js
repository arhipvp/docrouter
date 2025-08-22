document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const list = document.getElementById('files');
  const folderTree = document.getElementById('folder-tree');
  const progress = document.getElementById('upload-progress');
  const sent = document.getElementById('ai-sent');
  const received = document.getElementById('ai-received');

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

  function renderTree(container, tree) {
    Object.keys(tree).forEach(key => {
      const li = document.createElement('li');
      li.textContent = key;
      const children = tree[key];
      if (children && Object.keys(children).length > 0) {
        const ul = document.createElement('ul');
        renderTree(ul, children);
        li.appendChild(ul);
      }
      container.appendChild(li);
    });
  }

  async function refreshFolderTree() {
    const resp = await fetch('/folder-tree');
    if (!resp.ok) return;
    const tree = await resp.json();
    folderTree.innerHTML = '';
    renderTree(folderTree, tree);
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
        const result = JSON.parse(xhr.responseText);
        sent.textContent = result.prompt || '';
        received.textContent = result.raw_response || '';
        form.reset();
        progress.value = 0;
        refreshFiles();
        refreshFolderTree();
      } else {
        alert('Ошибка загрузки');
      }
    };
    xhr.send(data);
  });

  refreshFiles();
  refreshFolderTree();
});
