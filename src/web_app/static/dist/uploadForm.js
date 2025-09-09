var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { refreshFiles, openMetadataModal, closeModal } from './files.js';
import { refreshFolderTree } from './folders.js';
import { openChatModal } from './chat.js';
export let aiExchange;
let metadataModal;
let editForm;
let previewDialog;
let textPreview;
let buttonsWrap;
let regenerateBtn;
let editBtn;
let finalizeBtn;
let askAiBtn;
let currentId = null;
let inputs;
const fieldMap = {
    'edit-category': 'category',
    'edit-subcategory': 'subcategory',
    'edit-issuer': 'issuer',
    'edit-date': 'date',
    'edit-name': 'suggested_name',
    'edit-description': 'description',
    'edit-summary': 'summary',
};
export function renderDialog(container, prompt, response, history) {
    container.innerHTML = '';
    if (history && history.length) {
        history.forEach((msg) => {
            const div = document.createElement('div');
            div.className = `ai-message ${msg.role === 'user' ? 'user' : 'assistant'}`;
            div.textContent = msg.message;
            container.appendChild(div);
        });
        return;
    }
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
    metadataModal = document.getElementById('metadata-modal');
    editForm = document.getElementById('edit-form');
    const modalContent = metadataModal.querySelector('.modal__content');
    previewDialog = document.createElement('div');
    previewDialog.className = 'ai-dialog';
    previewDialog.style.display = 'none';
    modalContent.insertBefore(previewDialog, editForm);
    textPreview = document.createElement('textarea');
    textPreview.readOnly = true;
    textPreview.style.display = 'none';
    modalContent.insertBefore(textPreview, editForm);
    buttonsWrap = document.createElement('div');
    buttonsWrap.className = 'modal__buttons';
    buttonsWrap.style.display = 'none';
    modalContent.appendChild(buttonsWrap);
    askAiBtn = document.createElement('button');
    askAiBtn.type = 'button';
    askAiBtn.textContent = 'Спросить ИИ';
    buttonsWrap.appendChild(askAiBtn);
    regenerateBtn = document.createElement('button');
    regenerateBtn.type = 'button';
    regenerateBtn.textContent = 'Перегенерировать';
    buttonsWrap.appendChild(regenerateBtn);
    editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.textContent = 'Редактировать';
    buttonsWrap.appendChild(editBtn);
    finalizeBtn = document.createElement('button');
    finalizeBtn.type = 'button';
    finalizeBtn.textContent = 'Финализировать';
    buttonsWrap.appendChild(finalizeBtn);
    inputs = editForm.querySelectorAll('input, textarea');
    const saveBtn = editForm.querySelector('button[type="submit"]');
    const hidePreview = () => {
        previewDialog.style.display = 'none';
        textPreview.style.display = 'none';
        buttonsWrap.style.display = 'none';
        saveBtn.style.display = '';
        inputs.forEach((el) => (el.disabled = false));
        currentId = null;
    };
    const metadataClose = metadataModal.querySelector('.modal__close');
    metadataClose.addEventListener('click', hidePreview);
    regenerateBtn.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
        if (!currentId)
            return;
        try {
            const resp = yield fetch(`/files/${currentId}/comment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: '' }),
            });
            if (!resp.ok)
                throw new Error();
            const data = yield resp.json();
            openPreviewModal(data);
        }
        catch (_a) {
            alert('Ошибка генерации');
        }
    }));
    editBtn.addEventListener('click', () => {
        var _a;
        const disabled = (_a = inputs[0]) === null || _a === void 0 ? void 0 : _a.disabled;
        inputs.forEach((el) => {
            if (!(el.id === 'edit-summary'))
                el.disabled = !disabled;
        });
    });
    finalizeBtn.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
        if (!currentId)
            return;
        const meta = {};
        inputs.forEach((el) => {
            const key = fieldMap[el.id];
            if (!key || key === 'summary')
                return;
            const v = el.value.trim();
            if (v)
                meta[key] = v;
        });
        try {
            const resp = yield fetch(`/files/${currentId}/finalize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metadata: meta, confirm: true }),
            });
            if (!resp.ok)
                throw new Error();
            closeModal(metadataModal);
            hidePreview();
            form.reset();
            progress.value = 0;
            refreshFiles();
            refreshFolderTree();
        }
        catch (_a) {
            alert('Ошибка финализации');
        }
    }));
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
                            openPreviewModal(finalData);
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
                    openPreviewModal(result);
                }
            }
            else {
                alert('Ошибка загрузки');
            }
        };
        xhr.send(data);
    });
    askAiBtn.addEventListener('click', () => {
        if (!currentId)
            return;
        openChatModal({ id: currentId });
    });
    document.addEventListener('chat-updated', (ev) => {
        const detail = ev.detail;
        if ((detail === null || detail === void 0 ? void 0 : detail.id) === currentId) {
            renderDialog(previewDialog, undefined, undefined, detail.history);
        }
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && missingModal.style.display === 'flex') {
            missingModal.style.display = 'none';
        }
    });
}
function openPreviewModal(result) {
    var _a;
    currentId = result.id;
    openMetadataModal({ id: result.id, metadata: result.metadata });
    previewDialog.style.display = 'block';
    textPreview.style.display = 'block';
    buttonsWrap.style.display = 'flex';
    renderDialog(previewDialog, result.prompt, result.raw_response, result.chat_history);
    textPreview.value = ((_a = result.metadata) === null || _a === void 0 ? void 0 : _a.extracted_text) || '';
    const saveBtn = editForm.querySelector('button[type="submit"]');
    saveBtn.style.display = 'none';
    inputs.forEach((el) => (el.disabled = true));
}
