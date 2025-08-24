var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
let folderTree;
let createForm;
let renameForm;
let deleteForm;
let folderMessage;
export function setupFolders() {
    folderTree = document.getElementById('folder-tree');
    createForm = document.getElementById('create-folder-form');
    renameForm = document.getElementById('rename-folder-form');
    deleteForm = document.getElementById('delete-folder-form');
    folderMessage = document.getElementById('folder-message');
    folderTree.addEventListener('click', (e) => __awaiter(this, void 0, void 0, function* () {
        const target = e.target;
        if (target.classList.contains('rename-btn')) {
            const path = target.dataset.path;
            const suggested = path.split('/').pop() || '';
            const newName = prompt('Новое имя папки:', suggested);
            if (!newName)
                return;
            try {
                yield renameFolder(path, newName.trim());
                folderMessage.textContent = 'Папка переименована';
            }
            catch (err) {
                folderMessage.textContent = err.message;
            }
        }
        if (target.classList.contains('delete-btn')) {
            const path = target.dataset.path;
            if (!path)
                return;
            if (!confirm(`Удалить папку: ${path}?`))
                return;
            try {
                yield deleteFolder(path);
                folderMessage.textContent = 'Папка удалена';
            }
            catch (err) {
                folderMessage.textContent = err.message;
            }
        }
    }));
    createForm === null || createForm === void 0 ? void 0 : createForm.addEventListener('submit', (e) => __awaiter(this, void 0, void 0, function* () {
        e.preventDefault();
        const path = document.getElementById('create-folder-path').value.trim();
        if (!path)
            return;
        try {
            yield createFolder(path);
            folderMessage.textContent = 'Папка создана';
            createForm.reset();
        }
        catch (err) {
            folderMessage.textContent = err.message;
        }
    }));
    renameForm === null || renameForm === void 0 ? void 0 : renameForm.addEventListener('submit', (e) => __awaiter(this, void 0, void 0, function* () {
        e.preventDefault();
        const oldPath = document.getElementById('rename-folder-old').value.trim();
        const newName = document.getElementById('rename-folder-new').value.trim();
        if (!oldPath || !newName)
            return;
        try {
            yield renameFolder(oldPath, newName);
            folderMessage.textContent = 'Папка переименована';
            renameForm.reset();
        }
        catch (err) {
            folderMessage.textContent = err.message;
        }
    }));
    deleteForm === null || deleteForm === void 0 ? void 0 : deleteForm.addEventListener('submit', (e) => __awaiter(this, void 0, void 0, function* () {
        e.preventDefault();
        const path = document.getElementById('delete-folder-path').value.trim();
        if (!path)
            return;
        if (!confirm('Удалить папку?'))
            return;
        try {
            yield deleteFolder(path);
            folderMessage.textContent = 'Папка удалена';
            deleteForm.reset();
        }
        catch (err) {
            folderMessage.textContent = err.message;
        }
    }));
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
export function refreshFolderTree() {
    return __awaiter(this, void 0, void 0, function* () {
        const resp = yield fetch('/folder-tree');
        if (!resp.ok)
            return;
        const tree = yield resp.json();
        folderTree.innerHTML = '';
        renderTree(folderTree, tree);
    });
}
function createFolder(path) {
    return __awaiter(this, void 0, void 0, function* () {
        const resp = yield fetch(`/folders?path=${encodeURIComponent(path)}`, { method: 'POST' });
        if (!resp.ok) {
            const err = yield resp.json().catch(() => ({ detail: 'Ошибка создания папки' }));
            throw new Error(err.detail || 'Ошибка создания папки');
        }
        yield refreshFolderTree();
    });
}
function renameFolder(oldPath, newName) {
    return __awaiter(this, void 0, void 0, function* () {
        const encoded = oldPath.split('/').map(encodeURIComponent).join('/');
        const resp = yield fetch(`/folders/${encoded}?new_name=${encodeURIComponent(newName)}`, { method: 'PATCH' });
        if (!resp.ok) {
            const err = yield resp.json().catch(() => ({ detail: 'Ошибка переименования' }));
            throw new Error(err.detail || 'Ошибка переименования');
        }
        yield refreshFolderTree();
    });
}
function deleteFolder(path) {
    return __awaiter(this, void 0, void 0, function* () {
        const encoded = path.split('/').map(encodeURIComponent).join('/');
        const resp = yield fetch(`/folders/${encoded}`, { method: 'DELETE' });
        if (!resp.ok) {
            const err = yield resp.json().catch(() => ({ detail: 'Ошибка удаления' }));
            throw new Error(err.detail || 'Ошибка удаления');
        }
        yield refreshFolderTree();
    });
}
