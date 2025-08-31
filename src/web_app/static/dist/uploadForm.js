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
export let sent;
export let received;
export function setupUploadForm() {
    const form = document.querySelector('form');
    const progress = document.getElementById('upload-progress');
    sent = document.getElementById('ai-sent');
    received = document.getElementById('ai-received');
    const missingModal = document.getElementById('missing-modal');
    const missingList = document.getElementById('missing-list');
    const missingConfirm = document.getElementById('missing-confirm');
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
                    missingModal.style.display = 'flex';
                    missingConfirm.onclick = () => __awaiter(this, void 0, void 0, function* () {
                        try {
                            const resp = yield fetch(`/files/${result.id}/finalize`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ missing: result.missing || [] })
                            });
                            if (!resp.ok)
                                throw new Error();
                            const finalData = yield resp.json();
                            missingModal.style.display = 'none';
                            sent.textContent = finalData.prompt || '';
                            received.textContent = finalData.raw_response || '';
                            form.reset();
                            progress.value = 0;
                            refreshFiles();
                            refreshFolderTree();
                        }
                        catch (_a) {
                            alert('Ошибка обработки');
                        }
                    });
                }
                else {
                    sent.textContent = result.prompt || '';
                    received.textContent = result.raw_response || '';
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
