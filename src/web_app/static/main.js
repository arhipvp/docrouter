document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const list = document.getElementById('files');
  const tagLanguage = document.getElementById('tag-language');
  const folderTree = document.getElementById('folder-tree');
  const progress = document.getElementById('upload-progress');
  const sent = document.getElementById('ai-sent');
  const received = document.getElementById('ai-received');
  const missingModal = document.getElementById('missing-modal');
  const missingList = document.getElementById('missing-list');
  const missingConfirm = document.getElementById('missing-confirm');
  const previewModal = document.getElementById('preview-modal');
  const previewFrame = document.getElementById('preview-frame');

  const imageInput = document.getElementById('image-files');
  const imageDropArea = document.getElementById('image-drop-area');
  const imageList = document.getElementById('selected-images');
  const uploadImagesBtn = document.getElementById('upload-images-btn');
  let imageFiles = [];

  const editModal = document.getElementById('edit-modal');
  const editForm = document.getElementById('edit-form');
  const editCategory = document.getElementById('edit-category');
  const editSubcategory = document.getElementById('edit-subcategory');
  const editIssuer = document.getElementById('edit-issuer');
  const editDate = document.getElementById('edit-date');
  const editName = document.getElementById('edit-name');
  let currentEditId = null;

  document.querySelectorAll('.modal .close').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.close;
      if (target) document.getElementById(target).style.display = 'none';
    });
  });

  // UI на формах (вариант codex)
  const createForm = document.getElementById('create-folder-form');
  const renameForm = document.getElementById('rename-folder-form');
  const deleteForm = document.getElementById('delete-folder-form');
  const folderMessage = document.getElementById('folder-message');

  // -------- Файлы --------
  async function refreshFiles() {
    const resp = await fetch('/files');
    if (!resp.ok) return;
    const files = await resp.json();
    list.innerHTML = '';
    files.forEach(f => {
      const li = document.createElement('li');
      li.dataset.id = f.id;

      const category = f.metadata?.category ?? '';
      const lang = tagLanguage.value;
      const tags = f.metadata ? (lang === 'ru' ? f.metadata.tags_ru : f.metadata.tags_en) : [];
      const tagsText = Array.isArray(tags) ? tags.join(', ') : '';
      li.innerHTML = `<strong>${f.filename}</strong> — ${category} — ${tagsText} — ${f.status} `;

      // скачать
      const link = document.createElement('a');
      link.href = `/download/${f.id}`;
      link.textContent = 'скачать';
      link.classList.add('download-link');
      li.appendChild(link);

      // редактировать
      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.textContent = 'Редактировать';
      editBtn.classList.add('edit-btn');
      editBtn.addEventListener('click', (ev) => {
        ev.stopPropagation(); // не открывать предпросмотр
        openEditModal(f);
      });
      li.appendChild(editBtn);

      list.appendChild(li);
    });
  }

  function renderImageList() {
    imageList.innerHTML = '';
    imageFiles.forEach(f => {
      const li = document.createElement('li');
      li.textContent = f.name;
      imageList.appendChild(li);
    });
  }

  function openEditModal(file) {
    currentEditId = file.id;
    const m = file.metadata || {};
    editCategory.value = m.category || '';
    editSubcategory.value = m.subcategory || '';
    editIssuer.value = m.issuer || '';
    editDate.value = m.date || '';
    editName.value = m.suggested_name || '';
    editModal.style.display = 'flex';
  }

  editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentEditId) return;

    const payload = {
      metadata: {
        category: editCategory.value.trim(),
        subcategory: editSubcategory.value.trim(),
        issuer: editIssuer.value.trim(),
        date: editDate.value,
        suggested_name: editName.value.trim()
      }
    };
    // partial update: удаляем пустые поля
    Object.keys(payload.metadata).forEach(k => {
      if (!payload.metadata[k]) delete payload.metadata[k];
    });

    const resp = await fetch(`/files/${currentEditId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      editModal.style.display = 'none';
      currentEditId = null;
      await refreshFiles();
    } else {
      alert('Ошибка обновления');
    }
  });

  // предпросмотр по клику на элемент списка (кроме ссылки и кнопки)
  list.addEventListener('click', (e) => {
    if (e.target.closest('a.download-link') || e.target.closest('button.edit-btn')) return;

    const li = e.target.closest('li');
    if (!li) return;
    const id = li.dataset.id;
    if (!id) return;

    previewFrame.src = `/preview/${id}`;
    previewModal.style.display = 'flex';
  });

  // закрытие предпросмотра
  const previewClose = previewModal.querySelector('.close');
  previewClose.addEventListener('click', () => {
    previewModal.style.display = 'none';
    previewFrame.src = '';
  });
  previewModal.addEventListener('click', (e) => {
    if (e.target === previewModal) {
      previewModal.style.display = 'none';
      previewFrame.src = '';
    }
  });

  // -------- Дерево папок --------
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

  // -------- Операции с папками (серверные вызовы) --------
  async function createFolder(path) {
    const resp = await fetch(`/folders?path=${encodeURIComponent(path)}`, { method: 'POST' });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Ошибка создания папки' }));
      throw new Error(err.detail || 'Ошибка создания папки');
    }
    await refreshFolderTree();
  }

  async function renameFolder(oldPath, newName) {
    const encoded = oldPath.split('/').map(encodeURIComponent).join('/');
    const resp = await fetch(`/folders/${encoded}?new_name=${encodeURIComponent(newName)}`, { method: 'PATCH' });
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

  // -------- Хэндлеры на дереве (кнопки ✎ и 🗑) --------
  folderTree.addEventListener('click', async (e) => {
    const target = e.target;
    if (target.classList.contains('rename-btn')) {
      const path = target.dataset.path;
      const suggested = path.split('/').pop() || '';
      const newName = prompt('Новое имя папки:', suggested);
      if (!newName) return;
      try {
        await renameFolder(path, newName.trim());
        folderMessage.textContent = 'Папка переименована';
      } catch (err) {
        folderMessage.textContent = err.message;
      }
    }
    if (target.classList.contains('delete-btn')) {
      const path = target.dataset.path;
      if (!path) return;
      if (!confirm(`Удалить папку: ${path}?`)) return;
      try {
        await deleteFolder(path);
        folderMessage.textContent = 'Папка удалена';
      } catch (err) {
        folderMessage.textContent = err.message;
      }
    }
  });

  // -------- Загрузка файла --------
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
        if (result.status === 'pending') {
          missingList.innerHTML = '';
          (result.missing || []).forEach((path) => {
            const li = document.createElement('li');
            li.textContent = path;
            missingList.appendChild(li);
          });
          missingModal.style.display = 'flex';
          missingConfirm.onclick = async () => {
            try {
              for (const path of result.missing || []) {
                await fetch(`/folders?path=${encodeURIComponent(path)}`, { method: 'POST' });
              }
              await fetch(`/files/${result.id}/finalize`, { method: 'POST' });
              missingModal.style.display = 'none';
              sent.textContent = result.prompt || '';
              received.textContent = result.raw_response || '';
              form.reset();
              progress.value = 0;
              refreshFiles();
              refreshFolderTree();
            } catch (err) {
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

  // -------- Загрузка набора изображений --------
  imageInput?.addEventListener('change', (e) => {
    imageFiles = Array.from(e.target.files);
    renderImageList();
  });

  ['dragenter', 'dragover'].forEach(evt => {
    imageDropArea?.addEventListener(evt, (e) => {
      e.preventDefault();
      imageDropArea.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(evt => {
    imageDropArea?.addEventListener(evt, (e) => {
      e.preventDefault();
      imageDropArea.classList.remove('dragover');
    });
  });

  imageDropArea?.addEventListener('drop', (e) => {
    const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'image/jpeg');
    if (files.length) {
      imageFiles = files;
      renderImageList();
    }
  });

  imageDropArea?.addEventListener('click', () => imageInput?.click());

  uploadImagesBtn?.addEventListener('click', async () => {
    if (!imageFiles.length) return;
    const data = new FormData();
    imageFiles.forEach(f => data.append('files', f));
    const resp = await fetch('/upload/images', { method: 'POST', body: data });
    if (resp.ok) {
      const result = await resp.json();
      sent.textContent = result.prompt || '';
      received.textContent = result.raw_response || '';
      imageFiles = [];
      imageInput.value = '';
      renderImageList();
      refreshFiles();
      refreshFolderTree();
    } else {
      alert('Ошибка загрузки');
    }
  });

  // -------- Формы для операций с папками --------
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

  // UX: закрытие всех модалок по Esc
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (previewModal.style.display === 'flex') {
      previewModal.style.display = 'none';
      previewFrame.src = '';
    }
    if (editModal.style.display === 'flex') {
      editModal.style.display = 'none';
      currentEditId = null;
    }
    if (missingModal.style.display === 'flex') {
      missingModal.style.display = 'none';
    }
  });

  tagLanguage.addEventListener('change', refreshFiles);

  // Первичная загрузка
  refreshFiles();
  refreshFolderTree();
});
