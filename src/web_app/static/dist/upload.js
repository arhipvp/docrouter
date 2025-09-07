// upload.js
// Модуль-оркестратор + утилиты модалок (общие для uploadForm/imageBatch/imageEditor)
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
import { setupUploadForm } from './uploadForm.js';
import { setupImageBatch } from './imageBatch.js';
import { setupImageEditor } from './imageEditor.js';
import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
/**
 * Точка входа инициализации загрузки/редактирования.
 * Делегирует настройку подмодулей.
 */
export function setupUpload() {
    var _a;
    setupUploadForm();
    setupImageEditor();
    setupImageBatch();
    const textPreview = document.getElementById('text-preview');
    if (textPreview) {
        const rerunBtn = document.createElement('button');
        rerunBtn.id = 'rerun-ocr-btn';
        rerunBtn.type = 'button';
        rerunBtn.textContent = 'Пересканировать';
        (_a = textPreview.parentElement) === null || _a === void 0 ? void 0 : _a.insertBefore(rerunBtn, textPreview);
        rerunBtn.addEventListener('click', () => __awaiter(this, void 0, void 0, function* () {
            const id = textPreview.dataset.id;
            if (!id)
                return;
            const langSelect = document.getElementById('language');
            const psmInput = document.getElementById('psm');
            const language = (langSelect === null || langSelect === void 0 ? void 0 : langSelect.value) || 'eng';
            const psm = parseInt((psmInput === null || psmInput === void 0 ? void 0 : psmInput.value) || '3', 10);
            try {
                const resp = yield apiRequest(`/files/${id}/rerun_ocr`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language, psm }),
                });
                const data = yield resp.json();
                textPreview.textContent = data.extracted_text || '';
            }
            catch (_a) {
                showNotification('Ошибка пересканирования');
            }
        }));
    }
}
/**
 * Открыть модалку с фокус-трапом.
 * @param {HTMLElement} modal
 * @param {{ onEscape?: () => void }} [options]
 */
export function openModal(modal, options = {}) {
    const { onEscape } = options;
    // запомним, кто был в фокусе
    modal.__lastFocused = document.activeElement || null;
    // показать модалку
    modal.style.display = 'flex';
    // сфокусироваться на первом фокусируемом элементе
    const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    const first = focusable[0] || modal;
    if (typeof (first === null || first === void 0 ? void 0 : first.focus) === 'function')
        first.focus();
    // обработчик клавиш: Tab — цикл фокуса, Esc — закрытие
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
            if (typeof onEscape === 'function')
                onEscape();
            closeModal(modal);
        }
    };
    modal.addEventListener('keydown', handleKeydown);
    modal.__handleKeydown = handleKeydown;
}
/**
 * Закрыть модалку и вернуть фокус.
 * @param {HTMLElement} modal
 */
export function closeModal(modal) {
    modal.style.display = 'none';
    const handler = modal.__handleKeydown;
    if (handler && typeof modal.removeEventListener === 'function') {
        modal.removeEventListener('keydown', handler);
    }
    modal.__handleKeydown = null;
    const last = modal.__lastFocused;
    if (last && typeof last.focus === 'function')
        last.focus();
    modal.__lastFocused = null;
}
