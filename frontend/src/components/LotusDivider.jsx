export default function LotusDivider({ tagline }) {
  return (
    <div className="lotus-divider">
      <div className="lotus-divider__ornament" aria-hidden="true">
        <span className="lotus-line" />
        <span className="lotus-gem">✦</span>
        <span className="lotus-line lotus-line--flip" />
      </div>
      {tagline ? <p className="lotus-tagline">{tagline}</p> : null}
    </div>
  );
}
