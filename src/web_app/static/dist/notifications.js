export function showError(message) {
    show(message, 'error');
}
export function showInfo(message) {
    show(message, 'info');
}
function show(message, type) {
    const container = document.getElementById('notifications');
    if (!container) {
        if (type === 'error')
            console.error(message);
        else
            console.log(message);
        return;
    }
    const div = document.createElement('div');
    div.className = `notification ${type}`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => {
        if (typeof div.remove === 'function') {
            div.remove();
        }
        else if (div.parentNode && typeof div.parentNode.removeChild === 'function') {
            div.parentNode.removeChild(div);
        }
    }, 5000);
}
