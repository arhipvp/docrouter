export interface ChatHistory {
  role: string;
  message: string;
}

export interface FileMetadata {
  category?: string;
  subcategory?: string;
  issuer?: string;
  date?: string;
  tags_ru?: string[];
  tags_en?: string[];
  suggested_name?: string;
  suggested_name_translit?: string;
  description?: string;
  summary?: string;
}

export interface FileInfo {
  id: string;
  path?: string;
  metadata?: FileMetadata;
  status?: string;
  extracted_text?: string;
  chat_history?: ChatHistory[];
}

export interface UploadPendingResponse {
  status: 'pending';
  id: string;
  suggested_path?: string;
  missing?: string[];
  prompt?: string;
  raw_response?: string;
}

export interface UploadFinalResponse {
  status: string;
  prompt?: string;
  raw_response?: string;
}

export type UploadResponse = UploadPendingResponse | UploadFinalResponse;

export interface FolderTree {
  [key: string]: FolderTree;
}

export interface ImageFile {
  blob: Blob;
  name: string;
}
