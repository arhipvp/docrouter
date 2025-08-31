// upload.js
// Модуль-оркестратор + утилиты модалок

import { setupUploadForm } from './uploadForm.js';
import { setupImageBatch } from './imageBatch.js';
import { setupImageEditor } from './imageEditor.js';

/**
 * Точка входа инициализации загрузки/редактирования.
 * Делегирует настройку подмодулей.
 */
export function setupUpload() {
  setupUploadForm();
  setupImageEditor();
  setupImageBatch();
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
  const focusable = modal.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0] || modal;
  if (typeof first?.focus === 'function') first.focus();

  // обработчик клавиш: Tab — цикл фокуса, Esc — закрытие
  const handleKeydown = (e) => {
    if (e.key === 'Tab') {
      const items = modal.querySelectorAll(
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
  if (last && typeof last.focus === 'function') last.focus();
  modal.__lastFocused = null;
}
