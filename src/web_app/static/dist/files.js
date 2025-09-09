var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { openChatModal } from './chat.js';
import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
import { refreshFolderTree } from './folders.js';
import { aiExchange, renderDialog } from './uploadForm.js';
let list;
let textPreview;
let tagLanguage;
let displayLangSelect;
let searchInput;
let previewModal;
let previewFrame;
let metadataModal;
let editForm;
let editCategory;
let editSubcategory;
let editIssuer;
let editDate;
let editPerson;
let editDocType;
let editLanguage;
let editNeedsFolder;
let editNewNameTranslit;
let editName;
let editDescription;
let editSummary;
let nameOriginalRadio;
let nameLatinRadio;
let nameOriginalLabel;
let nameLatinLabel;
let clarifyBtn;
let currentEditId = null;
let displayLang = '';
let lastFocused = null;
export function setupFiles() {
    list = document.getElementById('files');
    // Предотвращаем редактирование содержимого таблицы,
    // но сохраняем возможность выделения и копирования текста
    list.addEventListener('beforeinput', (e) => {
        const target = e.target;
        if (target.tagName === 'TD')
            e.preventDefault();
    });
    textPreview = document.getElementById('text-preview');
    tagLanguage = document.getElementById('tag-language');
    displayLangSelect = document.getElementById('display-lang');
    searchInput = document.getElementById('search-input');
    previewModal = document.getElementById('preview-modal');
    previewFrame = document.getElementById('preview-frame');
    metadataModal = document.getElementById('metadata-modal');
    editForm = document.getElementById('edit-form');
    editCategory = document.getElementById('edit-category');
    editSubcategory = document.getElementById('edit-subcategory');
    editIssuer = document.getElementById('edit-issuer');
    editDate = document.getElementById('edit-date');
    editPerson = document.getElementById('edit-person');
    editDocType = document.getElementById('edit-doc-type');
    editLanguage = document.getElementById('edit-language');
    editNeedsFolder = document.getElementById('edit-needs-new-folder');
    editNewNameTranslit = document.getElementById('edit-new-name-translit');
    editName = document.getElementById('edit-name');
    editDescription = document.getElementById('edit-description');
    editSummary = document.getElementById('edit-summary');
    nameOriginalRadio = document.getElementById('name-original');
    nameLatinRadio = document.getElementById('name-latin');
    nameOriginalLabel = document.getElementById('name-original-label');
    nameLatinLabel = document.getElementById('name-latin-label');
    clarifyBtn = document.getElementById('clarify-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    displayLangSelect === null || displayLangSelect === void 0 ? void 0 : displayLangSelect.addEventListener('change', () => {
        displayLang = displayLangSelect.value;
        refreshFiles(false, (searchInput === null || searchInput === void 0 ? void 0 : searchInput.value.trim()) || '');
    });
    editForm.addEventListener('submit', (e) => __awaiter(this, void 0, void 0, function* () {
        e.preventDefault();
        if (!currentEditId)
            return;
        const payload = {
            metadata: {
                category: editCategory.value.trim(),
                subcategory: editSubcategory.value.trim(),
                issuer: editIssuer.value.trim(),
                date: editDate.value,
                person: editPerson === null || editPerson === void 0 ? void 0 : editPerson.value.trim(),
                doc_type: editDocType === null || editDocType === void 0 ? void 0 : editDocType.value.trim(),
                language: editLanguage === null || editLanguage === void 0 ? void 0 : editLanguage.value.trim(),
                new_name_translit: editNewNameTranslit === null || editNewNameTranslit === void 0 ? void 0 : editNewNameTranslit.value.trim(),
                needs_new_folder: (editNeedsFolder === null || editNeedsFolder === void 0 ? void 0 : editNeedsFolder.checked) ? true : undefined,
                suggested_name: editName.value.trim(),
                description: editDescription.value.trim(),
            },
        };
        Object.keys(payload.metadata).forEach((k) => {
            if (!payload.metadata[k])
                delete payload.metadata[k];
        });
        try {
            const resp = yield apiRequest(`/files/${currentEditId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!resp.ok)
                throw new Error();
            const data = yield resp.json();
            renderDialog(aiExchange, data.prompt, data.raw_response);
            closeModal(metadataModal);
            currentEditId = null;
            yield refreshFiles();
        }
        catch (_a) {
            showNotification('Ошибка обновления');
        }
    }));
    clarifyBtn === null || clarifyBtn === void 0 ? void 0 : clarifyBtn.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
        if (!currentEditId)
            return;
        const message = editDescription.value.trim();
        try {
            const resp = yield apiRequest(`/files/${currentEditId}/comment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message }),
            });
            if (!resp.ok)
                throw new Error();
            const data = yield resp.json();
            populateMetadataForm(data);
            renderDialog(aiExchange, data.prompt, data.raw_response);
        }
        catch (_a) {
            showNotification('Ошибка запроса');
        }
    }));
    list.addEventListener('click', (e) => __awaiter(this, void 0, void 0, function* () {
        const target = e.target;
        if (target.closest('a.download-link') ||
            target.closest('button.edit-btn') ||
            target.closest('button.chat-btn'))
            return;
        const tr = target.closest('tr');
        if (!tr)
            return;
        const id = tr.dataset.id;
        if (!id)
            return;
        previewFrame.src = `/preview/${id}`;
        openModal(previewModal);
        try {
            const resp = yield apiRequest(`/files/${id}/details`);
            if (!resp.ok)
                throw new Error();
            const data = yield resp.json();
            textPreview.textContent = data.extracted_text || '';
            textPreview.dataset.id = id;
        }
        catch (_a) {
            textPreview.textContent = '';
            showNotification('Не удалось получить содержимое файла');
        }
    }));
    const previewClose = previewModal.querySelector('.modal__close');
    previewClose.addEventListener('click', () => {
        closeModal(previewModal);
        previewFrame.src = '';
    });
    previewModal.addEventListener('click', (e) => {
        if (e.target === previewModal) {
            closeModal(previewModal);
            previewFrame.src = '';
        }
    });
    const metadataClose = metadataModal.querySelector('.modal__close');
    metadataClose.addEventListener('click', () => {
        closeModal(metadataModal);
        currentEditId = null;
    });
    tagLanguage.addEventListener('change', () => refreshFiles(false, (searchInput === null || searchInput === void 0 ? void 0 : searchInput.value.trim()) || ''));
    nameOriginalRadio === null || nameOriginalRadio === void 0 ? void 0 : nameOriginalRadio.addEventListener('change', () => {
        if (nameOriginalRadio.checked)
            editName.value = nameOriginalRadio.value;
    });
    nameLatinRadio === null || nameLatinRadio === void 0 ? void 0 : nameLatinRadio.addEventListener('change', () => {
        if (nameLatinRadio.checked)
            editName.value = nameLatinRadio.value;
    });
    refreshBtn === null || refreshBtn === void 0 ? void 0 : refreshBtn.addEventListener('click', () => {
        refreshFiles(true, (searchInput === null || searchInput === void 0 ? void 0 : searchInput.value.trim()) || '');
        refreshFolderTree();
    });
    searchInput === null || searchInput === void 0 ? void 0 : searchInput.addEventListener('input', () => {
        const term = searchInput.value.trim();
        if (term)
            refreshFiles(false, term);
        else
            refreshFiles();
    });
    refreshFiles();
}
export function refreshFiles() {
    return __awaiter(this, arguments, void 0, function* (force = false, q = '') {
        try {
            const url = q
                ? `/files/search?q=${encodeURIComponent(q)}`
                : `/files${force ? '?force=1' : ''}`;
            const resp = yield apiRequest(url);
            if (!resp.ok)
                throw new Error();
            const files = yield resp.json();
            list.innerHTML = '';
            files.forEach((f) => {
                var _a, _b, _c, _d;
                const tr = document.createElement('tr');
                tr.dataset.id = f.id;
                const pathTd = document.createElement('td');
                pathTd.textContent = f.path || '';
                tr.appendChild(pathTd);
                const categoryTd = document.createElement('td');
                const category = (_b = (_a = f.metadata) === null || _a === void 0 ? void 0 : _a.category) !== null && _b !== void 0 ? _b : '';
                categoryTd.textContent = category;
                tr.appendChild(categoryTd);
                const tagsTd = document.createElement('td');
                const lang = tagLanguage.value;
                const tags = f.metadata ? (lang === 'ru' ? f.metadata.tags_ru : f.metadata.tags_en) : [];
                const tagsText = Array.isArray(tags) ? tags.join(', ') : '';
                tagsTd.textContent = tagsText;
                tr.appendChild(tagsTd);
                const summaryTd = document.createElement('td');
                const summary = ((_c = f.metadata) === null || _c === void 0 ? void 0 : _c.summary) ? f.metadata.summary.substring(0, 100) : '';
                summaryTd.textContent = summary;
                summaryTd.classList.add('summary');
                tr.appendChild(summaryTd);
                const descTd = document.createElement('td');
                const desc = ((_d = f.metadata) === null || _d === void 0 ? void 0 : _d.description) ? f.metadata.description.substring(0, 100) : '';
                descTd.textContent = desc;
                descTd.classList.add('description');
                tr.appendChild(descTd);
                const statusTd = document.createElement('td');
                const status = f.status;
                statusTd.textContent = status || '';
                tr.appendChild(statusTd);
                const actionsTd = document.createElement('td');
                const langParam = displayLang ? `?lang=${encodeURIComponent(displayLang)}` : '';
                const link = document.createElement('a');
                link.href = `/download/${f.id}${langParam}`;
                link.textContent = 'скачать';
                link.classList.add('download-link');
                actionsTd.appendChild(link);
                const jsonLink = document.createElement('a');
                jsonLink.href = `/files/${f.id}/details`;
                jsonLink.textContent = 'json';
                jsonLink.target = '_blank';
                jsonLink.classList.add('meta-link');
                actionsTd.appendChild(document.createTextNode(' '));
                actionsTd.appendChild(jsonLink);
                const textLink = document.createElement('a');
                textLink.href = `/files/${f.id}/text`;
                textLink.textContent = 'текст';
                textLink.target = '_blank';
                textLink.classList.add('meta-link');
                actionsTd.appendChild(document.createTextNode(' '));
                actionsTd.appendChild(textLink);
                const editBtn = document.createElement('button');
                editBtn.type = 'button';
                editBtn.textContent = 'Редактировать';
                editBtn.classList.add('edit-btn');
                editBtn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    openMetadataModal(f);
                });
                actionsTd.appendChild(editBtn);
                const chatBtn = document.createElement('button');
                chatBtn.type = 'button';
                chatBtn.textContent = 'Чат';
                chatBtn.classList.add('chat-btn');
                chatBtn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    openChatModal(f);
                });
                actionsTd.appendChild(chatBtn);
                const regenBtn = document.createElement('button');
                regenBtn.type = 'button';
                regenBtn.textContent = 'Перегенерировать';
                regenBtn.addEventListener('click', (ev) => __awaiter(this, void 0, void 0, function* () {
                    ev.stopPropagation();
                    try {
                        yield apiRequest(`/files/${f.id}/regenerate`, { method: 'POST' });
                        showNotification('Метаданные обновлены');
                        yield refreshFiles();
                    }
                    catch (_a) {
                        showNotification('Ошибка генерации');
                    }
                }));
                actionsTd.appendChild(regenBtn);
                tr.appendChild(actionsTd);
                list.appendChild(tr);
            });
        }
        catch (_a) {
            showNotification('Не удалось загрузить список файлов');
        }
    });
}
function populateMetadataForm(file) {
    const m = file.metadata || {};
    editCategory.value = m.category || '';
    editSubcategory.value = m.subcategory || '';
    editIssuer.value = m.issuer || '';
    editPerson && (editPerson.value = m.person || '');
    editDocType && (editDocType.value = m.doc_type || '');
    editLanguage && (editLanguage.value = m.language || '');
    editNeedsFolder && (editNeedsFolder.checked = m.needs_new_folder || false);
    editNewNameTranslit && (editNewNameTranslit.value = m.new_name_translit || '');
    editDate.value = m.date || '';
    const orig = m.suggested_name || '';
    const latin = m.suggested_name_translit || orig;
    editName.value = orig;
    editDescription.value = m.description || '';
    editSummary.value = m.summary || '';
    if (nameOriginalRadio) {
        nameOriginalRadio.value = orig;
        nameOriginalRadio.checked = true;
    }
    if (nameLatinRadio) {
        nameLatinRadio.value = latin;
        nameLatinRadio.checked = false;
    }
    if (nameOriginalLabel)
        nameOriginalLabel.textContent = orig;
    if (nameLatinLabel)
        nameLatinLabel.textContent = latin;
}
export function openMetadataModal(file) {
    currentEditId = file.id;
    populateMetadataForm(file);
    openModal(metadataModal);
}
export function openModal(modal) {
    lastFocused = document.activeElement;
    modal.style.display = 'flex';
    const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    const first = (focusable[0] || modal);
    if (typeof first.focus === 'function')
        first.focus();
    const handleKeydown = (e) => {
        if (e.key === 'Tab') {
            const items = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (!items.length)
                return;
            const firstEl = items[0];
            const lastEl = items[items.length - 1];
            if (e.shiftKey && document.activeElement === firstEl) {
                e.preventDefault();
                lastEl.focus();
            }
            else if (!e.shiftKey && document.activeElement === lastEl) {
                e.preventDefault();
                firstEl.focus();
            }
        }
        else if (e.key === 'Escape') {
            closeModal(modal);
            if (modal === previewModal)
                previewFrame.src = '';
            if (modal === metadataModal)
                currentEditId = null;
        }
    };
    modal.addEventListener('keydown', handleKeydown);
    modal._handleKeydown = handleKeydown;
}
export function closeModal(modal) {
    modal.style.display = 'none';
    const handler = modal._handleKeydown;
    if (handler && typeof modal.removeEventListener === 'function') {
        modal.removeEventListener('keydown', handler);
    }
    modal._handleKeydown = null;
    lastFocused === null || lastFocused === void 0 ? void 0 : lastFocused.focus();
    lastFocused = null;
}
