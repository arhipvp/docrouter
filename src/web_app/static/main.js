document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const list = document.getElementById('files');
  const folderTree = document.getElementById('folder-tree');
  const progress = document.getElementById('upload-progress');
  const sent = document.getElementById('ai-sent');
  const received = document.getElementById('ai-received');
  const createFolderBtn = document.getElementById('create-folder-btn');
  const newFolderInput = document.getElementById('new-folder-name');
  const renameModal = document.getElementById('rename-modal');
  const deleteModal = document.getElementById('delete-modal');
  const renameInput = document.getElementById('rename-input');
  const renameConfirm = document.getElementById('rename-confirm');
  const deleteConfirm = document.getElementById('delete-confirm');
  const deleteTarget = document.getElementById('delete-target');

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

  function renderTree(container, tree, basePath = '') {
    Object.keys(tree).forEach(key => {
      const li = document.createElement('li');
      const currentPath = basePath ? `${basePath}/${key}` : key;
      const nameSpan = document.createElement('span');
      nameSpan.textContent = key;
      li.appendChild(nameSpan);

      const renameBtn = document.createElement('button');
      renameBtn.textContent = '✎';
      renameBtn.classList.add('rename-btn');
      renameBtn.dataset.path = currentPath;
      li.appendChild(renameBtn);

      const deleteBtn = document.createElement('button');
      deleteBtn.textContent = '🗑';
      deleteBtn.classList.add('delete-btn');
      deleteBtn.dataset.path = currentPath;
      li.appendChild(deleteBtn);

      const children = tree[key];
      if (children && Object.keys(children).length > 0) {
        const ul = document.createElement('ul');
        renderTree(ul, children, currentPath);
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

  createFolderBtn.addEventListener('click', async () => {
    const name = newFolderInput.value.trim();
    if (!name) return;
    await fetch(`/folders?path=${encodeURIComponent(name)}`, { method: 'POST' });
    newFolderInput.value = '';
    refreshFolderTree();
  });

  folderTree.addEventListener('click', (e) => {
    if (e.target.classList.contains('rename-btn')) {
      const path = e.target.dataset.path;
      renameModal.dataset.path = path;
      renameInput.value = path.split('/').pop();
      renameModal.style.display = 'flex';
    }
    if (e.target.classList.contains('delete-btn')) {
      const path = e.target.dataset.path;
      deleteModal.dataset.path = path;
      deleteTarget.textContent = path;
      deleteModal.style.display = 'flex';
    }
  });

  document.querySelectorAll('.modal .close').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal').style.display = 'none';
    });
  });

  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
      e.target.style.display = 'none';
    }
  });

  renameConfirm.addEventListener('click', async () => {
    const path = renameModal.dataset.path;
    const newName = renameInput.value.trim();
    if (!path || !newName) return;
    await fetch(`/folders/${encodeURIComponent(path)}?new_name=${encodeURIComponent(newName)}`, { method: 'PATCH' });
    renameModal.style.display = 'none';
    refreshFolderTree();
  });

  deleteConfirm.addEventListener('click', async () => {
    const path = deleteModal.dataset.path;
    if (!path) return;
    await fetch(`/folders/${encodeURIComponent(path)}`, { method: 'DELETE' });
    deleteModal.style.display = 'none';
    refreshFolderTree();
  });

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
