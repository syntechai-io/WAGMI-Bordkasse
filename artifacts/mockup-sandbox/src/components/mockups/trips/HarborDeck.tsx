import { useState } from "react";
import "./_group.css";

/* ── Data ─────────────────────────────────────────────────────────── */
const trips = [
  { id: 1, name: "Pacific Loop 2025",  from: "SF Marina",    to: "SF Marina",    route: "SF Marina · Half Moon Bay · Monterey · Big Sur · SF", distance: "101.3", days: "4",  crew: "5", status: "Completed",  date: "Jun 14 – 18, 2025" },
  { id: 2, name: "Adriatic Tour",      from: "Split",        to: "Kotor",        route: "Split → Hvar → Dubrovnik → Kotor",                    distance: "218",   days: "6",  crew: "6", status: "In progress", date: "Aug 21 – 27, 2025" },
  { id: 3, name: "Channel Crossing",   from: "Cowes",        to: "St-Malo",      route: "Cowes → Cherbourg → St-Malo",                         distance: "147",   days: "2",  crew: "3", status: "Completed",  date: "May 02 – 04, 2025" },
  { id: 4, name: "Biscay Run",         from: "La Rochelle",  to: "Santander",    route: "La Rochelle → Santander",                             distance: "88",    days: "1",  crew: "4", status: "Completed",  date: "Apr 11 – 12, 2025" },
  { id: 5, name: "Kattegat Loop",      from: "Gothenburg",   to: "Gothenburg",   route: "Gothenburg → Copenhagen → Malmö → Gothenburg",        distance: "312",   days: "5",  crew: "4", status: "Planned",    date: "Sep 09 – 14, 2025" },
];

/* ── Status badge — matching reference (dark pill, bold accent text) */
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; border: string; color: string }> = {
    "Completed":  { bg: "rgba(16,185,129,.10)",  border: "rgba(52,211,153,.18)",  color: "#34d399" },
    "In progress":{ bg: "rgba(245,158,11,.12)",  border: "rgba(251,191,36,.22)",  color: "#fbbf24" },
    "Planned":    { bg: "rgba(96,165,250,.10)",  border: "rgba(147,197,253,.18)", color: "#93c5fd" },
  };
  const s = map[status] ?? map["Planned"];
  return (
    <span style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color }}
          className="inline-flex items-center rounded-[10px] px-3 py-1.5 text-[9.5px] font-black uppercase tracking-[.15em]">
      {status}
    </span>
  );
}

/* ── Animated wave SVG watermark ──────────────────────────────────── */
function WavesAndBoat() {
  return (
    <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[120px] overflow-hidden rounded-b-[28px]">
      {/* Wave layer 3 — deepest, slowest */}
      <svg viewBox="0 0 1600 120" preserveAspectRatio="none" className="absolute bottom-0 left-0 h-full w-[200%]" style={{ opacity: .10 }}>
        <path className="hd-wave-path-3" fill="white"
          d="M0,70 C100,45 200,95 300,70 S500,45 600,70 S800,95 900,70 S1100,45 1200,70 S1400,95 1500,70 S1600,45 1600,70 L1600,120 L0,120 Z
             M1600,70 C1500,45 1400,95 1300,70 S1100,45 1000,70 S800,95 700,70 S500,45 400,70 S200,95 100,70 S0,45 0,70 L0,120 L1600,120 Z" />
      </svg>
      {/* Wave layer 2 — middle */}
      <svg viewBox="0 0 1600 120" preserveAspectRatio="none" className="absolute bottom-0 left-0 h-full w-[200%]" style={{ opacity: .13 }}>
        <path className="hd-wave-path-2" fill="white"
          d="M0,80 C80,55 160,100 240,80 S400,55 480,80 S640,100 720,80 S880,55 960,80 S1120,100 1200,80 S1360,55 1440,80 S1520,100 1600,80 L1600,120 L0,120 Z
             M1600,80 C1520,55 1440,100 1360,80 S1200,55 1120,80 S960,100 880,80 S720,55 640,80 S480,100 400,80 S240,55 160,80 S80,100 0,80 L0,120 L1600,120 Z" />
      </svg>
      {/* Wave layer 1 — front, fastest */}
      <svg viewBox="0 0 1600 120" preserveAspectRatio="none" className="absolute bottom-0 left-0 h-full w-[200%]" style={{ opacity: .18 }}>
        <path className="hd-wave-path-1" fill="white"
          d="M0,88 C67,65 133,110 200,88 S333,65 400,88 S533,110 600,88 S733,65 800,88 S933,110 1000,88 S1133,65 1200,88 S1333,110 1400,88 S1533,65 1600,88 L1600,120 L0,120 Z
             M1600,88 C1533,65 1467,110 1400,88 S1267,65 1200,88 S1067,110 1000,88 S867,65 800,88 S667,110 600,88 S467,65 400,88 S267,110 200,88 S67,65 0,88 L0,120 L1600,120 Z" />
      </svg>

      {/* Sailboat silhouette — riding the top wave */}
      <div className="hd-boat absolute" style={{ right: 36, bottom: 54 }}>
        <svg width="64" height="60" viewBox="0 0 64 60" fill="none" style={{ opacity: .22 }}>
          {/* Hull */}
          <path d="M10 42 L54 42 L48 54 L16 54 Z" fill="white"/>
          {/* Mast */}
          <line x1="32" y1="42" x2="32" y2="4" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          {/* Main sail */}
          <path d="M32 6 L32 40 L6 40 Z" fill="white" fillOpacity=".75"/>
          {/* Jib */}
          <path d="M32 14 L32 40 L54 34 Z" fill="white" fillOpacity=".5"/>
          {/* Boom */}
          <line x1="32" y1="40" x2="56" y2="45" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeOpacity=".6"/>
          {/* Flag */}
          <path d="M32 4 L42 8 L32 12 Z" fill="white" fillOpacity=".9"/>
        </svg>
      </div>
    </div>
  );
}

/* ── Mini stat cell ───────────────────────────────────────────────── */
function Stat({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-[9px] font-semibold uppercase tracking-[.18em] text-white/50">{label}</p>
      <p className="text-[22px] font-black leading-none tracking-[-0.04em] text-white">
        {value}<span className="ml-1 text-[11px] font-semibold text-white/55">{unit}</span>
      </p>
    </div>
  );
}

/* ── Icon set ─────────────────────────────────────────────────────── */
type IName = "moon"|"sun"|"chevron"|"plus"|"anchor"|"users"|"calendar"|"compass"|"more"|"grid"|"list"|"log";
function Icon({ name, size = 20 }: { name: IName; size?: number }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.75, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "moon")    return <svg {...p}><path d="M20.2 15.5A8.5 8.5 0 0 1 8.5 3.8 8.5 8.5 0 1 0 20.2 15.5Z"/></svg>;
  if (name === "sun")     return <svg {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>;
  if (name === "chevron") return <svg {...p}><path d="m9 18 6-6-6-6"/></svg>;
  if (name === "plus")    return <svg {...p}><path d="M12 5v14M5 12h14"/></svg>;
  if (name === "anchor")  return <svg {...p}><circle cx="12" cy="5" r="2"/><path d="M12 7v14M5 11h14M5 21c0-3 3.1-5 7-5s7 2 7 5"/></svg>;
  if (name === "users")   return <svg {...p}><path d="M17 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M23 20v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
  if (name === "calendar")return <svg {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>;
  if (name === "compass") return <svg {...p}><circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z"/></svg>;
  if (name === "grid")    return <svg {...p}><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>;
  if (name === "list")    return <svg {...p}><path d="M9 6h12M9 12h12M9 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>;
  if (name === "more")    return <svg {...p}><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></svg>;
  if (name === "log")     return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>;
  return null;
}

/* ── Main component ───────────────────────────────────────────────── */
export function HarborDeck() {
  const [night, setNight]         = useState(false);
  const [activeTab, setActiveTab] = useState("Trips");
  const [toast, setToast]         = useState<string | null>(null);

  function flash(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2600);
  }

  const featured = trips[0];

  return (
    <main className="harbor-deck" data-theme={night ? "night" : "day"}>
      <div className="relative mx-auto min-h-[100dvh] max-w-[430px] overflow-hidden px-5 pb-36">

        {/* ── Top bar ──────────────────────────────────────────── */}
        <header className="flex items-start justify-between pt-9 pb-8">
          <div>
            <p className="text-[10.5px] font-semibold uppercase tracking-[.2em]"
               style={{ color: "var(--hd-muted)" }}>
              Tuesday, 3 September
            </p>
            <h1 className="mt-2 text-[26px] font-extrabold leading-none tracking-[-0.045em]">
              Good morning, Alex
              <span style={{ color: "var(--hd-accent)" }}>.</span>
            </h1>
          </div>
          <button
            aria-label="Toggle night mode"
            onClick={() => setNight(n => !n)}
            className="hd-focus mt-1 flex h-11 w-11 items-center justify-center rounded-[14px] border transition-all"
            style={{ borderColor: "var(--hd-line)", background: "var(--hd-surface)", color: "var(--hd-accent)" }}>
            <Icon name={night ? "sun" : "moon"} size={18}/>
          </button>
        </header>

        {/* ── Featured voyage card ─────────────────────────────── */}
        <section className="hd-feature relative overflow-hidden rounded-[28px] px-6 pb-6 pt-7 text-white"
                 style={{ minHeight: 256 }}>

          {/* Ring decorations */}
          <div className="absolute -right-10 -top-14 h-52 w-52 rounded-full border border-white/[.07]"/>
          <div className="absolute -right-20 top-4  h-64 w-64 rounded-full border border-white/[.04]"/>

          {/* Animated waves + sailboat */}
          <WavesAndBoat/>

          {/* Content (above waves) */}
          <div className="relative z-10">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[9.5px] font-bold uppercase tracking-[.2em] text-sky-200/70">
                  Featured voyage
                </p>
                <p className="mt-2 text-[11px] text-white/55">{featured.date}</p>
              </div>
              <StatusBadge status={featured.status}/>
            </div>

            <h2 className="mt-5 text-[32px] font-black leading-[1] tracking-[-0.05em]">
              Pacific Loop<br/>
              <span style={{ color: "rgba(255,255,255,0.65)" }}>2025</span>
            </h2>

            <p className="mt-3 text-[11px] leading-relaxed text-white/50 line-clamp-1">
              {featured.route}
            </p>

            {/* Stats row */}
            <div className="mt-7 grid grid-cols-3 gap-4 border-t border-white/[.12] pt-5">
              <Stat label="Distance" value={featured.distance} unit="NM"/>
              <Stat label="Duration"  value={featured.days}     unit="DAYS"/>
              <Stat label="Crew"      value={featured.crew}     unit="SAILORS"/>
            </div>

            <button
              onClick={() => flash("Opening Pacific Loop 2025…")}
              className="hd-focus mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-[14px] text-[12px] font-bold tracking-wide text-white transition-all active:scale-95"
              style={{ background: "rgba(255,255,255,0.12)", backdropFilter: "blur(6px)" }}>
              View full voyage <Icon name="chevron" size={15}/>
            </button>
          </div>
        </section>

        {/* ── Section header ───────────────────────────────────── */}
        <div className="mt-10 flex items-end justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[.18em]"
               style={{ color: "var(--hd-muted)" }}>Your logbook</p>
            <h2 className="mt-1.5 text-[20px] font-extrabold tracking-[-0.03em]">
              All voyages
              <span className="ml-2 text-[14px] font-semibold" style={{ color: "var(--hd-muted)" }}>05</span>
            </h2>
          </div>
          <p className="text-[11px] font-semibold" style={{ color: "var(--hd-muted)" }}>
            867.3 nm total
          </p>
        </div>

        {/* ── Voyage list ──────────────────────────────────────── */}
        <div className="mt-5 flex flex-col gap-4">
          {trips.slice(1).map((trip) => (
            <article
              key={trip.id}
              className="hd-card group rounded-[20px] border px-5 py-5"
              style={{
                background: "var(--hd-surface)",
                borderColor: "var(--hd-line)",
                boxShadow: "var(--hd-shadow-card)",
              }}>

              {/* Top row */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-[15px] font-bold leading-tight tracking-[-0.025em]">
                    {trip.name}
                  </h3>
                  <p className="mt-1.5 text-[11px]" style={{ color: "var(--hd-muted)" }}>
                    {trip.date}
                  </p>
                </div>
                <StatusBadge status={trip.status}/>
              </div>

              {/* Route */}
              <p className="mt-3.5 truncate text-[11px] leading-relaxed"
                 style={{ color: "var(--hd-muted)" }}>
                {trip.from} → {trip.to}
              </p>

              {/* Divider */}
              <div className="my-4 h-px" style={{ background: "var(--hd-line)" }}/>

              {/* Stats + CTA */}
              <div className="flex items-center gap-5">
                <div className="flex items-baseline gap-1">
                  <span className="text-[17px] font-black tracking-tight">{trip.distance}</span>
                  <span className="text-[10px] font-semibold" style={{ color: "var(--hd-muted)" }}>nm</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-[17px] font-black tracking-tight">{trip.days}</span>
                  <span className="text-[10px] font-semibold" style={{ color: "var(--hd-muted)" }}>days</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-[17px] font-black tracking-tight">{trip.crew}</span>
                  <span className="text-[10px] font-semibold" style={{ color: "var(--hd-muted)" }}>crew</span>
                </div>
                <button
                  aria-label={`Open ${trip.name}`}
                  onClick={() => flash(`Opening ${trip.name}…`)}
                  className="hd-focus ml-auto flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] transition-all active:scale-90"
                  style={{ background: "var(--hd-surface-soft)", color: "var(--hd-accent)" }}>
                  <Icon name="chevron" size={17}/>
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>

      {/* ── FAB ──────────────────────────────────────────────────── */}
      <button
        onClick={() => flash("New voyage started")}
        className="hd-focus fixed bottom-[84px] right-5 z-10 flex h-[54px] items-center gap-2.5 rounded-[18px] px-5 text-[13px] font-bold text-white transition-all active:scale-95"
        style={{ background: "var(--hd-accent)", boxShadow: "var(--hd-shadow-fab)" }}>
        <Icon name="plus" size={18}/> New trip
      </button>

      {/* ── Bottom tab bar ───────────────────────────────────────── */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-20 border-t px-5 pb-[max(14px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl"
        style={{ background: "color-mix(in srgb,var(--hd-bg) 90%,transparent)", borderColor: "var(--hd-line)" }}>
        <div className="mx-auto flex max-w-[390px] items-center justify-between">
          {([
            { label: "Dashboard", icon: "compass" as IName },
            { label: "Log",       icon: "log"     as IName },
            { label: "Trips",     icon: "anchor"  as IName },
            { label: "More",      icon: "more"    as IName },
          ]).map(({ label, icon }) => (
            <button
              key={label}
              onClick={() => setActiveTab(label)}
              className={`hd-focus flex min-w-[62px] flex-col items-center gap-1.5 text-[10px] font-semibold transition-colors${activeTab === label ? " hd-tab-active" : ""}`}
              style={{ color: activeTab === label ? "var(--hd-accent)" : "var(--hd-muted)" }}>
              <Icon name={icon} size={20}/>
              <span>{label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* ── Toast ────────────────────────────────────────────────── */}
      {toast && (
        <div
          role="status"
          className="fixed left-1/2 top-6 z-30 -translate-x-1/2 rounded-full px-5 py-3 text-[12px] font-semibold shadow-xl"
          style={{ background: "var(--hd-ink)", color: "var(--hd-bg)" }}>
          {toast}
        </div>
      )}
    </main>
  );
}
