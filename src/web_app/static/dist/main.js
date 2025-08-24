import { setupUpload } from './upload.js';
import { setupFiles, refreshFiles } from './files.js';
import { setupFolders, refreshFolderTree } from './folders.js';
import { setupChat } from './chat.js';
document.addEventListener('DOMContentLoaded', () => {
    setupUpload();
    setupFiles();
    setupFolders();
    setupChat();
    refreshFiles();
    refreshFolderTree();
});
