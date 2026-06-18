import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({ postDraftEmail: vi.fn() }));

import { postDraftEmail } from "../api/endpoints";
import { DraftEmailPanel } from "../components/DraftEmailPanel";
import type { Programme } from "../config/programmes";

const PROGRAMME: Programme = {
  university_slug: "university-of-stuttgart",
  programme_slug: "msc-computer-science",
  title: "University of Stuttgart - M.Sc. Computer Science",
};

beforeEach(() => {
  vi.mocked(postDraftEmail).mockReset();
});

describe("DraftEmailPanel", () => {
  it("renders the draft subject and body with a copy action", async () => {
    vi.mocked(postDraftEmail).mockResolvedValue({
      subject: "Inquiry about deadlines",
      body: "Dear Admissions Team,\n\nI am writing to ask about the deadline.",
      citations: [],
      insufficient_context: false,
      university_slug: PROGRAMME.university_slug,
      programme_slug: PROGRAMME.programme_slug,
      disclaimer: "Informational support only.",
    });
    const user = userEvent.setup();
    render(<DraftEmailPanel programme={PROGRAMME} />);

    await user.type(screen.getByLabelText("Email topic"), "deadlines");
    await user.click(screen.getByRole("button", { name: "Draft email" }));

    expect(
      await screen.findByText("Subject: Inquiry about deadlines"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Dear Admissions Team/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });
});
