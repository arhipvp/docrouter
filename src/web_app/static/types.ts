export interface ChatHistory {
  role: string;
  message: string;
}

export type FileStatus = 'draft' | 'pending' | 'finalized' | 'rejected';

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
  extracted_text?: string;
}

export interface FileInfo {
  id: string;
  path?: string;
  metadata?: FileMetadata;
  status?: FileStatus;
  extracted_text?: string;
  chat_history?: ChatHistory[];
  missing?: string[];
  suggested_path?: string;
  review_comment?: string;
  prompt?: string;
  raw_response?: string;
  created_path?: string;
}

export interface UploadPendingResponse {
  status: FileStatus;
  id: string;
  suggested_path?: string;
  missing?: string[];
  review_comment?: string;
  prompt?: string;
  raw_response?: string;
  created_path?: string;
  chat_history?: ChatHistory[];
}

export interface UploadFinalResponse {
  status: FileStatus;
  id: string;
  missing?: string[];
  suggested_path?: string;
  review_comment?: string;
  prompt?: string;
  raw_response?: string;
  created_path?: string;
  chat_history?: ChatHistory[];
}

export type UploadResponse = UploadPendingResponse | UploadFinalResponse;

export interface FileEntry {
  name: string;
  path: string;
  id?: string;
}

export interface FolderNode {
  name: string;
  path: string;
  children: FolderNode[];
  files: FileEntry[];
}

export type FolderTree = FolderNode[];

export interface ImageFile {
  blob: Blob;
  name: string;
}
