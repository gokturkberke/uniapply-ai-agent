import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({
  getHealth: vi.fn().mockResolvedValue({
    status: "ok",
    app_name: "UniApply AI Agent",
    environment: "development",
    version: "v1",
  }),
  postAsk: vi.fn(),
  postChecklist: vi.fn(),
  postDetectMissing: vi.fn(),
  postDraftEmail: vi.fn(),
}));

import App from "../App";

describe("App programme gate", () => {
  it("keeps the tabs disabled until a programme is selected", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByText("Select a programme to begin")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Ask" })).toBeDisabled();

    await user.selectOptions(
      screen.getByRole("combobox"),
      "saarland-university/msc-computer-science",
    );

    expect(screen.getByRole("tab", { name: "Ask" })).toBeEnabled();
    expect(screen.queryByText("Select a programme to begin")).toBeNull();
    expect(screen.getByLabelText("Your question")).toBeInTheDocument();
  });
});
