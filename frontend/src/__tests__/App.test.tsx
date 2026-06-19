import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({
  getHealth: vi.fn().mockResolvedValue({
    status: "ok",
    app_name: "UniApply AI Agent",
    environment: "development",
    version: "v1",
    llm_provider: "mock",
    llm_model: null,
  }),
  getProgrammes: vi.fn().mockResolvedValue([
    {
      university_slug: "saarland-university",
      programme_slug: "msc-computer-science",
      title: "Saarland University - M.Sc. Computer Science",
    },
    {
      university_slug: "technical-university-of-munich",
      programme_slug: "msc-informatics",
      title: "Technical University of Munich - M.Sc. Informatics",
    },
  ]),
  postAsk: vi.fn(),
  postChecklist: vi.fn(),
  postDetectMissing: vi.fn(),
  postDraftEmail: vi.fn(),
}));

import App from "../App";

describe("App programme gate", () => {
  it("loads programmes and keeps the tabs disabled until one is selected", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByText("Select a programme to begin")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Ask" })).toBeDisabled();

    // Programmes are fetched on mount; wait for the option, then pick it.
    await screen.findByRole("option", {
      name: "Saarland University - M.Sc. Computer Science",
    });
    await user.selectOptions(
      screen.getByRole("combobox"),
      "saarland-university/msc-computer-science",
    );

    expect(screen.getByRole("tab", { name: "Ask" })).toBeEnabled();
    expect(screen.queryByText("Select a programme to begin")).toBeNull();
    expect(screen.getByLabelText("Your question")).toBeInTheDocument();
  });
});
