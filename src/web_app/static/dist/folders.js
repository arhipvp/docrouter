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
function renderNodes(container, nodes) {
    nodes.forEach((node) => {
        const li = document.createElement('li');
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = node.name;
        details.appendChild(summary);
        if ((node.files && node.files.length) || (node.children && node.children.length)) {
            const ul = document.createElement('ul');
            // Файлы внутри папки
            (node.files || []).forEach((file) => {
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
                }
                else {
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
export function refreshFolderTree() {
    return __awaiter(this, void 0, void 0, function* () {
        folderTree = document.getElementById('folder-tree');
        try {
            const resp = yield apiRequest('/folder-tree');
            if (!resp.ok)
                throw new Error();
            const tree = yield resp.json();
            folderTree.innerHTML = '';
            renderNodes(folderTree, tree);
        }
        catch (_a) {
            showNotification('Не удалось загрузить дерево папок');
        }
    });
}
