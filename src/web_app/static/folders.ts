import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
import type { FolderNode, FileEntry } from './types.js';

let folderTree: HTMLElement;

function renderNodes(container: HTMLElement, nodes: FolderNode[]): void {
  nodes.forEach((node) => {
    const li = document.createElement('li');

    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = node.name;
    details.appendChild(summary);

    if ((node.files && node.files.length) || (node.children && node.children.length)) {
      const ul = document.createElement('ul');

      // Файлы внутри папки
      (node.files || []).forEach((file: FileEntry) => {
        const fileLi = document.createElement('li');
        const fileSpan = document.createElement('span');
        fileSpan.textContent = file.name;
        fileSpan.classList.add('file');

        if (file.id) {
          // Клик по имени файла — открываем предпросмотр
          fileSpan.addEventListener('click', () => {
            window.open(`/preview/${file.id}`, '_blank');
          });

          // Ссылка на скачивание файла
          const dl = document.createElement('a');
          dl.href = `/download/${file.id}`;
          dl.textContent = '⬇';
          dl.addEventListener('click', (e) => e.stopPropagation());

          fileLi.appendChild(fileSpan);
          fileLi.appendChild(document.createTextNode(' '));
          fileLi.appendChild(dl);
        } else {
          fileLi.appendChild(fileSpan);
        }

        ul.appendChild(fileLi);
      });

      // Рекурсивно отрисовываем вложенные папки
      renderNodes(ul, node.children || []);
      details.appendChild(ul);
    }

    li.appendChild(details);
    container.appendChild(li);
  });
}

export function renderTree(container: HTMLElement, tree: FolderNode[]): void {
  renderNodes(container, tree);
}

export async function refreshFolderTree() {
  folderTree = document.getElementById('folder-tree')!;
  try {
    const resp = await apiRequest('/folder-tree');
    if (!resp.ok) throw new Error();
    const tree: FolderNode[] = await resp.json();
    folderTree.innerHTML = '';
    renderNodes(folderTree, tree);
  } catch {
    showNotification('Не удалось загрузить дерево папок');
  }
}
