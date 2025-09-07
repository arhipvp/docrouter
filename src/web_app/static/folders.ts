import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
import type { FolderTree } from './types.js';

let folderTree: HTMLElement;

export function renderTree(container: HTMLElement, tree: FolderTree) {
  tree.forEach(({ name, children }) => {
    const li = document.createElement('li');

    const nameSpan = document.createElement('span');
    nameSpan.textContent = name;
    li.appendChild(nameSpan);

    if (children && children.length > 0) {
      const ul = document.createElement('ul');
      renderTree(ul, children);
      li.appendChild(ul);
    }
    container.appendChild(li);
  });
}

export async function refreshFolderTree() {
  folderTree = document.getElementById('folder-tree')!;
  try {
    const resp = await apiRequest('/folder-tree');
    if (!resp.ok) throw new Error();
    const tree: FolderTree = await resp.json();
    folderTree.innerHTML = '';
    renderTree(folderTree, tree);
  } catch {
    showNotification('Не удалось загрузить дерево папок');
  }
}
