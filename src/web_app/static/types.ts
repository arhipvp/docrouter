export interface ChatHistory {
  role: 'user' | 'assistant' | 'reviewer' | 'system';
  message: string;
}

export type FileStatus = 'draft' | 'pending' | 'finalized' | 'rejected' | 'missing';

export interface FileMetadata {
  category?: string;
  subcategory?: string;
  issuer?: string;
  person?: string;
  doc_type?: string;
  date?: string;
  date_of_birth?: string;
  expiration_date?: string;
  passport_number?: string;
  amount?: string;
  counterparty?: string;
  document_number?: string;
  due_date?: string;
  currency?: string;
  tags?: string[];
  tags_ru?: string[];
  tags_en?: string[];
  suggested_filename?: string;
  suggested_name?: string;
  suggested_name_translit?: string;
  summary?: string;
  description?: string;
  needs_new_folder?: boolean;
  extracted_text?: string;
  language?: string;
  new_name_translit?: string;
}

export interface FileInfo {
  id: string;
  filename?: string;
  path?: string;
  metadata?: FileMetadata;
  person?: string;
  date_of_birth?: string;
  expiration_date?: string;
  passport_number?: string;
  tags_ru?: string[];
  tags_en?: string[];
  sources?: string[];
  status?: FileStatus;
  extracted_text?: string;
  translated_text?: string;
  translation_lang?: string;
  confirmed?: boolean;
  chat_history?: ChatHistory[];
  missing?: string[];
  suggested_path?: string;
  review_comment?: string;
  prompt?: string;
  raw_response?: string;
  created_path?: string;
}

export interface UploadPendingResponse extends FileInfo {
  status: FileStatus;
}

export interface UploadFinalResponse extends FileInfo {
  status: FileStatus;
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
