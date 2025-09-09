// upload.js
// Модуль-оркестратор + утилиты модалок (общие для uploadForm/imageBatch/imageEditor)

import { setupUploadForm } from './uploadForm.js';
import { setupImageBatch } from './imageBatch.js';
import { setupImageEditor } from './imageEditor.js';
import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
import type { FileInfo } from './types.js';

/**
 * Точка входа инициализации загрузки/редактирования.
 * Делегирует настройку подмодулей.
 */
export function setupUpload() {
  setupUploadForm();
  setupImageEditor();
  setupImageBatch();

  const textPreview = document.getElementById('text-preview');
  if (textPreview) {
    const rerunBtn = document.createElement('button');
    rerunBtn.id = 'rerun-ocr-btn';
    rerunBtn.type = 'button';
    rerunBtn.textContent = 'Пересканировать';
    textPreview.parentElement?.insertBefore(rerunBtn, textPreview);

    rerunBtn.addEventListener('click', async () => {
      const id = (textPreview as HTMLElement).dataset.id;
      if (!id) return;
      const langSelect = document.getElementById('language') as HTMLSelectElement | null;
      const psmInput = document.getElementById('psm') as HTMLInputElement | null;
      const language = langSelect?.value || 'eng';
      const psm = parseInt(psmInput?.value || '3', 10);
      try {
        const resp = await apiRequest(`/files/${id}/rerun_ocr`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language, psm }),
        });
        const data: FileInfo = await resp.json();
        textPreview.textContent = data.extracted_text || '';
      } catch {
        showNotification('Ошибка пересканирования');
      }
    });
  }
}

/**
 * Открыть модалку с фокус-трапом.
 * @param {HTMLElement} modal
 * @param {{ onEscape?: () => void }} [options]
 */
export function openModal(modal: HTMLElement, options: { onEscape?: () => void } = {}) {
  const { onEscape } = options;

  // запомним, кто был в фокусе
  (modal as any).__lastFocused = document.activeElement || null;

  // показать модалку
  modal.style.display = 'flex';

  // сфокусироваться на первом фокусируемом элементе
  const focusable = modal.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0] || modal;
  if (typeof first?.focus === 'function') first.focus();

  // обработчик клавиш: Tab — цикл фокуса, Esc — закрытие
  const handleKeydown = (e) => {
    if (e.key === 'Tab') {
      const items = modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!items.length) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];

      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    } else if (e.key === 'Escape') {
      if (typeof onEscape === 'function') onEscape();
      closeModal(modal);
    }
  };

  modal.addEventListener('keydown', handleKeydown);
  (modal as any).__handleKeydown = handleKeydown;
}

/**
 * Закрыть модалку и вернуть фокус.
 * @param {HTMLElement} modal
 */
export function closeModal(modal) {
  modal.style.display = 'none';

  const handler = (modal as any).__handleKeydown;
  if (handler && typeof modal.removeEventListener === 'function') {
    modal.removeEventListener('keydown', handler);
  }
  (modal as any).__handleKeydown = null;

  const last = (modal as any).__lastFocused as HTMLElement | null;
  if (last && typeof last.focus === 'function') last.focus();
  modal.__lastFocused = null;
}
