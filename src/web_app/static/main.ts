import { setupUploadForm } from './uploadForm.js';
import { setupImageBatch } from './imageBatch.js';
import { setupImageEditor } from './imageEditor.js';
import { setupFiles, refreshFiles } from './files.js';
import { refreshFolderTree } from './folders.js';
import { setupChat } from './chat.js';

document.addEventListener('DOMContentLoaded', () => {
  setupUploadForm();
  setupImageEditor();
  setupImageBatch();
  setupFiles();
  setupChat();
  refreshFiles();
  refreshFolderTree();
});
