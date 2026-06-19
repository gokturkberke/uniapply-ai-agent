import { getJson, postJson } from "./client";
import type {
  AskRequest,
  AskResponse,
  ChecklistRequest,
  ChecklistResponse,
  DetectMissingRequest,
  DetectMissingResponse,
  EmailRequest,
  EmailResponse,
  HealthResponse,
  ProgrammeInfo,
} from "./types";

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export function getProgrammes(): Promise<ProgrammeInfo[]> {
  return getJson<ProgrammeInfo[]>("/programmes");
}

export function postAsk(payload: AskRequest): Promise<AskResponse> {
  return postJson<AskRequest, AskResponse>("/ask", payload);
}

export function postChecklist(
  payload: ChecklistRequest,
): Promise<ChecklistResponse> {
  return postJson<ChecklistRequest, ChecklistResponse>("/checklist", payload);
}

export function postDetectMissing(
  payload: DetectMissingRequest,
): Promise<DetectMissingResponse> {
  return postJson<DetectMissingRequest, DetectMissingResponse>(
    "/detect-missing",
    payload,
  );
}

export function postDraftEmail(payload: EmailRequest): Promise<EmailResponse> {
  return postJson<EmailRequest, EmailResponse>("/draft-email", payload);
}
