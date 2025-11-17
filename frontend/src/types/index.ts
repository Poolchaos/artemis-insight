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
  s3_key: string;
  page_count: number;
  uploaded_at: string;
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

export interface Summary {
  id: string;
  job_id: string;
  content: string;
  template_id?: string;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  fields: string[];
  prompt_template: string;
  is_system: boolean;
}

export interface SnippetResult {
  query: string;
  text: string;
  score: number;
  page_number: number;
  section_heading?: string;
}
