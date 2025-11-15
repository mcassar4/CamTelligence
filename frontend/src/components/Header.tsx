type Page = "live" | "events";

export function Header({ active, onNavigate }: { active: Page; onNavigate: (page: Page) => void }) {
  return (
    <header className="header">
      <div>
        <div style={{ fontWeight: 700, letterSpacing: 0.4 }}>CamTelligence</div>
        <div style={{ opacity: 0.7, fontSize: 12 }}>Person + Vehicle detection</div>
      </div>
      <nav style={{ display: "flex", gap: 10 }}>
        <NavButton label="Live Events" page="live" active={active} onClick={onNavigate} />
        <NavButton label="Event Browser" page="events" active={active} onClick={onNavigate} />
      </nav>
    </header>
  );
}

function NavButton({ label, page, active, onClick }: { label: string; page: Page; active: Page; onClick: (p: Page) => void }) {
  const style = active === page ? { background: "#0ea5e9", color: "#020617" } : {};
  return (
    <button style={style} onClick={() => onClick(page)}>
      {label}
    </button>
  );
}
