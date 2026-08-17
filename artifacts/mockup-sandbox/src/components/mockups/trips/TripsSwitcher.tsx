import { useMemo, useState } from "react";
import "./_group.css";

/* ── Unified data ───────────────────────────────────────────────────── */
const trips = [
  {
    id: 1,
    chapter: "CHAPTER 01",
    name: "Pacific Loop 2025",
    shortName: "Pacific Loop",
    year: "2025",
    ports: ["SF Marina", "Half Moon Bay", "Monterey", "Big Sur", "SF"],
    route: "SF Marina · Half Moon Bay · Monterey · Big Sur · SF",
    distance: "101.3",
    days: 4,
    crew: ["AM", "JL", "RS", "TK", "NV"],
    status: "Completed" as const,
    date: "Jun 14 – 18, 2025",
    dates: "14 — 18 JUN 2025",
    story: "A clean sweep around the cape, with the fog lifting just as we turned for home.",
  },
  {
    id: 2,
    chapter: "CHAPTER 02",
    name: "Adriatic Tour",
    shortName: "Adriatic Tour",
    year: "2025",
    ports: ["Split", "Hvar", "Dubrovnik", "Kotor"],
    route: "Split → Hvar → Dubrovnik → Kotor",
    distance: "218",
    days: 6,
    crew: ["IK", "LS", "MO", "VT", "AR", "CN"],
    status: "In progress" as const,
    date: "Aug 21 – 27, 2025",
    dates: "21 — 27 AUG 2025",
    story: "Island light, limestone harbours, and a weather window opening toward Kotor.",
  },
  {
    id: 3,
    chapter: "CHAPTER 03",
    name: "Channel Crossing",
    shortName: "Channel Crossing",
    year: "2025",
    ports: ["Cowes", "Cherbourg", "St-Malo"],
    route: "Cowes → Cherbourg → St-Malo",
    distance: "147",
    days: 2,
    crew: ["EH", "ML", "PB"],
    status: "Completed" as const,
    date: "May 02 – 04, 2025",
    dates: "02 — 04 MAY 2025",
    story: "Two watches, one moonlit crossing, and a dawn arrival through the Solent tide.",
  },
  {
    id: 4,
    chapter: "CHAPTER 04",
    name: "Biscay Run",
    shortName: "Biscay Run",
    year: "2024",
    ports: ["La Rochelle", "Santander"],
    route: "La Rochelle → Santander",
    distance: "88",
    days: 1,
    crew: ["GB", "SA", "RO", "EM"],
    status: "Completed" as const,
    date: "Apr 11 – 12, 2024",
    dates: "11 — 12 APR 2024",
    story: "A brisk southerly carried us across the bay before the coffee went cold.",
  },
  {
    id: 5,
    chapter: "CHAPTER 05",
    name: "Kattegat Loop",
    shortName: "Kattegat Loop",
    year: "2024",
    ports: ["Gothenburg", "Copenhagen", "Malmö", "Gothenburg"],
    route: "Gothenburg → Copenhagen → Malmö → Gothenburg",
    distance: "312",
    days: 5,
    crew: ["FH", "KA", "JL", "SN"],
    status: "Planned" as const,
    date: "Sep 09 – 14, 2024",
    dates: "09 — 14 SEP 2024",
    story: "The northern route is drawn; next stop is a long blue line between three cities.",
  },
];

type Status = "Completed" | "In progress" | "Planned";
type View = "cards" | "log";

/* ── Shared helpers ─────────────────────────────────────────────────── */
function statusColor(status: Status): { bg: string; border: string; text: string } {
  if (status === "Completed")  return { bg: "rgba(16,185,129,.10)",  border: "rgba(52,211,153,.18)",  text: "#34d399" };
  if (status === "In progress")return { bg: "rgba(245,158,11,.12)",  border: "rgba(251,191,36,.22)",  text: "#fbbf24" };
  return                               { bg: "rgba(96,165,250,.10)",  border: "rgba(147,197,253,.18)", text: "#93c5fd" };
}

/* ── Icons ──────────────────────────────────────────────────────────── */
type IName = "moon"|"sun"|"chevron"|"plus"|"anchor"|"log"|"more"|"compass"|"cards"|"list-lines"|"mappin"|"arrow-right"|"users"|"ruler"|"chevdown";
function Icon({ name, size = 20 }: { name: IName; size?: number }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.75, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "moon")       return <svg {...p}><path d="M20.2 15.5A8.5 8.5 0 0 1 8.5 3.8 8.5 8.5 0 1 0 20.2 15.5Z"/></svg>;
  if (name === "sun")        return <svg {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>;
  if (name === "chevron")    return <svg {...p}><path d="m9 18 6-6-6-6"/></svg>;
  if (name === "chevdown")   return <svg {...p}><path d="m6 9 6 6 6-6"/></svg>;
  if (name === "plus")       return <svg {...p}><path d="M12 5v14M5 12h14"/></svg>;
  if (name === "anchor")     return <svg {...p}><circle cx="12" cy="5" r="2"/><path d="M12 7v14M5 11h14M5 21c0-3 3.1-5 7-5s7 2 7 5"/></svg>;
  if (name === "log")        return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>;
  if (name === "more")       return <svg {...p}><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></svg>;
  if (name === "compass")    return <svg {...p}><circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z"/></svg>;
  if (name === "cards")      return <svg {...p}><rect x="2" y="3" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>;
  if (name === "list-lines") return <svg {...p}><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>;
  if (name === "mappin")     return <svg {...p}><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>;
  if (name === "arrow-right")return <svg {...p} strokeWidth={1.5}><path d="m5 12 7-7 7 7M12 5v14"/></svg>;
  if (name === "users")      return <svg {...p}><path d="M17 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M23 20v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>;
  if (name === "ruler")      return <svg {...p}><path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.4 2.4 0 0 1 0-3.4l2.6-2.6a2.4 2.4 0 0 1 3.4 0z"/><path d="m14.5 12.5 2-2M11.5 9.5l2-2M8.5 6.5l2-2"/></svg>;
  return null;
}

/* ── View toggle ────────────────────────────────────────────────────── */
function ViewToggle({ view, onChange, night }: { view: View; onChange: (v: View) => void; night: boolean }) {
  const trackBg  = night ? "rgba(255,255,255,.07)" : "rgba(0,0,0,.06)";
  const thumbBg  = night ? "#1a2744" : "#ffffff";
  const activeC  = "var(--hd-accent)";
  const inactiveC = night ? "rgba(255,255,255,.35)" : "rgba(0,0,0,.35)";
  return (
    <div
      role="tablist"
      aria-label="View style"
      className="relative flex items-center rounded-[14px] p-1 gap-1"
      style={{ background: trackBg, minWidth: 130 }}
    >
      {(["cards", "log"] as View[]).map((v) => {
        const active = view === v;
        return (
          <button
            key={v}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(v)}
            className="relative flex items-center gap-1.5 rounded-[11px] px-3 py-1.5 text-[11px] font-semibold transition-all"
            style={{
              background: active ? thumbBg : "transparent",
              color: active ? activeC : inactiveC,
              boxShadow: active ? (night ? "0 1px 6px rgba(0,0,0,.4)" : "0 1px 4px rgba(0,0,0,.10)") : "none",
              zIndex: 1,
            }}
          >
            <Icon name={v === "cards" ? "cards" : "list-lines"} size={13}/>
            <span>{v === "cards" ? "Cards" : "Log"}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ── CARDS VIEW (HarborDeck) ────────────────────────────────────────── */
function WavesAndBoat() {
  return (
    <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[120px] overflow-hidden rounded-b-[28px]">
      <svg viewBox="0 0 1600 120" preserveAspectRatio="none" className="absolute bottom-0 left-0 h-full w-[200%]" style={{ opacity: .10 }}>
        <path className="hd-wave-path-3" fill="white"
          d="M0,70 C100,45 200,95 300,70 S500,45 600,70 S800,95 900,70 S1100,45 1200,70 S1400,95 1500,70 S1600,45 1600,70 L1600,120 L0,120 Z
             M1600,70 C1500,45 1400,95 1300,70 S1100,45 1000,70 S800,95 700,70 S500,45 400,70 S200,95 100,70 S0,45 0,70 L0,120 L1600,120 Z" />
      </svg>
      <svg viewBox="0 0 1600 120" preserveAspectRatio="none" className="absolute bottom-0 left-0 h-full w-[200%]" style={{ opacity: .13 }}>
        <path className="hd-wave-path-2" fill="white"
          d="M0,80 C80,55 160,100 240,80 S400,55 480,80 S640,100 720,80 S880,55 960,80 S1120,100 1200,80 S1360,55 1440,80 S1520,100 1600,80 L1600,120 L0,120 Z
             M1600,80 C1520,55 1440,100 1360,80 S1200,55 1120,80 S960,100 880,80 S720,55 640,80 S480,100 400,80 S240,55 160,80 S80,100 0,80 L0,120 L1600,120 Z" />
      </svg>
      <svg viewBox="0 0 1600 120" preserveAspectRatio="none" className="absolute bottom-0 left-0 h-full w-[200%]" style={{ opacity: .18 }}>
        <path className="hd-wave-path-1" fill="white"
          d="M0,88 C67,65 133,110 200,88 S333,65 400,88 S533,110 600,88 S733,65 800,88 S933,110 1000,88 S1133,65 1200,88 S1333,110 1400,88 S1533,65 1600,88 L1600,120 L0,120 Z
             M1600,88 C1533,65 1467,110 1400,88 S1267,65 1200,88 S1067,110 1000,88 S867,65 800,88 S667,110 600,88 S467,65 400,88 S267,110 200,88 S67,65 0,88 L0,120 L1600,120 Z" />
      </svg>
      <div className="hd-boat absolute" style={{ right: 36, bottom: 54 }}>
        <svg width="64" height="60" viewBox="0 0 64 60" fill="none" style={{ opacity: .22 }}>
          <path d="M10 42 L54 42 L48 54 L16 54 Z" fill="white"/>
          <line x1="32" y1="42" x2="32" y2="4" stroke="white" strokeWidth="2" strokeLinecap="round"/>
          <path d="M32 6 L32 40 L6 40 Z" fill="white" fillOpacity=".75"/>
          <path d="M32 14 L32 40 L54 34 Z" fill="white" fillOpacity=".5"/>
          <line x1="32" y1="40" x2="56" y2="45" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeOpacity=".6"/>
          <path d="M32 4 L42 8 L32 12 Z" fill="white" fillOpacity=".9"/>
        </svg>
      </div>
    </div>
  );
}

function CardBadge({ status }: { status: Status }) {
  const s = statusColor(status);
  return (
    <span style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.text }}
          className="inline-flex items-center rounded-[10px] px-3 py-1.5 text-[9.5px] font-black uppercase tracking-[.15em]">
      {status}
    </span>
  );
}

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

function CardsView({ night, onFlash }: { night: boolean; onFlash: (msg: string) => void }) {
  const featured = trips[0];
  return (
    <div className="relative mx-auto min-h-[100dvh] max-w-[430px] px-5 pb-36">
      {/* Featured card */}
      <section className="hd-feature relative overflow-hidden rounded-[28px] px-6 pb-6 pt-7 text-white" style={{ minHeight: 256 }}>
        <div className="absolute -right-10 -top-14 h-52 w-52 rounded-full border border-white/[.07]"/>
        <div className="absolute -right-20 top-4  h-64 w-64 rounded-full border border-white/[.04]"/>
        <WavesAndBoat/>
        <div className="relative z-10">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[9.5px] font-bold uppercase tracking-[.2em] text-sky-200/70">Featured voyage</p>
              <p className="mt-2 text-[11px] text-white/55">{featured.date}</p>
            </div>
            <CardBadge status={featured.status}/>
          </div>
          <h2 className="mt-5 text-[32px] font-black leading-[1] tracking-[-0.05em]">
            Pacific Loop<br/>
            <span style={{ color: "rgba(255,255,255,0.65)" }}>2025</span>
          </h2>
          <p className="mt-3 text-[11px] leading-relaxed text-white/50 line-clamp-1">{featured.route}</p>
          <div className="mt-7 grid grid-cols-3 gap-4 border-t border-white/[.12] pt-5">
            <Stat label="Distance" value={featured.distance} unit="NM"/>
            <Stat label="Duration"  value={String(featured.days)} unit="DAYS"/>
            <Stat label="Crew"      value={String(featured.crew.length)} unit="SAILORS"/>
          </div>
          <button
            onClick={() => onFlash("Opening Pacific Loop 2025…")}
            className="hd-focus mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-[14px] text-[12px] font-bold tracking-wide text-white transition-all active:scale-95"
            style={{ background: "rgba(255,255,255,0.12)", backdropFilter: "blur(6px)" }}>
            View full voyage <Icon name="chevron" size={15}/>
          </button>
        </div>
      </section>

      {/* Section header */}
      <div className="mt-10 flex items-end justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.18em]" style={{ color: "var(--hd-muted)" }}>Your logbook</p>
          <h2 className="mt-1.5 text-[20px] font-extrabold tracking-[-0.03em]">
            All voyages
            <span className="ml-2 text-[14px] font-semibold" style={{ color: "var(--hd-muted)" }}>05</span>
          </h2>
        </div>
        <p className="text-[11px] font-semibold" style={{ color: "var(--hd-muted)" }}>867.3 nm total</p>
      </div>

      {/* Trip list */}
      <div className="mt-5 flex flex-col gap-4">
        {trips.slice(1).map((trip) => (
          <article key={trip.id} className="hd-card group rounded-[20px] border px-5 py-5"
            style={{ background: "var(--hd-surface)", borderColor: "var(--hd-line)", boxShadow: "var(--hd-shadow-card)" }}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-[15px] font-bold leading-tight tracking-[-0.025em]">{trip.name}</h3>
                <p className="mt-1.5 text-[11px]" style={{ color: "var(--hd-muted)" }}>{trip.date}</p>
              </div>
              <CardBadge status={trip.status}/>
            </div>
            <p className="mt-3.5 truncate text-[11px] leading-relaxed" style={{ color: "var(--hd-muted)" }}>
              {trip.ports[0]} → {trip.ports[trip.ports.length - 1]}
            </p>
            <div className="my-4 h-px" style={{ background: "var(--hd-line)" }}/>
            <div className="flex items-center gap-5">
              <div className="flex items-baseline gap-1">
                <span className="text-[17px] font-black tracking-tight">{trip.distance}</span>
                <span className="text-[10px] font-semibold" style={{ color: "var(--hd-muted)" }}>nm</span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-[17px] font-black tracking-tight">{trip.days}</span>
                <span className="text-[10px] font-semibold" style={{ color: "var(--hd-muted)" }}>d</span>
              </div>
              <div className="flex items-baseline gap-1">
                <span className="text-[17px] font-black tracking-tight">{trip.crew.length}</span>
                <span className="text-[10px] font-semibold" style={{ color: "var(--hd-muted)" }}>crew</span>
              </div>
              <button aria-label={`Open ${trip.name}`} onClick={() => onFlash(`Opening ${trip.name}…`)}
                className="hd-focus ml-auto flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] transition-all active:scale-90"
                style={{ background: "var(--hd-surface-soft)", color: "var(--hd-accent)" }}>
                <Icon name="chevron" size={17}/>
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

/* ── LOG VIEW (VoyageTimeline) ──────────────────────────────────────── */
function LogView({ night, onFlash }: { night: boolean; onFlash: (msg: string) => void }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const grouped = useMemo(() =>
    trips.reduce<Record<string, typeof trips>>((g, t) => { (g[t.year] ??= []).push(t); return g; }, {}),
  []);

  const ink    = night ? "#E8DCC8" : "#1A1208";
  const muted  = night ? "#B4A797" : "#756A5E";
  const paper  = night ? "#12100E" : "#FAF7F2";
  const card   = night ? "#1B1815" : "#FFFDF9";
  const line   = night ? "#3A3027" : "#DDD3C6";
  const accent = night ? "#D4883A" : "#C4522A";

  const logStatus: Record<Status, { label: string; color: string; dot: string }> = {
    "Completed":  { label: "Completed",   color: "#637158", dot: "#879b72" },
    "In progress":{ label: "In progress", color: "#B06A2A", dot: "#D4883A" },
    "Planned":    { label: "Planned",     color: "#81766A", dot: "#B9A99A" },
  };

  return (
    <div className="mx-auto max-w-[430px] pb-32 pt-1" style={{ color: ink, fontFamily: "'Inter', ui-sans-serif, sans-serif" }}>
      {/* Index bar */}
      <div className="mb-8 flex items-center justify-between border-y py-3" style={{ borderColor: line }}>
        <div className="flex items-center gap-2">
          <Icon name="compass" size={14}/>
          <span className="text-[10px] font-semibold uppercase tracking-[.2em]" style={{ color: muted }}>Captain's index</span>
        </div>
        <span className="font-mono text-[11px]" style={{ color: muted }}>05 ENTRIES / 866 NM</span>
      </div>

      {/* Grouped by year */}
      {Object.entries(grouped).map(([year, yearTrips]) => (
        <div key={year} className="relative mb-10">
          <div className="mb-5 flex items-baseline gap-4">
            <h2 className="text-[38px] leading-none tracking-[-0.06em]"
                style={{ fontFamily: "'Playfair Display', Georgia, serif", color: accent, fontWeight: 700 }}>
              {year}
            </h2>
            <span className="font-mono text-[9px] uppercase tracking-[.18em]" style={{ color: muted }}>
              {yearTrips.length} {yearTrips.length === 1 ? "voyage" : "voyages"}
            </span>
          </div>

          <div className="relative pl-4">
            <div className="absolute bottom-0 left-0 top-0 w-px" style={{ background: line }}/>
            <div className="space-y-4">
              {yearTrips.map((trip) => {
                const st = logStatus[trip.status];
                const isOpen = expanded === trip.name;
                return (
                  <article key={trip.id} className="relative overflow-hidden border"
                    style={{ background: card, borderColor: line, boxShadow: night ? "0 10px 35px rgba(0,0,0,.18)" : "0 8px 28px rgba(102,73,40,.06)" }}>
                    <div className="absolute -left-[21px] top-8 h-2 w-2 rounded-full border-2" style={{ background: paper, borderColor: accent }}/>
                    <div className="p-5">
                      <div className="flex items-start justify-between gap-3">
                        <span className="font-mono text-[9px] font-bold tracking-[.18em]" style={{ color: accent }}>{trip.chapter}</span>
                        <span className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[.12em]" style={{ color: st.color }}>
                          <i className="h-1.5 w-1.5 rounded-full" style={{ background: st.dot }}/>{st.label}
                        </span>
                      </div>
                      <h3 className="mt-3 text-[26px] leading-none tracking-[-0.035em]"
                          style={{ fontFamily: "'Playfair Display', Georgia, serif" }}>
                        {trip.shortName}
                      </h3>
                      <div className="mt-4 flex items-center gap-2 overflow-hidden whitespace-nowrap text-[11px]" style={{ color: muted }}>
                        <Icon name="mappin" size={13}/>
                        {trip.ports.map((port, i) => (
                          <span key={`${port}-${i}`} className="flex shrink-0 items-center gap-2">
                            <span>{port}</span>
                            {i < trip.ports.length - 1 && <Icon name="arrow-right" size={10}/>}
                          </span>
                        ))}
                      </div>
                      <div className="my-5 h-px" style={{ background: line }}/>
                      <div className="grid grid-cols-[1fr_auto] items-end gap-4">
                        <div>
                          <span className="block text-[9px] font-semibold uppercase tracking-[.17em]" style={{ color: muted }}>Distance logged</span>
                          <div className="mt-1 flex items-baseline gap-2">
                            <strong className="font-mono text-[30px] font-medium leading-none tracking-[-0.08em]" style={{ color: accent }}>{trip.distance}</strong>
                            <span className="font-mono text-[11px]" style={{ color: muted }}>NM</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center justify-end gap-1.5 text-[10px]" style={{ color: muted }}>
                            <Icon name="ruler" size={12}/>{trip.dates}
                          </div>
                          <div className="mt-2 flex items-center justify-end gap-1.5 text-[10px]" style={{ color: muted }}>
                            <Icon name="users" size={12}/>{trip.crew.length} aboard · {trip.days}d
                          </div>
                        </div>
                      </div>
                      <div className="mt-5 flex items-center justify-between gap-4">
                        <div className="flex items-center">
                          {trip.crew.map((m, i) => (
                            <span key={m} className="flex h-7 w-7 -mr-1 items-center justify-center rounded-full border text-[9px] font-semibold"
                                  style={{ background: i % 2 ? accent : paper, color: i % 2 ? paper : accent, borderColor: card }}>{m}</span>
                          ))}
                        </div>
                        <button type="button" onClick={() => setExpanded(isOpen ? null : trip.name)}
                          className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[.13em]" style={{ color: accent }}>
                          {isOpen ? "Close log" : "Read log"}
                          <span style={{ display: "inline-flex", transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 200ms" }}>
                            <Icon name="chevdown" size={13}/>
                          </span>
                        </button>
                      </div>
                      {isOpen && (
                        <p className="mt-5 border-l-2 pl-3 text-[13px] italic leading-relaxed"
                           style={{ borderColor: accent, color: muted, fontFamily: "'Playfair Display', Georgia, serif" }}>
                          {trip.story}
                        </p>
                      )}
                    </div>
                    {trip.status === "In progress" && <div className="h-1 w-full" style={{ background: accent }}/>}
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      ))}

      <footer className="flex items-center justify-center gap-2 border-t pt-8 text-[10px] uppercase tracking-[.2em]" style={{ borderColor: line, color: muted }}>
        ⚓ end of the known log
      </footer>
    </div>
  );
}

/* ── Root ───────────────────────────────────────────────────────────── */
export function TripsSwitcher() {
  const [view, setView]       = useState<View>("cards");
  const [night, setNight]     = useState(false);
  const [activeTab, setActiveTab] = useState("Trips");
  const [toast, setToast]     = useState<string | null>(null);

  function flash(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2600);
  }

  // Log view uses its own paper colour; card view uses CSS variables
  const bg = view === "log"
    ? (night ? "#12100E" : "#FAF7F2")
    : "var(--hd-bg)";

  return (
    <main className="harbor-deck" data-theme={night ? "night" : "day"}
          style={{ background: bg, transition: "background 240ms ease" }}>

      {/* ── Shared top bar ─────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-20 flex items-center justify-between px-5 py-3"
        style={{
          background: view === "log"
            ? (night ? "rgba(18,16,14,.92)" : "rgba(250,247,242,.92)")
            : "color-mix(in srgb, var(--hd-bg) 88%, transparent)",
          backdropFilter: "blur(16px)",
          borderBottom: `1px solid ${view === "log" ? (night ? "#3A3027" : "#DDD3C6") : "var(--hd-line)"}`,
          transition: "background 240ms ease, border-color 240ms ease",
        }}>

        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[.2em]"
             style={{ color: view === "log" ? (night ? "#B4A797" : "#756A5E") : "var(--hd-muted)" }}>
            {view === "cards" ? "Good morning, Alex." : "The voyage log"}
          </p>
          <h1 className="mt-0.5 text-[17px] font-extrabold tracking-[-0.035em]"
              style={{
                fontFamily: view === "log" ? "'Playfair Display', Georgia, serif" : "inherit",
                color: view === "log" ? (night ? "#E8DCC8" : "#1A1208") : "var(--hd-ink)",
              }}>
            {view === "cards" ? (
              <>Trips<span style={{ color: "var(--hd-accent)" }}>.</span></>
            ) : (
              <>Voyages<span style={{ color: night ? "#D4883A" : "#C4522A" }}>.</span></>
            )}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <ViewToggle view={view} onChange={setView} night={night}/>
          <button
            aria-label="Toggle night mode"
            onClick={() => setNight(n => !n)}
            className="hd-focus flex h-9 w-9 items-center justify-center rounded-[12px] border transition-all"
            style={{
              borderColor: view === "log" ? (night ? "#3A3027" : "#DDD3C6") : "var(--hd-line)",
              background: view === "log" ? (night ? "#1B1815" : "#FFFDF9") : "var(--hd-surface)",
              color: view === "log" ? (night ? "#D4883A" : "#C4522A") : "var(--hd-accent)",
            }}>
            <Icon name={night ? "sun" : "moon"} size={16}/>
          </button>
        </div>
      </header>

      {/* ── Animated view body ─────────────────────────────────────── */}
      <div style={{ paddingTop: 8 }}>
        <div
          style={{
            opacity: view === "cards" ? 1 : 0,
            transform: view === "cards" ? "none" : "translateY(8px)",
            transition: "opacity 220ms ease, transform 220ms ease",
            position: view === "cards" ? "relative" : "absolute",
            pointerEvents: view === "cards" ? "auto" : "none",
            width: "100%",
          }}>
          <CardsView night={night} onFlash={flash}/>
        </div>
        <div
          style={{
            opacity: view === "log" ? 1 : 0,
            transform: view === "log" ? "none" : "translateY(8px)",
            transition: "opacity 220ms ease, transform 220ms ease",
            position: view === "log" ? "relative" : "absolute",
            pointerEvents: view === "log" ? "auto" : "none",
            width: "100%",
            paddingLeft: 20,
            paddingRight: 20,
          }}>
          <LogView night={night} onFlash={flash}/>
        </div>
      </div>

      {/* ── FAB (cards view only) ──────────────────────────────────── */}
      <div style={{ opacity: view === "cards" ? 1 : 0, transition: "opacity 200ms ease", pointerEvents: view === "cards" ? "auto" : "none" }}>
        <button onClick={() => flash("New voyage started")}
          className="hd-focus fixed bottom-[84px] right-5 z-10 flex h-[54px] items-center gap-2.5 rounded-[18px] px-5 text-[13px] font-bold text-white transition-all active:scale-95"
          style={{ background: "var(--hd-accent)", boxShadow: "var(--hd-shadow-fab)" }}>
          <Icon name="plus" size={18}/> New trip
        </button>
      </div>

      {/* ── Bottom tab bar ─────────────────────────────────────────── */}
      <nav className="fixed bottom-0 left-0 right-0 z-20 border-t px-5 pb-[max(14px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl"
           style={{
             background: view === "log"
               ? (night ? "rgba(18,16,14,.92)" : "rgba(250,247,242,.92)")
               : "color-mix(in srgb,var(--hd-bg) 90%,transparent)",
             borderColor: view === "log" ? (night ? "#3A3027" : "#DDD3C6") : "var(--hd-line)",
           }}>
        <div className="mx-auto flex max-w-[390px] items-center justify-between">
          {([
            { label: "Dashboard", icon: "compass" as IName },
            { label: "Log",       icon: "log"     as IName },
            { label: "Trips",     icon: "anchor"  as IName },
            { label: "More",      icon: "more"    as IName },
          ]).map(({ label, icon }) => {
            const accentC = view === "log" ? (night ? "#D4883A" : "#C4522A") : "var(--hd-accent)";
            const mutedC  = view === "log" ? (night ? "#B4A797" : "#756A5E") : "var(--hd-muted)";
            return (
              <button key={label} onClick={() => setActiveTab(label)}
                className="hd-focus flex min-w-[62px] flex-col items-center gap-1.5 text-[10px] font-semibold transition-colors"
                style={{ color: activeTab === label ? accentC : mutedC }}>
                <Icon name={icon} size={20}/>
                <span>{label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* ── Toast ─────────────────────────────────────────────────── */}
      {toast && (
        <div role="status"
             className="fixed left-1/2 top-6 z-30 -translate-x-1/2 rounded-full px-5 py-3 text-[12px] font-semibold shadow-xl"
             style={{ background: "var(--hd-ink)", color: "var(--hd-bg)" }}>
          {toast}
        </div>
      )}
    </main>
  );
}
