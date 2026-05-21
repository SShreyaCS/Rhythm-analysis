const stroke = { stroke: 'currentColor', strokeWidth: 1.5, fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round' };

export function LogoIcon({ size = 44 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 44 44" aria-hidden="true">
      <circle cx="22" cy="22" r="19" {...stroke} opacity="0.85" />
      <path
        d="M22 10c0 6-6 8-6 15 0 5 6 9 6 9s6-4 6-9c0-7-6-9-6-15z"
        {...stroke}
      />
      <path d="M16 19c-4-3-8-2-10 2M28 19c4-3 8-2 10 2" {...stroke} />
      <path d="M14 28c2 2 5 3 8 3s6-1 8-3" {...stroke} />
      <circle cx="22" cy="14" r="2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function InfoIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" {...stroke} />
      <path d="M12 11v6M12 8h.01" {...stroke} />
    </svg>
  );
}

export function ChevronLeftIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 6l-6 6 6 6" {...stroke} />
    </svg>
  );
}

export function UploadIcon({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 16V6M8 10l4-4 4 4" {...stroke} />
      <path d="M4 18h16" {...stroke} />
    </svg>
  );
}

export function RhythmIcon({ size = 64 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <circle cx="32" cy="32" r="26" {...stroke} opacity="0.5" />
      <path d="M12 36h6l4-12 4 20 4-16 4 10h6" {...stroke} />
    </svg>
  );
}
