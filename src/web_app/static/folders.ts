let folderTree: HTMLElement;

function renderTree(container: HTMLElement, tree: any) {
  Object.keys(tree).forEach(key => {
    const li = document.createElement('li');

    const nameSpan = document.createElement('span');
    nameSpan.textContent = key;
    li.appendChild(nameSpan);

    const children = tree[key];
    if (children && Object.keys(children).length > 0) {
      const ul = document.createElement('ul');
      renderTree(ul, children);
      li.appendChild(ul);
    }
    container.appendChild(li);
  });
}

export async function refreshFolderTree() {
  folderTree = document.getElementById('folder-tree')!;
  const resp = await fetch('/folder-tree');
  if (!resp.ok) return;
  const tree = await resp.json();
  folderTree.innerHTML = '';
  renderTree(folderTree, tree);
}

