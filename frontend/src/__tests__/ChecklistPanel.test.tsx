import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({ postChecklist: vi.fn() }));

import { postChecklist } from "../api/endpoints";
import { ChecklistPanel } from "../components/ChecklistPanel";
import type { Programme } from "../config/programmes";

const PROGRAMME: Programme = {
  university_slug: "saarland-university",
  programme_slug: "msc-computer-science",
  title: "Saarland University - M.Sc. Computer Science",
};

beforeEach(() => {
  vi.mocked(postChecklist).mockReset();
});

describe("ChecklistPanel", () => {
  it("renders generated checklist items", async () => {
    vi.mocked(postChecklist).mockResolvedValue({
      items: [
        { requirement: "Bachelor's degree", detail: "In CS or a related field." },
      ],
      citations: [
        { source_id: "saarland-cs-official-programme-page", heading_path: [] },
      ],
      insufficient_context: false,
      university_slug: PROGRAMME.university_slug,
      programme_slug: PROGRAMME.programme_slug,
      disclaimer: "Informational support only.",
    });
    const user = userEvent.setup();
    render(<ChecklistPanel programme={PROGRAMME} />);

    await user.click(screen.getByRole("button", { name: "Generate checklist" }));

    expect(await screen.findByText("Bachelor's degree")).toBeInTheDocument();
    expect(screen.getByText("In CS or a related field.")).toBeInTheDocument();
    expect(
      screen.getByText("saarland-cs-official-programme-page"),
    ).toBeInTheDocument();
  });
});
