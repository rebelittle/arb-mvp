type Props = {
  selected: string;
  onChange: (sport: string) => void;
};

const SPORTS = [
  { key: "", label: "All" },
  { key: "nfl", label: "NFL" },
  { key: "nba", label: "NBA" },
  { key: "ncaam", label: "NCAAM" },
  { key: "mlb", label: "MLB" },
  { key: "nhl", label: "NHL" },
  { key: "soccer", label: "Soccer" },
];

export default function SportTabs({ selected, onChange }: Props) {
  return (
    <div className="sport-tabs">
      {SPORTS.map(({ key, label }) => (
        <button
          key={key}
          className={`sport-tab${selected === key ? " active" : ""}`}
          onClick={() => onChange(key)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  );
}
