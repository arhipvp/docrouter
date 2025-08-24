import { setupUpload } from './upload';
import { setupFolders, refreshFolderTree } from './folders';
import { setupChat } from './chat';

document.addEventListener('DOMContentLoaded', () => {
  setupUpload();
  setupFolders();
  setupChat();
  refreshFolderTree();
});
