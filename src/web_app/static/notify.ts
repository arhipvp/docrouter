let container: HTMLElement | null = null;

export function showNotification(message: string) {
  if (typeof document === 'undefined' || !document.body) {
    console.error(message);
    return;
  }
  if (!container) {
    container = document.createElement('div');
    container.style.position = 'fixed';
    container.style.top = '10px';
    container.style.right = '10px';
    container.style.zIndex = '1000';
    document.body.appendChild(container);
  }
  const note = document.createElement('div');
  note.textContent = message;
  note.style.background = '#f44336';
  note.style.color = '#fff';
  note.style.padding = '0.5em 1em';
  note.style.marginTop = '0.5em';
  note.style.borderRadius = '4px';
  container.appendChild(note);
  setTimeout(() => {
    note.remove();
    if (container && container.childElementCount === 0) {
      container.remove();
      container = null;
    }
  }, 3000);
}
