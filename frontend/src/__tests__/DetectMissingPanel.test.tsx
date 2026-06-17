import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({ postDetectMissing: vi.fn() }));

import { postDetectMissing } from "../api/endpoints";
import { DetectMissingPanel } from "../components/DetectMissingPanel";
import type { Programme } from "../config/programmes";

const PROGRAMME: Programme = {
  university_slug: "paderborn-university",
  programme_slug: "msc-computer-science",
  university: "Paderborn University",
  programme: "M.Sc. Computer Science",
};

beforeEach(() => {
  vi.mocked(postDetectMissing).mockReset();
});

describe("DetectMissingPanel", () => {
  it("splits the profile by line and renders missing vs satisfied", async () => {
    vi.mocked(postDetectMissing).mockResolvedValue({
      missing: ["Statement of Purpose"],
      satisfied: ["Bachelor's degree"],
      citations: [],
      insufficient_context: false,
      university_slug: PROGRAMME.university_slug,
      programme_slug: PROGRAMME.programme_slug,
      disclaimer: "Informational support only.",
    });
    const user = userEvent.setup();
    render(<DetectMissingPanel programme={PROGRAMME} />);

    await user.type(
      screen.getByLabelText("What you already have"),
      "Bachelor's degree{enter}IELTS 7.0",
    );
    await user.click(
      screen.getByRole("button", { name: "Detect missing documents" }),
    );

    expect(await screen.findByText("Statement of Purpose")).toBeInTheDocument();
    expect(screen.getByText("Bachelor's degree")).toBeInTheDocument();
    expect(vi.mocked(postDetectMissing)).toHaveBeenCalledWith({
      university_slug: PROGRAMME.university_slug,
      programme_slug: PROGRAMME.programme_slug,
      profile: ["Bachelor's degree", "IELTS 7.0"],
    });
  });
});
