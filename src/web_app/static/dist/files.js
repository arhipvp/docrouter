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
let list;
let textPreview;
let tagLanguage;
let displayLangSelect;
let previewModal;
let previewFrame;
let metadataModal;
let editForm;
let editCategory;
let editSubcategory;
let editIssuer;
let editDate;
let editName;
let nameOriginalRadio;
let nameLatinRadio;
let nameOriginalLabel;
let nameLatinLabel;
let currentEditId = null;
let displayLang = '';
export function setupFiles() {
    list = document.getElementById('files');
    textPreview = document.getElementById('text-preview');
    tagLanguage = document.getElementById('tag-language');
    displayLangSelect = document.getElementById('display-lang');
    previewModal = document.getElementById('preview-modal');
    previewFrame = document.getElementById('preview-frame');
    metadataModal = document.getElementById('metadata-modal');
    editForm = document.getElementById('edit-form');
    editCategory = document.getElementById('edit-category');
    editSubcategory = document.getElementById('edit-subcategory');
    editIssuer = document.getElementById('edit-issuer');
    editDate = document.getElementById('edit-date');
    editName = document.getElementById('edit-name');
    nameOriginalRadio = document.getElementById('name-original');
    nameLatinRadio = document.getElementById('name-latin');
    nameOriginalLabel = document.getElementById('name-original-label');
    nameLatinLabel = document.getElementById('name-latin-label');
    displayLangSelect === null || displayLangSelect === void 0 ? void 0 : displayLangSelect.addEventListener('change', () => {
        displayLang = displayLangSelect.value;
        refreshFiles();
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
                suggested_name: editName.value.trim()
            }
        };
        Object.keys(payload.metadata).forEach(k => {
            if (!payload.metadata[k])
                delete payload.metadata[k];
        });
        try {
            const resp = yield apiRequest(`/files/${currentEditId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            metadataModal.style.display = 'none';
            currentEditId = null;
            yield refreshFiles();
        }
        catch (_a) {
            showNotification('Ошибка обновления');
        }
    }));
    list.addEventListener('click', (e) => __awaiter(this, void 0, void 0, function* () {
        if (e.target.closest('a.download-link') || e.target.closest('button.edit-btn') || e.target.closest('button.chat-btn'))
            return;
        const tr = e.target.closest('tr');
        if (!tr)
            return;
        const id = tr.dataset.id;
        if (!id)
            return;
        previewFrame.src = `/preview/${id}`;
        previewModal.style.display = 'flex';
        try {
            const resp = yield apiRequest(`/files/${id}/details`);
            const data = yield resp.json();
            textPreview.textContent = data.extracted_text || '';
        }
        catch (_a) {
            textPreview.textContent = '';
            showNotification('Не удалось получить содержимое файла');
        }
    }));
    const previewClose = previewModal.querySelector('.close');
    previewClose.addEventListener('click', () => {
        previewModal.style.display = 'none';
        previewFrame.src = '';
    });
    previewModal.addEventListener('click', (e) => {
        if (e.target === previewModal) {
            previewModal.style.display = 'none';
            previewFrame.src = '';
        }
    });
    const metadataClose = metadataModal.querySelector('.close');
    metadataClose.addEventListener('click', () => {
        metadataModal.style.display = 'none';
        currentEditId = null;
    });
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape')
            return;
        if (previewModal.style.display === 'flex') {
            previewModal.style.display = 'none';
            previewFrame.src = '';
        }
        if (metadataModal.style.display === 'flex') {
            metadataModal.style.display = 'none';
            currentEditId = null;
        }
    });
    tagLanguage.addEventListener('change', refreshFiles);
    nameOriginalRadio === null || nameOriginalRadio === void 0 ? void 0 : nameOriginalRadio.addEventListener('change', () => {
        if (nameOriginalRadio.checked)
            editName.value = nameOriginalRadio.value;
    });
    nameLatinRadio === null || nameLatinRadio === void 0 ? void 0 : nameLatinRadio.addEventListener('change', () => {
        if (nameLatinRadio.checked)
            editName.value = nameLatinRadio.value;
    });
    refreshFiles();
}
export function refreshFiles() {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const resp = yield apiRequest('/files');
            const files = yield resp.json();
            list.innerHTML = '';
            files.forEach((f) => {
                var _a, _b;
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
                const statusTd = document.createElement('td');
                statusTd.textContent = f.status;
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
                actionsTd.appendChild(document.createTextNode(' '));
                actionsTd.appendChild(jsonLink);
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
                tr.appendChild(actionsTd);
                list.appendChild(tr);
            });
        }
        catch (_a) {
            showNotification('Не удалось загрузить список файлов');
        }
    });
}
function openMetadataModal(file) {
    currentEditId = file.id;
    const m = file.metadata || {};
    editCategory.value = m.category || '';
    editSubcategory.value = m.subcategory || '';
    editIssuer.value = m.issuer || '';
    editDate.value = m.date || '';
    const orig = m.suggested_name || '';
    const latin = m.suggested_name_translit || orig;
    editName.value = orig;
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
    metadataModal.style.display = 'flex';
}
