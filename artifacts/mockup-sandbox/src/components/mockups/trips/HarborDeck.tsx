import { useState } from "react";
import "./_group.css";

type IconName = "moon" | "sun" | "chevron" | "plus" | "pin" | "users" | "calendar" | "compass" | "more" | "grid" | "list";

const trips = [
  { name: "Pacific Loop 2025", route: "SF Marina  ·  Half Moon Bay  ·  Monterey  ·  Big Sur  ·  SF", distance: "101.3", days: "4", crew: "5", status: "Completed", date: "Jun 14 – 18", tone: "pacific" },
  { name: "Channel Crossing", route: "Cowes  →  Cherbourg  →  St-Malo", distance: "147", days: "2", crew: "3", status: "Completed", date: "May 02 – 04", tone: "channel" },
  { name: "Adriatic Tour", route: "Split  →  Hvar  →  Dubrovnik  →  Kotor", distance: "218", days: "6", crew: "6", status: "In progress", date: "Aug 21 – 27", tone: "adriatic" },
  { name: "Biscay Run", route: "La Rochelle  →  Santander", distance: "88", days: "1", crew: "4", status: "Completed", date: "Apr 11 – 12", tone: "biscay" },
  { name: "Kattegat Loop", route: "Gothenburg  →  Copenhagen  →  Malmö  →  Gothenburg", distance: "312", days: "5", crew: "4", status: "Planned", date: "Sep 09 – 14", tone: "kattegat" },
];

function Icon({ name, size = 19 }: { name: IconName; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "moon") return <svg {...common}><path d="M20.2 15.5A8.5 8.5 0 0 1 8.5 3.8 8.5 8.5 0 1 0 20.2 15.5Z" /></svg>;
  if (name === "sun") return <svg {...common}><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></svg>;
  if (name === "chevron") return <svg {...common}><path d="m9 18 6-6-6-6" /></svg>;
  if (name === "plus") return <svg {...common}><path d="M12 5v14M5 12h14" /></svg>;
  if (name === "pin") return <svg {...common}><path d="m12 21-7-7a9.9 9.9 0 1 1 14 0l-7 7Z" /><circle cx="12" cy="10" r="2.5" /></svg>;
  if (name === "users") return <svg {...common}><path d="M16 20v-1.8a3.8 3.8 0 0 0-3.8-3.8H6.8A3.8 3.8 0 0 0 3 18.2V20m7.6-9.6a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Zm5.1 2.1a3.4 3.4 0 0 1 2.8-6.1M17.5 14.4a3.8 3.8 0 0 1 3.5 3.8V20" /></svg>;
  if (name === "calendar") return <svg {...common}><rect x="3" y="4.5" width="18" height="17" rx="2" /><path d="M16 2v5M8 2v5M3 10h18" /></svg>;
  if (name === "compass") return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2.1 4.9-4.9 2.1 2.1-4.9 4.9-2.1Z" /></svg>;
  if (name === "grid") return <svg {...common}><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></svg>;
  if (name === "list") return <svg {...common}><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" /></svg>;
  if (name === "more") return <svg {...common}><circle cx="5" cy="12" r="1" fill="currentColor" /><circle cx="12" cy="12" r="1" fill="currentColor" /><circle cx="19" cy="12" r="1" fill="currentColor" /></svg>;
  return null;
}

function Status({ status }: { status: string }) {
  const cls = status === "Completed" ? "bg-emerald-400/15 text-emerald-300" : status === "In progress" ? "bg-amber-400/15 text-amber-300" : "bg-sky-400/15 text-sky-300";
  return <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.11em] ${cls}`}>{status}</span>;
}

export function HarborDeck() {
  const [night, setNight] = useState(false);
  const [view, setView] = useState<"list" | "grid">("list");
  const [activeTab, setActiveTab] = useState("Trips");
  const [toast, setToast] = useState(false);

  function newTrip() {
    setToast(true);
    window.setTimeout(() => setToast(false), 2400);
  }

  return (
    <main className="harbor-deck" data-theme={night ? "night" : "day"}>
      <div className="relative mx-auto min-h-[100dvh] max-w-[430px] overflow-hidden px-5 pb-28">
        <header className="flex items-center justify-between pb-5 pt-7">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[.18em]" style={{ color: "var(--hd-muted)" }}>Tuesday, September 03</p>
            <h1 className="mt-1 text-[25px] font-extrabold tracking-[-.04em]">Good morning, Alex<span style={{ color: "var(--hd-accent)" }}>.</span></h1>
          </div>
          <button aria-label="Toggle night mode" onClick={() => setNight(!night)} className="hd-focus flex h-11 w-11 items-center justify-center rounded-2xl border transition-colors" style={{ borderColor: "var(--hd-line)", background: "var(--hd-surface)", color: "var(--hd-accent)" }}>
            <Icon name={night ? "sun" : "moon"} />
          </button>
        </header>

        <section className="hd-feature relative overflow-hidden rounded-[24px] px-5 pb-5 pt-5 text-white">
          <div className="absolute -right-6 -top-10 h-44 w-44 rounded-full border border-white/10" />
          <div className="absolute -right-12 top-1 h-56 w-56 rounded-full border border-white/[.07]" />
          <div className="relative flex items-start justify-between">
            <div><p className="text-[10px] font-bold uppercase tracking-[.16em] text-sky-200/80">Featured voyage</p><p className="mt-2 text-[11px] text-slate-300">{trips[0].date}</p></div>
            <Status status={trips[0].status} />
          </div>
          <h2 className="relative mt-4 max-w-[290px] text-[28px] font-extrabold leading-[1.02] tracking-[-.045em]">Pacific Loop<br />2025</h2>
          <p className="relative mt-4 max-w-[310px] truncate text-xs text-slate-300">{trips[0].route}</p>
          <div className="relative mt-5 grid grid-cols-3 border-t border-white/15 pt-4">
            <div><p className="text-[10px] uppercase tracking-wider text-slate-400">Distance</p><p className="mt-1 text-[17px] font-bold">101.3 <small className="text-[10px] font-medium text-slate-400">NM</small></p></div>
            <div><p className="text-[10px] uppercase tracking-wider text-slate-400">Duration</p><p className="mt-1 text-[17px] font-bold">4 <small className="text-[10px] font-medium text-slate-400">DAYS</small></p></div>
            <div><p className="text-[10px] uppercase tracking-wider text-slate-400">Crew</p><p className="mt-1 text-[17px] font-bold">5 <small className="text-[10px] font-medium text-slate-400">SAILORS</small></p></div>
          </div>
          <button onClick={() => setToast(true)} className="hd-focus relative mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-white/10 text-xs font-bold tracking-wide text-white transition-colors hover:bg-white/20">View voyage <Icon name="chevron" size={15} /></button>
        </section>

        <div className="mt-8 flex items-end justify-between">
          <div><p className="text-[11px] font-bold uppercase tracking-[.16em]" style={{ color: "var(--hd-muted)" }}>Your logbook</p><h2 className="mt-1 text-xl font-extrabold tracking-[-.03em]">All voyages <span className="ml-1 text-sm font-semibold" style={{ color: "var(--hd-muted)" }}>05</span></h2></div>
          <div className="flex rounded-lg p-1" style={{ background: "var(--hd-surface-soft)" }}>
            <button onClick={() => setView("list")} className={`hd-focus rounded-md p-2 ${view === "list" ? "shadow-sm" : ""}`} style={{ background: view === "list" ? "var(--hd-surface)" : "transparent", color: view === "list" ? "var(--hd-accent)" : "var(--hd-muted)" }} aria-label="List view"><Icon name="list" size={16} /></button>
            <button onClick={() => setView("grid")} className={`hd-focus rounded-md p-2 ${view === "grid" ? "shadow-sm" : ""}`} style={{ background: view === "grid" ? "var(--hd-surface)" : "transparent", color: view === "grid" ? "var(--hd-accent)" : "var(--hd-muted)" }} aria-label="Grid view"><Icon name="grid" size={16} /></button>
          </div>
        </div>

        <div className={view === "grid" ? "mt-4 grid grid-cols-2 gap-3" : "mt-4 space-y-2.5"}>
          {trips.slice(1).map((trip) => <article key={trip.name} className={`group flex ${view === "grid" ? "min-h-[190px] flex-col" : "min-h-[92px]"} rounded-2xl border p-3.5 transition-transform active:scale-[.99]`} style={{ background: "var(--hd-surface)", borderColor: "var(--hd-line)" }}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0"><h3 className={`${view === "grid" ? "text-sm" : "text-[15px]"} truncate font-bold tracking-[-.02em]`}>{trip.name}</h3><p className="mt-1 truncate text-[10px]" style={{ color: "var(--hd-muted)" }}><Icon name="calendar" size={11} /> <span className="ml-1">{trip.date}</span></p></div>
              <Status status={trip.status} />
            </div>
            <p className="mt-3 truncate text-[11px]" style={{ color: "var(--hd-muted)" }}><Icon name="pin" size={12} /> <span className="ml-1">{trip.route}</span></p>
            <div className={`mt-auto flex items-center gap-4 pt-3 text-[11px] font-semibold ${view === "grid" ? "border-t" : ""}`} style={{ color: "var(--hd-muted)", borderColor: "var(--hd-line)" }}>
              <span><b style={{ color: "var(--hd-ink)" }}>{trip.distance}</b> nm</span><span><b style={{ color: "var(--hd-ink)" }}>{trip.days}</b> d</span><span><b style={{ color: "var(--hd-ink)" }}>{trip.crew}</b> crew</span>
              {view === "list" && <button aria-label={`Open ${trip.name}`} onClick={() => setToast(true)} className="hd-focus ml-auto flex h-9 w-9 items-center justify-center rounded-lg" style={{ background: "var(--hd-surface-soft)", color: "var(--hd-accent)" }}><Icon name="chevron" size={17} /></button>}
            </div>
          </article>)}
        </div>
      </div>

      <button onClick={newTrip} className="hd-focus fixed bottom-[78px] right-5 z-10 flex h-14 items-center gap-2 rounded-2xl px-4 text-sm font-bold text-white shadow-xl transition-transform active:scale-95" style={{ background: "var(--hd-accent)" }}><Icon name="plus" size={19} /> New trip</button>
      <nav className="fixed bottom-0 left-0 right-0 z-20 border-t px-5 pb-[max(12px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl" style={{ background: "color-mix(in srgb, var(--hd-bg) 88%, transparent)", borderColor: "var(--hd-line)" }}>
        <div className="mx-auto flex max-w-[390px] items-center justify-between">
          {["Dashboard", "Log", "Trips", "More"].map((tab, i) => <button key={tab} onClick={() => setActiveTab(tab)} className={`hd-focus flex min-w-[62px] flex-col items-center gap-1 text-[10px] font-semibold ${activeTab === tab ? "hd-tab-active" : ""}`} style={{ color: activeTab === tab ? "var(--hd-accent)" : "var(--hd-muted)" }}><Icon name={i === 0 ? "compass" : i === 1 ? "calendar" : i === 2 ? "pin" : "more"} size={19} /><span>{tab}</span></button>)}
        </div>
      </nav>
      {toast && <div role="status" className="fixed left-1/2 top-5 z-30 -translate-x-1/2 rounded-full px-4 py-2.5 text-xs font-semibold text-white shadow-lg" style={{ background: "var(--hd-ink)" }}>Voyage details are ready to explore</div>}
    </main>
  );
}