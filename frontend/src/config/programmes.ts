import type { ProgrammeInfo } from "../api/types";

// Programmes come from the backend registry (GET /programmes). The composite key
// (university_slug/programme_slug) is unique even when two programmes share a
// programme_slug, so it disambiguates the current selection.
export type Programme = ProgrammeInfo;

export function programmeKey(
  programme: Pick<Programme, "university_slug" | "programme_slug">,
): string {
  return `${programme.university_slug}/${programme.programme_slug}`;
}

export function findProgramme(
  programmes: Programme[],
  key: string,
): Programme | undefined {
  return programmes.find((programme) => programmeKey(programme) === key);
}
