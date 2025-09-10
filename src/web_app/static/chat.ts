import { apiRequest } from './http.js';
import { showNotification } from './notify.js';
import type { ChatHistory, FileInfo, FileStatus } from './types.js';

let chatModal: HTMLElement;
let chatHistory: HTMLElement;
let chatForm: HTMLFormElement | null;
let chatInput: HTMLInputElement | null;
let currentChatId: string | null = null;
let lastFocused: HTMLElement | null = null;

export function setupChat() {
  chatModal = document.getElementById('chat-modal')!;
  chatHistory = document.getElementById('chat-history')!;
  chatForm = document.getElementById('chat-form') as HTMLFormElement;
  chatInput = document.getElementById('chat-input') as HTMLInputElement;

  const closeBtn = chatModal.querySelector('.modal__close') as HTMLElement;
  closeBtn?.addEventListener('click', closeChat);

  chatForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentChatId || !chatInput) return;

    const msg = chatInput.value.trim();
    if (!msg) return;

    try {
      const resp = await apiRequest(`/chat/${currentChatId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = (await resp.json()) as { chat_history: ChatHistory[] };
      renderChat(data.chat_history);
      chatInput.value = '';
      document.dispatchEvent(
        new CustomEvent('chat-updated', {
          detail: { id: currentChatId, history: data.chat_history },
        })
      );
    } catch {
      showNotification('Ошибка отправки сообщения');
    }
  });
}

function renderChat(
  history: ChatHistory[],
  translatedText?: string,
  translationLang?: string,
  confirmed?: boolean
) {
  chatHistory.innerHTML = '';
  const roleLabels: Record<ChatHistory['role'], string> = {
    user: 'user',
    assistant: 'assistant',
    reviewer: 'reviewer',
    system: 'system',
  };
  history.forEach((msg: ChatHistory) => {
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

export async function openChatModal(
  fileOrId: FileInfo | string,
  history?: ChatHistory[]
) {
  let translatedText: string | undefined;
  let translationLang: string | undefined;
  let confirmed: boolean | undefined;
  if (typeof fileOrId === 'string') {
    currentChatId = fileOrId;
  } else {
    currentChatId = fileOrId.id;
    const fileStatus: FileStatus | undefined = fileOrId.status;
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
    document.dispatchEvent(
      new CustomEvent('chat-updated', { detail: { id: currentChatId, history: hist } })
    );
    openModal(chatModal);
    return;
  }
  if (!currentChatId) return;
  try {
    const resp = await apiRequest(`/files/${currentChatId}/details`);
    const data: FileInfo = await resp.json();
    if (data.status === 'finalized' || data.status === 'rejected') {
      showNotification('Чат недоступен для финализированных или отклонённых файлов');
      return;
    }
    const h = data.chat_history || [];
    renderChat(h, data.translated_text, data.translation_lang, data.confirmed);
    document.dispatchEvent(
      new CustomEvent('chat-updated', { detail: { id: currentChatId, history: h } })
    );
  } catch {
    renderChat([]);
    showNotification('Не удалось загрузить чат');
  }
  openModal(chatModal);
}

export function closeChat() {
  closeModal(chatModal);
  currentChatId = null;
}

function openModal(modal: HTMLElement) {
  lastFocused = document.activeElement as HTMLElement;
  modal.style.display = 'flex';

  const focusable = modal.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = (focusable[0] || modal) as HTMLElement;
  if (typeof (first as any).focus === 'function') (first as any).focus();

  const handleKeydown = (e: KeyboardEvent) => {
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
      closeChat();
    }
  };

  modal.addEventListener('keydown', handleKeydown);
  (modal as any)._handleKeydown = handleKeydown;
}

function closeModal(modal: HTMLElement) {
  modal.style.display = 'none';

  const handler = (modal as any)._handleKeydown;
  if (handler && typeof (modal as any).removeEventListener === 'function') {
    modal.removeEventListener('keydown', handler);
  }
  (modal as any)._handleKeydown = null;

  lastFocused?.focus();
  lastFocused = null;
}
