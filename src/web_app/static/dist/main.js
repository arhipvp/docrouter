import { setupUpload } from './upload.js';
import { setupFiles, refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';
import { setupChat } from './chat.js';
document.addEventListener('DOMContentLoaded', () => {
    setupUpload();
    setupFiles();
    setupChat();
    refreshFiles();
    refreshFolderTree();
});
