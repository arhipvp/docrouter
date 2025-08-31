import type { ChatHistory, FileInfo } from './types.js';

let chatModal: HTMLElement;
let chatHistory: HTMLElement;
let chatForm: HTMLFormElement | null;
let chatInput: HTMLInputElement | null;
let currentChatId: string | null = null;

export function setupChat() {
  chatModal = document.getElementById('chat-modal')!;
  chatHistory = document.getElementById('chat-history')!;
  chatForm = document.getElementById('chat-form') as HTMLFormElement;
  chatInput = document.getElementById('chat-input') as HTMLInputElement;
  const closeBtn = chatModal.querySelector('.close') as HTMLElement;
  closeBtn?.addEventListener('click', closeChat);

  chatForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentChatId || !chatInput) return;
    const msg = chatInput.value.trim();
    if (!msg) return;
    const resp = await fetch(`/chat/${currentChatId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    if (resp.ok) {
      const data = await resp.json() as { chat_history: ChatHistory[] };
      renderChat(data.chat_history);
      chatInput.value = '';
    }
  });
}

function renderChat(history: ChatHistory[]) {
  chatHistory.innerHTML = '';
  history.forEach((msg: ChatHistory) => {
    const div = document.createElement('div');
    div.textContent = `${msg.role}: ${msg.message}`;
    chatHistory.appendChild(div);
  });
}

export async function openChatModal(file: FileInfo) {
  currentChatId = file.id;
  try {
    const resp = await fetch(`/files/${file.id}/details`);
    const data: FileInfo = resp.ok ? await resp.json() : {};
    renderChat(data.chat_history || []);
  } catch {
    renderChat([]);
  }
  chatModal.style.display = 'flex';
}

export function closeChat() {
  chatModal.style.display = 'none';
  currentChatId = null;
}
