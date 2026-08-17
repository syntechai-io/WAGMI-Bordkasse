import { useMemo, useState } from "react";

type TripStatus = "completed" | "in progress" | "planned";

type Trip = {
  name: string;
  route: string;
  distance: string;
  days: number;
  crew: number;
  status: TripStatus;
  bearing: string;
  accent: string;
};

const trips: Trip[] = [
  { name: "Pacific Loop 2025", route: "SF Marina  →  Half Moon Bay  →  Monterey  →  Big Sur  →  SF", distance: "101.3", days: 4, crew: 5, status: "completed", bearing: "↗", accent: "#56A18F" },
  { name: "Channel Crossing", route: "Cowes  →  Cherbourg  →  St-Malo", distance: "147", days: 2, crew: 3, status: "completed", bearing: "→", accent: "#56A18F" },
  { name: "Adriatic Tour", route: "Split  →  Hvar  →  Dubrovnik  →  Kotor", distance: "218", days: 6, crew: 6, status: "in progress", bearing: "↘", accent: "#E8A030" },
  { name: "Biscay Run", route: "La Rochelle  →  Santander", distance: "88", days: 1, crew: 4, status: "completed", bearing: "↗", accent: "#56A18F" },
  { name: "Kattegat Loop", route: "Gothenburg  →  Copenhagen  →  Malmö  →  Gothenburg", distance: "312", days: 5, crew: 4, status: "planned", bearing: "↖", accent: "#8290A2" },
];

const navItems = [
  { label: "Overview", icon: "◈" },
  { label: "Trips", icon: "⌁", active: true },
  { label: "Crew", icon: "♧" },
  { label: "Vessel", icon: "⌂" },
];

export function CaptainsLog() {
  const [light, setLight] = useState(false);
  const [filter, setFilter] = useState<"all" | TripStatus>("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [toast, setToast] = useState("");

  const visibleTrips = useMemo(
    () => filter === "all" ? trips : trips.filter((trip) => trip.status === filter),
    [filter],
  );

  const announce = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2400);
  };

  return (
    <main
      className="min-h-[100dvh] w-full overflow-x-hidden"
      style={{
        backgroundColor: light ? "#0F1F35" : "#040D1C",
        color: "#D9E0E7",
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        backgroundImage: "radial-gradient(rgba(114, 154, 169, .13) 1px, transparent 1px)",
        backgroundSize: "22px 22px",
      }}
    >
      <div className="mx-auto flex min-h-[100dvh] max-w-[1420px]">
        <aside className="hidden w-[214px] shrink-0 flex-col border-r border-[#1B3045] px-5 py-7 md:flex">
          <div className="mb-12 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#E8A030]/50 bg-[#E8A030]/10 text-xl text-[#E8A030]">⌁</div>
            <div><div className="text-[13px] font-semibold tracking-[.18em] text-[#E7EEF1]">LOGBOOK</div><div className="mt-0.5 font-mono text-[9px] tracking-[.18em] text-[#6C8791]">NORTHSTAR / 07</div></div>
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => (
              <button key={item.label} onClick={() => announce(`${item.label} view is ready for your next watch.`)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-[12px] transition ${item.active ? "bg-[#183348] text-[#E8A030]" : "text-[#79909E] hover:bg-[#10283B] hover:text-[#C1D0D5]"}`}>
                <span className="w-5 text-center text-lg">{item.icon}</span>{item.label}
                {item.active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#E8A030]" />}
              </button>
            ))}
          </nav>
          <div className="mt-auto border-t border-[#1B3045] pt-5">
            <div className="mb-3 font-mono text-[9px] uppercase tracking-[.18em] text-[#63808B]">Vessel status</div>
            <div className="flex items-center gap-2 text-[11px] text-[#9BB5B7]"><span className="h-2 w-2 rounded-full bg-[#56A18F]" />At anchor · Monterey Bay</div>
            <div className="mt-3 font-mono text-[10px] text-[#637E8D]">36N 37W · 121N 54W</div>
          </div>
        </aside>

        <section className="min-w-0 flex-1 px-5 py-6 sm:px-8 lg:px-12 lg:py-10">
          <header className="mb-8 flex items-start justify-between gap-4">
            <div>
              <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[.2em] text-[#7793A0]"><span className="h-1.5 w-1.5 rounded-full bg-[#56A18F]" />Saturday · 18 October 2025</div>
              <h1 className="text-[clamp(28px,4vw,42px)] font-semibold tracking-[-.04em] text-[#E5EBED]">Captain&apos;s log<span className="text-[#E8A030]">.</span></h1>
              <p className="mt-2 text-[13px] text-[#79909E]">A clear record of where we&apos;ve been, and where the tide takes us next.</p>
            </div>
            <button aria-label="Toggle day mode" onClick={() => setLight(!light)} className="mt-1 flex h-9 w-9 items-center justify-center rounded-lg border border-[#294055] bg-[#102337] text-[#E8A030] transition hover:border-[#E8A030]">{light ? "☀" : "◐"}</button>
          </header>

          <div className="mb-9 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[#1D3449] bg-[#1D3449] sm:grid-cols-4">
            {[
              ["05", "Total voyages", "this season"],
              ["866.3", "Nautical miles", "logged"],
              ["01", "Active trip", "at sea"],
              ["12", "Crew aboard", "across all trips"],
            ].map(([value, label, note], i) => (
              <div key={label} className={`bg-[#0A1A2C]/95 px-4 py-5 sm:px-6 ${i === 2 ? "border-l border-[#E8A030]/30" : ""}`}>
                <div className="font-mono text-[clamp(21px,3vw,30px)] tracking-[-.05em]" style={{ color: i === 2 ? "#E8A030" : "#DDE7E9" }}>{value}</div>
                <div className="mt-1 text-[11px] font-medium text-[#A4B7BD]">{label}</div><div className="mt-1 font-mono text-[9px] uppercase tracking-[.14em] text-[#597685]">{note}</div>
              </div>
            ))}
          </div>

          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="text-[17px] font-semibold text-[#DCE5E6]">Voyages</h2><p className="mt-1 font-mono text-[10px] uppercase tracking-[.15em] text-[#607C88]">Most recent first · all distances in nm</p></div>
            <div className="flex rounded-lg border border-[#253E52] bg-[#091A2B] p-1">
              {(["all", "completed", "in progress", "planned"] as const).map((key) => <button key={key} onClick={() => setFilter(key)} className={`rounded-md px-2.5 py-1.5 text-[10px] capitalize transition sm:px-3 ${filter === key ? "bg-[#29475A] text-[#E8A030]" : "text-[#718C98] hover:text-[#B5C6C9]"}`}>{key === "all" ? "All" : key}</button>)}
            </div>
          </div>

          <div className="space-y-2">
            {visibleTrips.map((trip, index) => (
              <article key={trip.name} className={`group relative overflow-hidden rounded-xl border transition ${selected === trip.name ? "border-[#E8A030]/70 bg-[#112A3D]" : "border-[#1D3449] bg-[#091A2B]/90 hover:border-[#3A5969]"}`}>
                <button onClick={() => setSelected(selected === trip.name ? null : trip.name)} className="grid w-full grid-cols-[42px_minmax(0,1fr)_auto] items-center gap-3 px-4 py-4 text-left sm:grid-cols-[54px_minmax(250px,1fr)_108px_80px_122px] sm:gap-4 sm:px-5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full border text-[22px]" style={{ color: trip.accent, borderColor: `${trip.accent}55`, backgroundColor: `${trip.accent}12` }}>{trip.bearing}</div>
                  <div className="min-w-0"><div className="truncate text-[14px] font-semibold text-[#DCE6E8]">{trip.name}</div><div className="mt-1 truncate font-mono text-[10px] text-[#71909A]">{trip.route}</div></div>
                  <div className="hidden sm:block"><div className="font-mono text-[16px] text-[#DCE6E8]">{trip.distance}</div><div className="font-mono text-[9px] uppercase tracking-wider text-[#5F7C87]">nautical mi</div></div>
                  <div className="hidden text-right sm:block"><div className="font-mono text-[13px] text-[#C0D0D2]">{trip.days}d</div><div className="font-mono text-[9px] uppercase tracking-wider text-[#5F7C87]">{trip.crew} crew</div></div>
                  <div className="text-right"><span className="inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[9px] capitalize tracking-wide" style={{ color: trip.accent, borderColor: `${trip.accent}55`, backgroundColor: `${trip.accent}12` }}><span>{trip.status === "completed" ? "◈" : trip.status === "in progress" ? "◉" : "—"}</span><span className="hidden sm:inline">{trip.status}</span><span className="sm:hidden">{trip.distance} nm</span></span></div>
                </button>
                {selected === trip.name && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#294457] bg-[#0B2032] px-5 py-3 text-[11px] text-[#91A9AF]"><span><strong className="font-mono text-[#E8A030]">LEG {String(index + 1).padStart(2, "0")}</strong> · voyage details opened</span><button onClick={() => announce(`Preparing ${trip.name} for export.`)} className="rounded-md border border-[#3B596A] px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-[#B9CBCD] hover:border-[#E8A030] hover:text-[#E8A030]">Export log</button></div>}
              </article>
            ))}
          </div>
          <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[#1A3144] pt-5 font-mono text-[9px] uppercase tracking-[.16em] text-[#587582]"><span>Last synced 04:42 UTC · GPS online</span><button onClick={() => announce("New voyage entry is ready to plot.")} className="text-[#E8A030] hover:text-[#F3C16B]">+ Log a voyage</button></footer>
        </section>
      </div>
      {toast && <div className="fixed bottom-5 left-1/2 z-10 -translate-x-1/2 rounded-lg border border-[#42606A] bg-[#102A3B] px-4 py-3 text-[12px] text-[#D5E2E1] shadow-2xl">{toast}</div>}
    </main>
  );
}