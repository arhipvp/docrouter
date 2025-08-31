var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
let chatModal;
let chatHistory;
let chatForm;
let chatInput;
let currentChatId = null;
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
        const resp = yield fetch(`/chat/${currentChatId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        if (resp.ok) {
            const data = yield resp.json();
            renderChat(data.chat_history);
            chatInput.value = '';
        }
    }));
}
function renderChat(history) {
    chatHistory.innerHTML = '';
    history.forEach((msg) => {
        const div = document.createElement('div');
        div.textContent = `${msg.role}: ${msg.message}`;
        chatHistory.appendChild(div);
    });
}
export function openChatModal(file) {
    return __awaiter(this, void 0, void 0, function* () {
        currentChatId = file.id;
        try {
            const resp = yield fetch(`/files/${file.id}/details`);
            const data = resp.ok ? yield resp.json() : {};
            renderChat(data.chat_history || []);
        }
        catch (_a) {
            renderChat([]);
        }
        chatModal.style.display = 'flex';
    });
}
export function closeChat() {
    chatModal.style.display = 'none';
    currentChatId = null;
}
