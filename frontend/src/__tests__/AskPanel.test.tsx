import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({ postAsk: vi.fn() }));

import { postAsk } from "../api/endpoints";
import { AskPanel } from "../components/AskPanel";
import type { Programme } from "../config/programmes";

const PROGRAMME: Programme = {
  university_slug: "technical-university-of-munich",
  programme_slug: "msc-informatics",
  title: "Technical University of Munich - M.Sc. Informatics",
};

const DISCLAIMER = "Informational support only.";

beforeEach(() => {
  vi.mocked(postAsk).mockReset();
});

describe("AskPanel", () => {
  it("renders a grounded answer with confidence and citations", async () => {
    vi.mocked(postAsk).mockResolvedValue({
      answer: "The deadline is March 31.",
      citations: [
        {
          source_id: "tum-informatics-official-programme-page",
          heading_path: ["Application", "Deadlines"],
        },
      ],
      insufficient_context: false,
      confidence: 0.92,
      university_slug: PROGRAMME.university_slug,
      programme_slug: PROGRAMME.programme_slug,
      disclaimer: DISCLAIMER,
    });
    const user = userEvent.setup();
    render(<AskPanel programme={PROGRAMME} />);

    await user.type(screen.getByLabelText("Your question"), "When is the deadline?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("The deadline is March 31.")).toBeInTheDocument();
    expect(screen.getByText("Confidence 92%")).toBeInTheDocument();
    expect(
      screen.getByText("tum-informatics-official-programme-page"),
    ).toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
  });

  it("shows the refusal state without confidence or citations", async () => {
    vi.mocked(postAsk).mockResolvedValue({
      answer: "Information not found in the official documents.",
      citations: [],
      insufficient_context: true,
      confidence: 0,
      university_slug: PROGRAMME.university_slug,
      programme_slug: PROGRAMME.programme_slug,
      disclaimer: DISCLAIMER,
    });
    const user = userEvent.setup();
    render(<AskPanel programme={PROGRAMME} />);

    await user.type(screen.getByLabelText("Your question"), "Unsupported question?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(
      await screen.findByText("Not found in the official documents"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Information not found in the official documents."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Confidence/)).toBeNull();
  });
});
