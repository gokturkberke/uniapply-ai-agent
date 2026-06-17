import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProgrammeSelector } from "../components/ProgrammeSelector";
import { PROGRAMMES } from "../config/programmes";

describe("ProgrammeSelector", () => {
  it("lists the placeholder plus all 5 programmes", () => {
    render(<ProgrammeSelector value={null} onChange={vi.fn()} />);

    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(PROGRAMMES.length + 1);
    expect(
      screen.getByRole("option", {
        name: "Technical University of Munich — M.Sc. Informatics",
      }),
    ).toBeInTheDocument();
  });

  it("reports the composite slug key when a programme is picked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ProgrammeSelector value={null} onChange={onChange} />);

    await user.selectOptions(
      screen.getByRole("combobox"),
      "technical-university-of-munich/msc-informatics",
    );

    expect(onChange).toHaveBeenCalledWith(
      "technical-university-of-munich/msc-informatics",
    );
  });
});
