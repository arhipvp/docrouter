export function showError(message: string) {
  show(message, 'error');
}

export function showInfo(message: string) {
  show(message, 'info');
}

function show(message: string, type: 'error' | 'info') {
  const container = document.getElementById('notifications');
  if (!container) {
    if (type === 'error') console.error(message);
    else console.log(message);
    return;
  }
  const div = document.createElement('div');
  div.className = `notification ${type}`;
  div.textContent = message;
  container.appendChild(div);
  setTimeout(() => {
    if (typeof (div as any).remove === 'function') {
      (div as any).remove();
    } else if ((div as any).parentNode && typeof (div as any).parentNode.removeChild === 'function') {
      (div as any).parentNode.removeChild(div);
    }
  }, 5000);
}
