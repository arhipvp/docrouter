import { setupUpload } from './upload';
import { setupFiles, refreshFiles } from './files';
import { refreshFolderTree } from './folders';
import { setupChat } from './chat';
import './style.css';
import 'cropperjs/dist/cropper.css';

document.addEventListener('DOMContentLoaded', () => {
  setupUpload();
  setupFiles();
  setupChat();
  refreshFiles();
  refreshFolderTree();
});
