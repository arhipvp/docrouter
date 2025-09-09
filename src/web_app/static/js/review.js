import { renderDialog } from '../dist/uploadForm.js';

function getFileId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

document.addEventListener('DOMContentLoaded', () => {
  const id = getFileId();
  if (!id) {
    return;
  }

  const suggestedPathEl = document.getElementById('suggested-path');
  const missingListEl = document.getElementById('missing-list');
  const commentEl = document.getElementById('comment');
  const dialogEl = document.getElementById('review-dialog');
  const confirmBtn = document.getElementById('confirm-btn');
  const commentBtn = document.getElementById('comment-btn');

  async function loadDetails() {
    try {
      const resp = await fetch(`/files/${id}/details`);
      if (!resp.ok) return;
      const data = await resp.json();
      if (suggestedPathEl) {
        suggestedPathEl.textContent = data.suggested_path || '';
      }
      if (missingListEl) {
        missingListEl.innerHTML = '';
        (data.missing || []).forEach((path) => {
          const li = document.createElement('li');
          li.textContent = path;
          missingListEl.appendChild(li);
        });
      }
      if (dialogEl) {
        renderDialog(
          dialogEl,
          data.prompt,
          data.raw_response,
          data.chat_history,
          data.review_comment,
          data.created_path
        );
      }
    } catch {
      // ignore
    }
  }

  confirmBtn?.addEventListener('click', async () => {
    try {
      await fetch(`/files/${id}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true }),
      });
      await fetch('/files?force=1');
      if (window.opener) {
        window.opener.location.reload();
      }
    } catch {
      // ignore
    }
  });

  commentBtn?.addEventListener('click', async () => {
    const comment = commentEl?.value.trim();
    if (!comment) return;
    try {
      const resp = await fetch(`/files/${id}/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment }),
      });
      if (!resp.ok) return;
      const data = await resp.json();
      if (dialogEl) {
        renderDialog(
          dialogEl,
          data.prompt,
          data.raw_response,
          data.chat_history,
          data.review_comment,
          data.created_path
        );
      }
      if (commentEl) {
        commentEl.value = '';
      }
    } catch {
      // ignore
    }
  });

  loadDetails();
});
