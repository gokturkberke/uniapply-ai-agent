import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProgrammeSelector } from "../components/ProgrammeSelector";
import type { Programme } from "../config/programmes";

const PROGRAMMES: Programme[] = [
  {
    university_slug: "technical-university-of-munich",
    programme_slug: "msc-informatics",
    title: "Technical University of Munich - M.Sc. Informatics",
  },
  {
    university_slug: "saarland-university",
    programme_slug: "msc-computer-science",
    title: "Saarland University - M.Sc. Computer Science",
  },
];

describe("ProgrammeSelector", () => {
  it("lists the placeholder plus the provided programmes", () => {
    render(
      <ProgrammeSelector programmes={PROGRAMMES} value={null} onChange={vi.fn()} />,
    );

    expect(screen.getAllByRole("option")).toHaveLength(PROGRAMMES.length + 1);
    expect(
      screen.getByRole("option", {
        name: "Technical University of Munich - M.Sc. Informatics",
      }),
    ).toBeInTheDocument();
  });

  it("reports the composite slug key when a programme is picked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ProgrammeSelector programmes={PROGRAMMES} value={null} onChange={onChange} />,
    );

    await user.selectOptions(
      screen.getByRole("combobox"),
      "technical-university-of-munich/msc-informatics",
    );

    expect(onChange).toHaveBeenCalledWith(
      "technical-university-of-munich/msc-informatics",
    );
  });
});
