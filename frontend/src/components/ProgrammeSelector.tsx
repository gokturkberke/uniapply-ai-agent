import { PROGRAMMES, programmeKey } from "../config/programmes";
import { controlClass } from "../ui/styles";

export function ProgrammeSelector({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (key: string | null) => void;
}) {
  return (
    <div>
      <label htmlFor="programme" className="sr-only">
        Programme
      </label>
      <select
        id="programme"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value || null)}
        className={`${controlClass} sm:w-80`}
      >
        <option value="">Select a programme...</option>
        {PROGRAMMES.map((programme) => (
          <option key={programmeKey(programme)} value={programmeKey(programme)}>
            {programme.university} — {programme.programme}
          </option>
        ))}
      </select>
    </div>
  );
}
