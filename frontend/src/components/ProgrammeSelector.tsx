import { type Programme, programmeKey } from "../config/programmes";
import { controlClass } from "../ui/styles";

export function ProgrammeSelector({
  programmes,
  value,
  onChange,
  loading = false,
}: {
  programmes: Programme[];
  value: string | null;
  onChange: (key: string | null) => void;
  loading?: boolean;
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
        disabled={loading && programmes.length === 0}
        className={`${controlClass} sm:w-80`}
      >
        <option value="">
          {loading ? "Loading programmes..." : "Select a programme..."}
        </option>
        {programmes.map((programme) => (
          <option key={programmeKey(programme)} value={programmeKey(programme)}>
            {programme.title}
          </option>
        ))}
      </select>
    </div>
  );
}
