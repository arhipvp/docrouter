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
let chatModal;
let chatHistory;
let chatForm;
let chatInput;
let currentChatId = null;
let lastFocused = null;
export function setupChat() {
    chatModal = document.getElementById('chat-modal');
    chatHistory = document.getElementById('chat-history');
    chatForm = document.getElementById('chat-form');
    chatInput = document.getElementById('chat-input');
    const closeBtn = chatModal.querySelector('.modal__close');
    closeBtn === null || closeBtn === void 0 ? void 0 : closeBtn.addEventListener('click', closeChat);
    chatForm === null || chatForm === void 0 ? void 0 : chatForm.addEventListener('submit', (e) => __awaiter(this, void 0, void 0, function* () {
        e.preventDefault();
        if (!currentChatId || !chatInput)
            return;
        const msg = chatInput.value.trim();
        if (!msg)
            return;
        try {
            const resp = yield apiRequest(`/chat/${currentChatId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg }),
            });
            const data = (yield resp.json());
            renderChat(data.chat_history);
            chatInput.value = '';
            document.dispatchEvent(new CustomEvent('chat-updated', {
                detail: { id: currentChatId, history: data.chat_history },
            }));
        }
        catch (_a) {
            showNotification('Ошибка отправки сообщения');
        }
    }));
}
function renderChat(history, translatedText, translationLang, confirmed) {
    chatHistory.innerHTML = '';
    const roleLabels = {
        user: 'user',
        assistant: 'assistant',
        reviewer: 'reviewer',
        system: 'system',
    };
    history.forEach((msg) => {
        const div = document.createElement('div');
        div.textContent = `${roleLabels[msg.role]}: ${msg.message}`;
        chatHistory.appendChild(div);
    });
    if (translatedText) {
        const transDiv = document.createElement('div');
        transDiv.className = 'chat-translation';
        const langLabel = translationLang ? ` (${translationLang})` : '';
        transDiv.textContent = `Перевод${langLabel}: ${translatedText}`;
        chatHistory.appendChild(transDiv);
    }
    if (typeof confirmed === 'boolean') {
        const confDiv = document.createElement('div');
        confDiv.className = 'chat-confirmed';
        confDiv.textContent = confirmed ? 'Путь подтверждён' : 'Путь не подтверждён';
        chatHistory.appendChild(confDiv);
    }
}
export function openChatModal(fileOrId, history) {
    return __awaiter(this, void 0, void 0, function* () {
        let translatedText;
        let translationLang;
        let confirmed;
        if (typeof fileOrId === 'string') {
            currentChatId = fileOrId;
        }
        else {
            currentChatId = fileOrId.id;
            const fileStatus = fileOrId.status;
            if (fileStatus === 'finalized' || fileStatus === 'rejected') {
                showNotification('Чат недоступен для финализированных или отклонённых файлов');
                return;
            }
            history = fileOrId.chat_history && fileOrId.chat_history.length ? fileOrId.chat_history : history;
            translatedText = fileOrId.translated_text;
            translationLang = fileOrId.translation_lang;
            confirmed = fileOrId.confirmed;
        }
        const hist = history && history.length ? history : null;
        if (hist) {
            renderChat(hist, translatedText, translationLang, confirmed);
            document.dispatchEvent(new CustomEvent('chat-updated', { detail: { id: currentChatId, history: hist } }));
            openModal(chatModal);
            return;
        }
        if (!currentChatId)
            return;
        try {
            const resp = yield apiRequest(`/files/${currentChatId}/details`);
            const data = yield resp.json();
            if (data.status === 'finalized' || data.status === 'rejected') {
                showNotification('Чат недоступен для финализированных или отклонённых файлов');
                return;
            }
            const h = data.chat_history || [];
            renderChat(h, data.translated_text, data.translation_lang, data.confirmed);
            document.dispatchEvent(new CustomEvent('chat-updated', { detail: { id: currentChatId, history: h } }));
        }
        catch (_a) {
            renderChat([]);
            showNotification('Не удалось загрузить чат');
        }
        openModal(chatModal);
    });
}
export function closeChat() {
    closeModal(chatModal);
    currentChatId = null;
}
function openModal(modal) {
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
            closeChat();
        }
    };
    modal.addEventListener('keydown', handleKeydown);
    modal._handleKeydown = handleKeydown;
}
function closeModal(modal) {
    modal.style.display = 'none';
    const handler = modal._handleKeydown;
    if (handler && typeof modal.removeEventListener === 'function') {
        modal.removeEventListener('keydown', handler);
    }
    modal._handleKeydown = null;
    lastFocused === null || lastFocused === void 0 ? void 0 : lastFocused.focus();
    lastFocused = null;
}
