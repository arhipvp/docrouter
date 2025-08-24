import { setupUpload } from './upload.js';
import { setupFolders, refreshFolderTree } from './folders.js';
import { setupChat } from './chat.js';

document.addEventListener('DOMContentLoaded', () => {
  setupUpload();
  setupFolders();
  setupChat();
  refreshFolderTree();
});
