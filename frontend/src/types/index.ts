export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  name: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Document {
  id: string;
  user_id: string;
  filename: string;
  s3_key?: string;
  file_path?: string;
  file_size?: number;
  mime_type?: string;
  page_count?: number;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  upload_date?: string;
  uploaded_at?: string; // Legacy support
  created_at?: string;
  updated_at?: string;
}

export interface DocumentUploadResponse {
  document: Document;
  job_id: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  skip: number;
  limit: number;
}

export interface Job {
  id: string;
  user_id: string;
  document_id: string;
  job_type: 'summarization' | 'snippet_retrieval';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result_id?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface SummaryListItem {
  id: string;
  document_id: string;
  template_name: string;
  status: 'processing' | 'completed' | 'failed';
  section_count: number;
  total_word_count: number;
  started_at: string;
  completed_at?: string;
}

export interface SummarySection {
  title: string;
  order: number;
  content: string;
  source_chunks: number;
  pages_referenced: number[];
  word_count: number;
  generated_at: string;
}

export interface ProcessingMetadata {
  total_pages: number;
  total_words: number;
  total_chunks: number;
  embedding_count: number;
  processing_duration_seconds?: number;
  estimated_cost_usd?: number;
}

export interface Summary {
  id: string;
  document_id: string;
  user_id: string;
  job_id?: string;
  template_id: string;
  template_name: string;
  status: 'processing' | 'completed' | 'failed';
  sections: SummarySection[];
  metadata?: ProcessingMetadata;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateSection {
  // New backend format
  title?: string;
  guidance_prompt?: string;
  order?: number;
  required?: boolean;
  // Legacy format (for compatibility with form components)
  name?: string;
  prompt?: string;
}

export interface ProcessingStrategy {
  approach: string;
  chunk_size: number;
  overlap: number;
  embedding_model: string;
  summarization_model: string;
  max_tokens_per_section: number;
  temperature: number;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  // New backend fields
  target_length?: string;
  category?: string;
  sections?: TemplateSection[];
  processing_strategy?: ProcessingStrategy;
  system_prompt?: string;
  is_active?: boolean;
  is_default?: boolean;
  // Legacy fields (for compatibility)
  fields?: string[];
  prompt_template?: string;
  is_system?: boolean;
  user_id?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  version?: number;
  usage_count?: number;
}

export interface CreateTemplateRequest {
  name: string;
  description: string;
  sections: TemplateSection[];
}

export interface UpdateTemplateRequest {
  name?: string;
  description?: string;
  sections?: TemplateSection[];
}

export interface TemplateListResponse {
  items: Template[];
  total: number;
  skip: number;
  limit: number;
}

export interface SnippetResult {
  query: string;
  text: string;
  score: number;
  page_number: number;
  section_heading?: string;
}
