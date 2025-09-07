var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
let folderTree;
export function renderTree(container, tree) {
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
export function refreshFolderTree() {
    return __awaiter(this, void 0, void 0, function* () {
        folderTree = document.getElementById('folder-tree');
        try {
            const resp = yield apiRequest('/folder-tree');
            if (!resp.ok)
                throw new Error();
            const tree = yield resp.json();
            folderTree.innerHTML = '';
            renderTree(folderTree, tree);
        }
        catch (_a) {
            showNotification('Не удалось загрузить дерево папок');
        }
    });
}
