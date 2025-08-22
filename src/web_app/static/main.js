document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const list = document.getElementById('files');
  const folderTree = document.getElementById('folder-tree');
  const progress = document.getElementById('upload-progress');
  const sent = document.getElementById('ai-sent');
  const received = document.getElementById('ai-received');
  const createForm = document.getElementById('create-folder-form');
  const renameForm = document.getElementById('rename-folder-form');
  const deleteForm = document.getElementById('delete-folder-form');
  const folderMessage = document.getElementById('folder-message');

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

  async function createFolder(path) {
    const resp = await fetch(`/folders?path=${encodeURIComponent(path)}`, {
      method: 'POST'
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Ошибка создания папки' }));
      throw new Error(err.detail || 'Ошибка создания папки');
    }
    await refreshFolderTree();
  }

  async function renameFolder(oldPath, newName) {
    const encoded = oldPath.split('/').map(encodeURIComponent).join('/');
    const resp = await fetch(`/folders/${encoded}?new_name=${encodeURIComponent(newName)}`, {
      method: 'PATCH'
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Ошибка переименования' }));
      throw new Error(err.detail || 'Ошибка переименования');
    }
    await refreshFolderTree();
  }

  async function deleteFolder(path) {
    const encoded = path.split('/').map(encodeURIComponent).join('/');
    const resp = await fetch(`/folders/${encoded}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Ошибка удаления' }));
      throw new Error(err.detail || 'Ошибка удаления');
    }
    await refreshFolderTree();
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

  createForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const path = document.getElementById('create-folder-path').value.trim();
    if (!path) return;
    try {
      await createFolder(path);
      folderMessage.textContent = 'Папка создана';
      createForm.reset();
    } catch (err) {
      folderMessage.textContent = err.message;
    }
  });

  renameForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const oldPath = document.getElementById('rename-folder-old').value.trim();
    const newName = document.getElementById('rename-folder-new').value.trim();
    if (!oldPath || !newName) return;
    try {
      await renameFolder(oldPath, newName);
      folderMessage.textContent = 'Папка переименована';
      renameForm.reset();
    } catch (err) {
      folderMessage.textContent = err.message;
    }
  });

  deleteForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const path = document.getElementById('delete-folder-path').value.trim();
    if (!path) return;
    if (!confirm('Удалить папку?')) return;
    try {
      await deleteFolder(path);
      folderMessage.textContent = 'Папка удалена';
      deleteForm.reset();
    } catch (err) {
      folderMessage.textContent = err.message;
    }
  });

  refreshFiles();
  refreshFolderTree();
});
