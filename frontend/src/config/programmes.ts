// The supported programmes, scoped by the exact registry slugs the backend
// expects (data/registry/sources.json). The user must pick one before any
// request, so every call is scoped to a single institution. Three programmes
// share the slug "msc-computer-science"; the university_slug disambiguates
// them, so the composite key (university_slug/programme_slug) is unique.

export interface Programme {
  university_slug: string;
  programme_slug: string;
  university: string;
  programme: string;
}

export const PROGRAMMES: Programme[] = [
  {
    university_slug: "university-of-konstanz",
    programme_slug: "msc-computer-and-information-science",
    university: "University of Konstanz",
    programme: "M.Sc. Computer and Information Science",
  },
  {
    university_slug: "paderborn-university",
    programme_slug: "msc-computer-science",
    university: "Paderborn University",
    programme: "M.Sc. Computer Science",
  },
  {
    university_slug: "technical-university-of-munich",
    programme_slug: "msc-informatics",
    university: "Technical University of Munich",
    programme: "M.Sc. Informatics",
  },
  {
    university_slug: "university-of-stuttgart",
    programme_slug: "msc-computer-science",
    university: "University of Stuttgart",
    programme: "M.Sc. Computer Science",
  },
  {
    university_slug: "saarland-university",
    programme_slug: "msc-computer-science",
    university: "Saarland University",
    programme: "M.Sc. Computer Science",
  },
];

export function programmeKey(
  programme: Pick<Programme, "university_slug" | "programme_slug">,
): string {
  return `${programme.university_slug}/${programme.programme_slug}`;
}

export function findProgramme(key: string): Programme | undefined {
  return PROGRAMMES.find((programme) => programmeKey(programme) === key);
}
