var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';
export let aiExchange;
export function renderDialog(container, prompt, response) {
    container.innerHTML = '';
    if (prompt) {
        const userDiv = document.createElement('div');
        userDiv.className = 'ai-message user';
        userDiv.textContent = prompt;
        container.appendChild(userDiv);
    }
    if (response) {
        const aiDiv = document.createElement('div');
        aiDiv.className = 'ai-message assistant';
        aiDiv.textContent = response;
        container.appendChild(aiDiv);
    }
}
export function setupUploadForm() {
    const form = document.querySelector('form');
    const progress = document.getElementById('upload-progress');
    aiExchange = document.getElementById('ai-exchange');
    const missingModal = document.getElementById('missing-modal');
    const missingList = document.getElementById('missing-list');
    const missingConfirm = document.getElementById('missing-confirm');
    const missingCancel = document.getElementById('missing-cancel');
    const missingDialog = document.getElementById('missing-dialog');
    const suggestedPath = document.getElementById('suggested-path');
    form.addEventListener('submit', (e) => {
        var _a;
        e.preventDefault();
        const fileInput = form.querySelector('input[type="file"]');
        const file = (_a = fileInput === null || fileInput === void 0 ? void 0 : fileInput.files) === null || _a === void 0 ? void 0 : _a[0];
        if (!file || !file.name) {
            alert('Файл должен иметь имя');
            return;
        }
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
                    suggestedPath.textContent = result.suggested_path || '';
                    missingList.innerHTML = '';
                    (result.missing || []).forEach((path) => {
                        const li = document.createElement('li');
                        li.textContent = path;
                        missingList.appendChild(li);
                    });
                    renderDialog(missingDialog, result.prompt, result.raw_response);
                    missingModal.style.display = 'flex';
                    missingConfirm.onclick = () => __awaiter(this, void 0, void 0, function* () {
                        try {
                            const resp = yield fetch(`/files/${result.id}/finalize`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ missing: result.missing || [], confirm: true }),
                            });
                            if (!resp.ok)
                                throw new Error();
                            const finalData = yield resp.json();
                            missingModal.style.display = 'none';
                            renderDialog(aiExchange, finalData.prompt, finalData.raw_response);
                            form.reset();
                            progress.value = 0;
                            refreshFiles();
                            refreshFolderTree();
                        }
                        catch (_a) {
                            alert('Ошибка обработки');
                        }
                    });
                    missingCancel.onclick = () => __awaiter(this, void 0, void 0, function* () {
                        try {
                            yield fetch(`/files/${result.id}`, {
                                method: 'PATCH',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ status: 'rejected' }),
                            });
                        }
                        catch (_a) {
                            // ignore errors, просто закрываем модалку
                        }
                        missingModal.style.display = 'none';
                        refreshFiles();
                    });
                }
                else {
                    renderDialog(aiExchange, result.prompt, result.raw_response);
                    form.reset();
                    progress.value = 0;
                    refreshFiles();
                    refreshFolderTree();
                }
            }
            else {
                alert('Ошибка загрузки');
            }
        };
        xhr.send(data);
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && missingModal.style.display === 'flex') {
            missingModal.style.display = 'none';
        }
    });
}
