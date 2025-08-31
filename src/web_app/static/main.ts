import { setupUpload } from './upload.js'; // orchestrates upload modules
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
