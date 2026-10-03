import type { TrapProps } from "./trap";

export function Trap({ onChange, value }: TrapProps) {
  return (
    <div
      aria-hidden="true"
      style={{
        height: 1,
        left: -9999,
        opacity: 0,
        overflow: "hidden",
        pointerEvents: "none",
        position: "absolute",
        width: 1,
      }}
    >
      <input
        autoComplete="off"
        name="website"
        onChange={(event) => onChange(event.target.value)}
        tabIndex={-1}
        type="text"
        value={value}
      />
    </div>
  );
}
