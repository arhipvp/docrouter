import { setupUploadForm } from './uploadForm.js';
import { setupImageBatch } from './imageBatch.js';
import { setupImageEditor } from './imageEditor.js';

export function setupUpload() {
  setupUploadForm();
  setupImageEditor();
  setupImageBatch();
}
