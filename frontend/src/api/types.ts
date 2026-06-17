// TypeScript mirrors of the backend Pydantic models (app/api/schemas.py,
// app/rag/generation.py, app/rag/artifacts.py). Field names match exactly.

export interface Citation {
  source_id: string;
  heading_path: string[];
}

export interface ChecklistItem {
  requirement: string;
  detail: string;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  version: string;
}

export interface AskRequest {
  question: string;
  university_slug: string;
  programme_slug?: string | null;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  insufficient_context: boolean;
  confidence: number;
  university_slug: string;
  programme_slug: string | null;
  disclaimer: string;
}

export interface ChecklistRequest {
  university_slug: string;
  programme_slug: string;
}

export interface ChecklistResponse {
  items: ChecklistItem[];
  citations: Citation[];
  insufficient_context: boolean;
  university_slug: string;
  programme_slug: string;
  disclaimer: string;
}

export interface DetectMissingRequest {
  university_slug: string;
  programme_slug: string;
  profile: string[];
}

export interface DetectMissingResponse {
  missing: string[];
  satisfied: string[];
  citations: Citation[];
  insufficient_context: boolean;
  university_slug: string;
  programme_slug: string;
  disclaimer: string;
}

export interface EmailRequest {
  university_slug: string;
  programme_slug?: string | null;
  topic: string;
}

export interface EmailResponse {
  subject: string;
  body: string;
  citations: Citation[];
  insufficient_context: boolean;
  university_slug: string;
  programme_slug: string | null;
  disclaimer: string;
}
