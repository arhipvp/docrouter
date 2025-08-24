let folderTree: HTMLElement;
let createForm: HTMLFormElement | null;
let renameForm: HTMLFormElement | null;
let deleteForm: HTMLFormElement | null;
let folderMessage: HTMLElement;

export function setupFolders() {
  folderTree = document.getElementById('folder-tree')!;
  createForm = document.getElementById('create-folder-form') as HTMLFormElement;
  renameForm = document.getElementById('rename-folder-form') as HTMLFormElement;
  deleteForm = document.getElementById('delete-folder-form') as HTMLFormElement;
  folderMessage = document.getElementById('folder-message')!;

  folderTree.addEventListener('click', async (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains('rename-btn')) {
      const path = target.dataset.path!;
      const suggested = path.split('/').pop() || '';
      const newName = prompt('Новое имя папки:', suggested);
      if (!newName) return;
      try {
        await renameFolder(path, newName.trim());
        folderMessage.textContent = 'Папка переименована';
      } catch (err: any) {
        folderMessage.textContent = err.message;
      }
    }
    if (target.classList.contains('delete-btn')) {
      const path = target.dataset.path!;
      if (!path) return;
      if (!confirm(`Удалить папку: ${path}?`)) return;
      try {
        await deleteFolder(path);
        folderMessage.textContent = 'Папка удалена';
      } catch (err: any) {
        folderMessage.textContent = err.message;
      }
    }
  });

  createForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const path = (document.getElementById('create-folder-path') as HTMLInputElement).value.trim();
    if (!path) return;
    try {
      await createFolder(path);
      folderMessage.textContent = 'Папка создана';
      createForm.reset();
    } catch (err: any) {
      folderMessage.textContent = err.message;
    }
  });

  renameForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const oldPath = (document.getElementById('rename-folder-old') as HTMLInputElement).value.trim();
    const newName = (document.getElementById('rename-folder-new') as HTMLInputElement).value.trim();
    if (!oldPath || !newName) return;
    try {
      await renameFolder(oldPath, newName);
      folderMessage.textContent = 'Папка переименована';
      renameForm.reset();
    } catch (err: any) {
      folderMessage.textContent = err.message;
    }
  });

  deleteForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const path = (document.getElementById('delete-folder-path') as HTMLInputElement).value.trim();
    if (!path) return;
    if (!confirm('Удалить папку?')) return;
    try {
      await deleteFolder(path);
      folderMessage.textContent = 'Папка удалена';
      deleteForm.reset();
    } catch (err: any) {
      folderMessage.textContent = err.message;
    }
  });
}

function renderTree(container: HTMLElement, tree: any, basePath = '') {
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

export async function refreshFolderTree() {
  const resp = await fetch('/folder-tree');
  if (!resp.ok) return;
  const tree = await resp.json();
  folderTree.innerHTML = '';
  renderTree(folderTree, tree);
}

async function createFolder(path: string) {
  const resp = await fetch(`/folders?path=${encodeURIComponent(path)}`, { method: 'POST' });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка создания папки' }));
    throw new Error(err.detail || 'Ошибка создания папки');
  }
  await refreshFolderTree();
}

async function renameFolder(oldPath: string, newName: string) {
  const encoded = oldPath.split('/').map(encodeURIComponent).join('/');
  const resp = await fetch(`/folders/${encoded}?new_name=${encodeURIComponent(newName)}`, { method: 'PATCH' });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка переименования' }));
    throw new Error(err.detail || 'Ошибка переименования');
  }
  await refreshFolderTree();
}

async function deleteFolder(path: string) {
  const encoded = path.split('/').map(encodeURIComponent).join('/');
  const resp = await fetch(`/folders/${encoded}`, { method: 'DELETE' });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Ошибка удаления' }));
    throw new Error(err.detail || 'Ошибка удаления');
  }
  await refreshFolderTree();
}
