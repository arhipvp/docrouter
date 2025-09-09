var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { refreshFiles, openMetadataModal, openModal, closeModal } from './files.js';
import { refreshFolderTree } from './folders.js';
import { openChatModal } from './chat.js';
export let aiExchange;
let metadataModal;
let editForm;
let previewDialog;
let textPreview;
let buttonsWrap;
let rerunOcrBtn;
let regenerateBtn;
let editBtn;
let finalizeBtn;
let askAiBtn;
let currentId = null;
let currentFile = null;
let inputs;
let stepIndicator;
let finalizeModal;
let finalizeConfirm;
let finalizeCancel;
let currentStep = 1;
const fieldMap = {
    'edit-category': 'category',
    'edit-subcategory': 'subcategory',
    'edit-issuer': 'issuer',
    'edit-date': 'date',
    'edit-name': 'suggested_name',
    'edit-description': 'description',
    'edit-summary': 'summary',
};
function updateStep(step) {
    currentStep = step;
    if (!stepIndicator)
        return;
    const steps = stepIndicator.querySelectorAll('.step');
    steps.forEach((el) => {
        const s = Number(el.dataset.step || '0');
        el.classList.toggle('active', s === step);
        el.classList.toggle('completed', s < step);
    });
}
export function renderDialog(container, prompt, response, history, reviewComment, createdPath) {
    container.innerHTML = '';
    if (history && history.length) {
        history.forEach((msg) => {
            const div = document.createElement('div');
            div.className = `ai-message ${msg.role === 'user' ? 'user' : 'assistant'}`;
            div.textContent = msg.message;
            container.appendChild(div);
        });
        if (reviewComment) {
            const commentDiv = document.createElement('div');
            commentDiv.className = 'ai-message reviewer';
            commentDiv.textContent = reviewComment;
            container.appendChild(commentDiv);
        }
        if (createdPath) {
            const pathDiv = document.createElement('div');
            pathDiv.className = 'ai-message system';
            pathDiv.textContent = createdPath;
            container.appendChild(pathDiv);
        }
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
    if (reviewComment) {
        const commentDiv = document.createElement('div');
        commentDiv.className = 'ai-message reviewer';
        commentDiv.textContent = reviewComment;
        container.appendChild(commentDiv);
    }
    if (createdPath) {
        const pathDiv = document.createElement('div');
        pathDiv.className = 'ai-message system';
        pathDiv.textContent = createdPath;
        container.appendChild(pathDiv);
    }
}
export function setupUploadForm() {
    var _a;
    const form = document.querySelector('form');
    const progress = document.getElementById('upload-progress');
    aiExchange = document.getElementById('ai-exchange');
    const container = (document.querySelector('.app__container') || document.querySelector('.container'));
    if (container) {
        stepIndicator = document.createElement('div');
        stepIndicator.className = 'step-indicator';
        ['Выбор файлов', 'Предпросмотр', 'Финализация'].forEach((t, i) => {
            const el = document.createElement('div');
            el.className = 'step';
            el.dataset.step = String(i + 1);
            el.textContent = `${i + 1}. ${t}`;
            stepIndicator.appendChild(el);
        });
        container.insertBefore(stepIndicator, form);
        updateStep(1);
    }
    const missingModal = document.getElementById('missing-modal');
    const missingList = document.getElementById('missing-list');
    const missingConfirm = document.getElementById('missing-confirm');
    const missingCancel = document.getElementById('missing-cancel');
    const missingDialog = document.getElementById('missing-dialog');
    const suggestedPath = document.getElementById('suggested-path');
    metadataModal = document.getElementById('metadata-modal');
    editForm = document.getElementById('edit-form');
    finalizeModal = document.createElement('div');
    finalizeModal.id = 'finalize-modal';
    finalizeModal.className = 'modal confirm-modal';
    finalizeModal.innerHTML = `
    <div class="modal__content">
      <p>Финализировать документ?</p>
      <div class="modal__buttons">
        <button id="finalize-confirm">Да</button>
        <button id="finalize-cancel" type="button">Отмена</button>
      </div>
    </div>`;
    (_a = (document.body || container)) === null || _a === void 0 ? void 0 : _a.appendChild(finalizeModal);
    finalizeConfirm = finalizeModal.querySelector('#finalize-confirm');
    finalizeCancel = finalizeModal.querySelector('#finalize-cancel');
    finalizeCancel.addEventListener('click', () => closeModal(finalizeModal));
    const modalContent = metadataModal.querySelector('.modal__content');
    previewDialog = document.createElement('div');
    previewDialog.className = 'ai-dialog';
    previewDialog.style.display = 'none';
    modalContent.insertBefore(previewDialog, editForm);
    textPreview = document.createElement('textarea');
    textPreview.readOnly = true;
    textPreview.style.display = 'none';
    modalContent.insertBefore(textPreview, editForm);
    rerunOcrBtn = document.createElement('button');
    rerunOcrBtn.type = 'button';
    rerunOcrBtn.textContent = 'Пересканировать';
    rerunOcrBtn.style.display = 'none';
    modalContent.insertBefore(rerunOcrBtn, editForm);
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
        rerunOcrBtn.style.display = 'none';
        buttonsWrap.style.display = 'none';
        saveBtn.style.display = '';
        inputs.forEach((el) => (el.disabled = false));
        currentId = null;
        currentFile = null;
    };
    const metadataClose = metadataModal.querySelector('.modal__close');
    metadataClose.addEventListener('click', () => {
        hidePreview();
        updateStep(1);
    });
    regenerateBtn.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
        if (!currentId)
            return;
        try {
            const resp = yield fetch(`/files/${currentId}/regenerate`, {
                method: 'POST',
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
    rerunOcrBtn.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
        if (!currentId)
            return;
        const langSelect = document.getElementById('language');
        const psmInput = document.getElementById('psm');
        const language = (langSelect === null || langSelect === void 0 ? void 0 : langSelect.value) || 'eng';
        const psm = parseInt((psmInput === null || psmInput === void 0 ? void 0 : psmInput.value) || '3', 10);
        try {
            const resp = yield fetch(`/files/${currentId}/rerun_ocr`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language, psm }),
            });
            if (!resp.ok)
                throw new Error();
            const data = yield resp.json();
            textPreview.value = data.extracted_text || '';
            if (currentFile === null || currentFile === void 0 ? void 0 : currentFile.metadata) {
                currentFile.metadata.extracted_text = data.extracted_text;
            }
        }
        catch (_a) {
            alert('Ошибка пересканирования');
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
    finalizeBtn.addEventListener('click', () => {
        if (!currentId)
            return;
        openModal(finalizeModal);
    });
    finalizeConfirm.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
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
            closeModal(finalizeModal);
            closeModal(metadataModal);
            hidePreview();
            form.reset();
            progress.value = 0;
            refreshFiles();
            refreshFolderTree();
            updateStep(3);
            setTimeout(() => updateStep(1), 500);
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
                    renderDialog(missingDialog, result.prompt, result.raw_response, result.chat_history, result.review_comment, result.created_path);
                    missingModal.style.display = 'flex';
                    updateStep(2);
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
                        var _a;
                        try {
                            yield fetch(`/files/${result.id}`, { method: 'DELETE' });
                        }
                        catch (_b) {
                            // ignore errors, просто закрываем модалку
                        }
                        missingModal.style.display = 'none';
                        (_a = document.querySelector(`#files tr[data-id="${result.id}"]`)) === null || _a === void 0 ? void 0 : _a.remove();
                        refreshFiles();
                        updateStep(1);
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
        openChatModal(currentId, currentFile === null || currentFile === void 0 ? void 0 : currentFile.chat_history);
    });
    document.addEventListener('chat-updated', (ev) => {
        const detail = ev.detail;
        if ((detail === null || detail === void 0 ? void 0 : detail.id) === currentId && currentFile) {
            currentFile.chat_history = detail.history;
            const last = detail.history[detail.history.length - 1];
            if ((last === null || last === void 0 ? void 0 : last.role) === 'assistant') {
                try {
                    const suggested = JSON.parse(last.message);
                    inputs.forEach((el) => {
                        const key = fieldMap[el.id];
                        if (key && suggested[key]) {
                            el.value = suggested[key];
                            currentFile.metadata = currentFile.metadata || {};
                            currentFile.metadata[key] = suggested[key];
                        }
                    });
                }
                catch (_a) {
                    // ответ не содержит JSON с метаданными
                }
            }
            renderDialog(previewDialog, undefined, undefined, detail.history, currentFile.review_comment, currentFile.created_path);
        }
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && missingModal.style.display === 'flex') {
            missingModal.style.display = 'none';
            updateStep(1);
        }
    });
}
function openPreviewModal(result) {
    var _a;
    currentFile = result;
    currentId = result.id;
    openMetadataModal(result);
    previewDialog.style.display = 'block';
    textPreview.style.display = 'block';
    rerunOcrBtn.style.display = 'inline-block';
    buttonsWrap.style.display = 'flex';
    updateStep(2);
    renderDialog(previewDialog, result.prompt, result.raw_response, result.chat_history, result.review_comment, result.created_path);
    textPreview.value = ((_a = result.metadata) === null || _a === void 0 ? void 0 : _a.extracted_text) || '';
    const saveBtn = editForm.querySelector('button[type="submit"]');
    saveBtn.style.display = 'none';
    inputs.forEach((el) => (el.disabled = true));
}
