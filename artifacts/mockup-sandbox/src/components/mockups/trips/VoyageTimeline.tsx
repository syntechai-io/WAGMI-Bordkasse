import { useMemo, useState } from "react";
import { Anchor, ArrowDownRight, CalendarDays, ChevronDown, Compass, MapPin, Moon, Ruler, Sun, Users, Waves } from "lucide-react";

type TripStatus = "completed" | "in progress" | "planned";

type Trip = {
  year: string;
  chapter: string;
  title: string;
  ports: string[];
  dates: string;
  distance: string;
  days: number;
  crew: string[];
  status: TripStatus;
  story: string;
};

const trips: Trip[] = [
  {
    year: "2025",
    chapter: "CHAPTER 01",
    title: "Pacific Loop",
    ports: ["SF Marina", "Half Moon Bay", "Monterey", "Big Sur", "SF"],
    dates: "06 — 09 SEP 2025",
    distance: "101.3",
    days: 4,
    crew: ["AM", "JL", "RS", "TK", "NV"],
    status: "completed",
    story: "A clean sweep around the cape, with the fog lifting just as we turned for home.",
  },
  {
    year: "2024",
    chapter: "CHAPTER 02",
    title: "Channel Crossing",
    ports: ["Cowes", "Cherbourg", "St-Malo"],
    dates: "18 — 20 JUL 2024",
    distance: "147",
    days: 2,
    crew: ["EH", "ML", "PB"],
    status: "completed",
    story: "Two watches, one moonlit crossing, and a dawn arrival through the Solent tide.",
  },
  {
    year: "2024",
    chapter: "CHAPTER 03",
    title: "Adriatic Tour",
    ports: ["Split", "Hvar", "Dubrovnik", "Kotor"],
    dates: "02 — 08 JUN 2024",
    distance: "218",
    days: 6,
    crew: ["IK", "LS", "MO", "VT", "AR", "CN"],
    status: "in progress",
    story: "Island light, limestone harbours, and a weather window opening toward Kotor.",
  },
  {
    year: "2023",
    chapter: "CHAPTER 04",
    title: "Biscay Run",
    ports: ["La Rochelle", "Santander"],
    dates: "11 — 12 AUG 2023",
    distance: "88",
    days: 1,
    crew: ["GB", "SA", "RO", "EM"],
    status: "completed",
    story: "A brisk southerly carried us across the bay before the coffee went cold.",
  },
  {
    year: "2023",
    chapter: "CHAPTER 05",
    title: "Kattegat Loop",
    ports: ["Gothenburg", "Copenhagen", "Malmö", "Gothenburg"],
    dates: "22 — 27 MAY 2023",
    distance: "312",
    days: 5,
    crew: ["FH", "KA", "JL", "SN"],
    status: "planned",
    story: "The northern route is drawn; next stop is a long blue line between three cities.",
  },
];

const statusStyles: Record<TripStatus, { label: string; color: string; dot: string }> = {
  completed: { label: "Completed", color: "#637158", dot: "#879b72" },
  "in progress": { label: "In progress", color: "#B06A2A", dot: "#D4883A" },
  planned: { label: "Planned", color: "#81766A", dot: "#B9A99A" },
};

export function VoyageTimeline() {
  const [night, setNight] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const grouped = useMemo(() => {
    return trips.reduce<Record<string, Trip[]>>((groups, trip) => {
      (groups[trip.year] ??= []).push(trip);
      return groups;
    }, {});
  }, []);

  const ink = night ? "#E8DCC8" : "#1A1208";
  const muted = night ? "#B4A797" : "#756A5E";
  const paper = night ? "#12100E" : "#FAF7F2";
  const card = night ? "#1B1815" : "#FFFDF9";
  const line = night ? "#3A3027" : "#DDD3C6";
  const accent = night ? "#D4883A" : "#C4522A";

  return (
    <main
      className="min-h-[100dvh] w-full overflow-x-hidden"
      style={{
        background: paper,
        color: ink,
        fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif",
        transition: "background-color 240ms ease, color 240ms ease",
      }}
    >
      <div className="mx-auto max-w-[760px] px-5 pb-16 pt-7 sm:px-8 sm:pt-10">
        <header className="flex items-start justify-between">
          <div>
            <div className="mb-5 flex items-center gap-2" style={{ color: accent }}>
              <Anchor size={16} strokeWidth={1.7} />
              <span className="text-[10px] font-semibold uppercase tracking-[0.25em]">The voyage log</span>
            </div>
            <h1
              className="text-[clamp(2.9rem,12vw,5.6rem)] leading-[0.88] tracking-[-0.055em]"
              style={{ fontFamily: "'Playfair Display', Georgia, serif", fontWeight: 700 }}
            >
              Voyages<span style={{ color: accent }}>.</span>
            </h1>
            <p className="mt-4 max-w-[370px] text-[13px] leading-relaxed" style={{ color: muted }}>
              A record of miles sailed, harbours found, and weather remembered.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setNight((value) => !value)}
            aria-label={night ? "Switch to day mode" : "Switch to night mode"}
            className="mt-1 flex h-10 w-10 items-center justify-center rounded-full border transition-transform hover:scale-105"
            style={{ borderColor: line, color: accent, background: card }}
          >
            {night ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </header>

        <div className="mt-10 flex items-center justify-between border-y py-3" style={{ borderColor: line }}>
          <div className="flex items-center gap-2">
            <Compass size={14} style={{ color: accent }} />
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em]" style={{ color: muted }}>Captain&apos;s index</span>
          </div>
          <span className="font-mono text-[11px]" style={{ color: muted }}>05 ENTRIES / 762 NM</span>
        </div>

        <section className="mt-10">
          {Object.entries(grouped).map(([year, yearTrips]) => (
            <div key={year} className="relative mb-12">
              <div className="mb-5 flex items-baseline gap-4">
                <h2
                  className="text-[40px] leading-none tracking-[-0.06em] sm:text-[48px]"
                  style={{ fontFamily: "'Playfair Display', Georgia, serif", color: accent }}
                >
                  {year}
                </h2>
                <span className="font-mono text-[9px] uppercase tracking-[0.18em]" style={{ color: muted }}>
                  {yearTrips.length} {yearTrips.length === 1 ? "voyage" : "voyages"}
                </span>
              </div>
              <div className="relative pl-4 sm:pl-7">
                <div className="absolute bottom-0 left-0 top-0 w-px" style={{ background: line }} />
                <div className="space-y-5">
                  {yearTrips.map((trip) => {
                    const status = statusStyles[trip.status];
                    const isOpen = expanded === trip.title;
                    return (
                      <article
                        key={trip.title}
                        className="relative overflow-hidden border"
                        style={{ background: card, borderColor: line, boxShadow: night ? "0 10px 35px rgba(0,0,0,.18)" : "0 8px 28px rgba(102,73,40,.06)" }}
                      >
                        <div className="absolute -left-[21px] top-8 h-2 w-2 rounded-full border-2" style={{ background: paper, borderColor: accent }} />
                        <div className="p-5 sm:p-7">
                          <div className="flex items-start justify-between gap-3">
                            <span className="font-mono text-[9px] font-bold tracking-[0.18em]" style={{ color: accent }}>{trip.chapter}</span>
                            <span className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.12em]" style={{ color: status.color }}>
                              <i className="h-1.5 w-1.5 rounded-full" style={{ background: status.dot }} />{status.label}
                            </span>
                          </div>
                          <h3 className="mt-4 text-[28px] leading-none tracking-[-0.035em] sm:text-[34px]" style={{ fontFamily: "'Playfair Display', Georgia, serif" }}>
                            {trip.title}
                          </h3>
                          <div className="mt-5 flex items-center gap-2 overflow-hidden whitespace-nowrap text-[11px]" style={{ color: muted }}>
                            <MapPin size={13} className="shrink-0" style={{ color: accent }} />
                            {trip.ports.map((port, index) => (
                              <span key={`${port}-${index}`} className="flex shrink-0 items-center gap-2">
                                <span>{port}</span>{index < trip.ports.length - 1 && <ArrowDownRight size={12} className="rotate-[-45deg]" />}
                              </span>
                            ))}
                          </div>
                          <div className="my-6 h-px" style={{ background: line }} />
                          <div className="grid grid-cols-[1fr_auto] items-end gap-4">
                            <div>
                              <span className="block text-[9px] font-semibold uppercase tracking-[0.17em]" style={{ color: muted }}>Distance logged</span>
                              <div className="mt-1 flex items-baseline gap-2">
                                <strong className="font-mono text-[34px] font-medium leading-none tracking-[-0.08em]" style={{ color: accent }}>{trip.distance}</strong>
                                <span className="font-mono text-[11px]" style={{ color: muted }}>NM</span>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="flex items-center justify-end gap-1.5 text-[10px]" style={{ color: muted }}><CalendarDays size={12} />{trip.dates}</div>
                              <div className="mt-2 flex items-center justify-end gap-1.5 text-[10px]" style={{ color: muted }}><Ruler size={12} />{trip.days} {trip.days === 1 ? "day" : "days"} underway</div>
                            </div>
                          </div>
                          <div className="mt-6 flex items-center justify-between gap-4">
                            <div className="flex items-center">
                              {trip.crew.map((member, index) => (
                                <span key={member} className="flex h-7 w-7 -mr-1 items-center justify-center rounded-full border text-[9px] font-semibold" style={{ background: index % 2 ? accent : paper, color: index % 2 ? paper : accent, borderColor: card }}>{member}</span>
                              ))}
                              <span className="ml-3 flex items-center gap-1 text-[10px]" style={{ color: muted }}><Users size={12} />{trip.crew.length} aboard</span>
                            </div>
                            <button type="button" onClick={() => setExpanded(isOpen ? null : trip.title)} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.13em]" style={{ color: accent }}>
                              {isOpen ? "Close log" : "Read log"} <ChevronDown size={13} className={isOpen ? "rotate-180 transition-transform" : "transition-transform"} />
                            </button>
                          </div>
                          {isOpen && <p className="mt-5 border-l-2 pl-3 text-[13px] italic leading-relaxed" style={{ borderColor: accent, color: muted, fontFamily: "'Playfair Display', Georgia, serif" }}>{trip.story}</p>}
                        </div>
                        {trip.status === "in progress" && <div className="h-1 w-full" style={{ background: accent }} />}
                      </article>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </section>
        <footer className="flex items-center justify-center gap-2 border-t pt-8 text-[10px] uppercase tracking-[0.2em]" style={{ borderColor: line, color: muted }}>
          <Waves size={13} style={{ color: accent }} /> end of the known log
        </footer>
      </div>
    </main>
  );
}

export default VoyageTimeline;