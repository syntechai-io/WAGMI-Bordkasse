import { useMemo, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  ChevronDown,
  CircleDot,
  Clock3,
  Fuel,
  MapPin,
  MoreHorizontal,
  Plus,
  Route,
  Search,
  ShipWheel,
  Sparkles,
  X,
} from "lucide-react";

type Stop = {
  id: number;
  date: string;
  weekday: string;
  title: string;
  detail: string;
  distance: string;
  color: string;
  x: number;
  y: number;
};

const stops: Stop[] = [
  { id: 1, date: "18", weekday: "FRI", title: "San Francisco", detail: "Marina Green · 08:40", distance: "0 nm", color: "#ef8354", x: 17, y: 70 },
  { id: 2, date: "19", weekday: "SAT", title: "Half Moon Bay", detail: "Pillar Point · 10:15", distance: "26.4 nm", color: "#3f8f88", x: 35, y: 56 },
  { id: 3, date: "20", weekday: "SUN", title: "Monterey", detail: "Municipal Wharf · 09:05", distance: "42.7 nm", color: "#e6a23c", x: 56, y: 42 },
  { id: 4, date: "21", weekday: "MON", title: "Big Sur", detail: "Point Sur · 11:30", distance: "31.2 nm", color: "#7067a6", x: 77, y: 25 },
];

export default function TripsRouteAtlas() {
  const [selected, setSelected] = useState(2);
  const [searchOpen, setSearchOpen] = useState(false);
  const [showStops, setShowStops] = useState(true);
  const active = useMemo(() => stops.find((stop) => stop.id === selected) ?? stops[0], [selected]);

  return (
    <main className="min-h-[100dvh] bg-[#f4f0e8] text-[#25333b]" style={{ fontFamily: "'DM Sans', ui-sans-serif, sans-serif" }}>
      <div className="mx-auto flex min-h-[100dvh] max-w-[1500px] flex-col overflow-hidden border-x border-[#d8d1c5] bg-[#f8f5ef] lg:flex-row">
        <aside className="flex w-full flex-col border-b border-[#d8d1c5] bg-[#f8f5ef] lg:w-[410px] lg:border-b-0 lg:border-r">
          <header className="border-b border-[#d8d1c5] px-6 pb-5 pt-7 sm:px-8">
            <div className="mb-9 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#273f48] text-[#f8f5ef]">
                  <ShipWheel size={18} strokeWidth={1.8} />
                </div>
                <span className="text-[15px] font-semibold tracking-[-0.02em]">CrewLog</span>
              </div>
              <button aria-label="More trip options" className="rounded-full p-2 text-[#7d8787] transition hover:bg-[#ebe6dc] hover:text-[#25333b]">
                <MoreHorizontal size={19} />
              </button>
            </div>
            <div className="flex items-end justify-between">
              <div>
                <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[#7f8d8d]">Voyage planner</p>
                <h1 className="text-[31px] font-semibold leading-none tracking-[-0.055em]">Pacific loop</h1>
              </div>
              <button onClick={() => setSearchOpen((value) => !value)} className="flex h-10 w-10 items-center justify-center rounded-full border border-[#d8d1c5] bg-[#fbf9f4] text-[#47636a] transition hover:border-[#47636a]" aria-label="Search trips">
                {searchOpen ? <X size={17} /> : <Search size={17} />}
              </button>
            </div>
            {searchOpen && (
              <div className="mt-5 flex items-center gap-2 rounded-xl border border-[#d8d1c5] bg-[#fbf9f4] px-3 py-2.5">
                <Search size={15} className="text-[#8b9693]" />
                <input autoFocus placeholder="Search ports or dates" className="w-full bg-transparent text-sm outline-none placeholder:text-[#a3aaa4]" />
              </div>
            )}
          </header>

          <div className="flex items-center justify-between px-6 py-5 sm:px-8">
            <div>
              <p className="text-[12px] font-medium text-[#7b8784]">4 stops · 18–21 May 2025</p>
              <p className="mt-1 text-sm font-semibold text-[#45585e]">101.3 nautical miles</p>
            </div>
            <button onClick={() => setShowStops((value) => !value)} className="flex items-center gap-1 text-[12px] font-semibold text-[#3f7775]">
              {showStops ? "Compact view" : "Show stops"} <ChevronDown size={14} className={showStops ? "rotate-180 transition" : "transition"} />
            </button>
          </div>

          <section className="flex-1 px-6 pb-6 sm:px-8">
            <div className="relative">
              <div className="absolute bottom-9 left-[21px] top-9 w-px bg-[#d7d1c6]" />
              {showStops && stops.map((stop) => (
                <button key={stop.id} onClick={() => setSelected(stop.id)} className={`group relative flex w-full items-start gap-4 rounded-2xl p-3 text-left transition ${selected === stop.id ? "bg-[#ebe6dc]" : "hover:bg-[#f0ece4]"}`}>
                  <div className="relative z-10 flex w-[18px] shrink-0 justify-center pt-1">
                    <span className="h-3 w-3 rounded-full border-[3px] border-[#f8f5ef] shadow-[0_0_0_1px_#bfc2b9]" style={{ backgroundColor: stop.color }} />
                  </div>
                  <div className="min-w-0 flex-1 pb-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-[10px] font-bold tracking-[0.14em] text-[#84908c]">{stop.weekday} · MAY {stop.date}</span>
                      <span className="text-[11px] font-semibold text-[#78918e]">{stop.distance}</span>
                    </div>
                    <p className="truncate text-[15px] font-semibold tracking-[-0.02em]">{stop.title}</p>
                    <p className="mt-1 text-[12px] text-[#82908d]">{stop.detail}</p>
                  </div>
                </button>
              ))}
            </div>
            <button className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-[#b8c1bb] py-3 text-[12px] font-semibold text-[#477875] transition hover:border-[#477875] hover:bg-[#eef1eb]">
              <Plus size={15} /> Add a stop
            </button>
          </section>
          <footer className="border-t border-[#d8d1c5] px-6 py-5 sm:px-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-[12px] font-medium text-[#778480]"><Sparkles size={15} className="text-[#d28b48]" /> Route notes synced</div>
              <button className="text-[12px] font-bold text-[#3f7775] hover:underline">View logbook</button>
            </div>
          </footer>
        </aside>

        <section className="relative min-h-[640px] flex-1 overflow-hidden bg-[#d9e1dc]">
          <div className="absolute inset-0 opacity-80" style={{ backgroundImage: "linear-gradient(118deg, transparent 0 37%, rgba(255,255,255,.2) 37.1% 37.35%, transparent 37.45%), linear-gradient(35deg, transparent 0 58%, rgba(255,255,255,.26) 58.1% 58.32%, transparent 58.45%), radial-gradient(ellipse at 22% 30%, #c0d3cc 0%, transparent 32%), radial-gradient(ellipse at 75% 75%, #bccfc8 0%, transparent 35%)" }} />
          <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "linear-gradient(rgba(80,111,104,.22) 1px, transparent 1px), linear-gradient(90deg, rgba(80,111,104,.22) 1px, transparent 1px)", backgroundSize: "54px 54px" }} />
          <div className="absolute left-7 top-7 z-10 rounded-2xl border border-white/60 bg-[#f8f5ef]/90 px-4 py-3 shadow-[0_8px_24px_rgba(45,63,61,.08)] backdrop-blur">
            <p className="text-[10px] font-bold uppercase tracking-[0.19em] text-[#71837d]">Route overview</p>
            <div className="mt-1 flex items-center gap-2"><Route size={16} className="text-[#3f7775]" /><span className="text-sm font-semibold">{active.title} highlighted</span></div>
          </div>
          <div className="absolute right-7 top-7 z-10 flex flex-col gap-2">
            <button className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/70 bg-[#f8f5ef]/90 text-[#405a5c] shadow-sm">+</button>
            <button className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/70 bg-[#f8f5ef]/90 text-[#405a5c] shadow-sm">−</button>
          </div>
          <div className="absolute inset-x-[13%] top-[16%] h-[60%]">
            <svg viewBox="0 0 100 100" className="h-full w-full overflow-visible">
              <path d="M 14 72 C 27 63, 28 60, 37 54 S 48 44, 57 41 S 69 31, 78 24" fill="none" stroke="#f8f5ef" strokeWidth="4.8" strokeLinecap="round" opacity=".75" />
              <path d="M 14 72 C 27 63, 28 60, 37 54 S 48 44, 57 41 S 69 31, 78 24" fill="none" stroke="#d07455" strokeWidth="1.8" strokeDasharray="2.2 2.2" strokeLinecap="round" />
              {stops.map((stop) => (
                <g key={stop.id} onClick={() => setSelected(stop.id)} className="cursor-pointer">
                  <circle cx={stop.x} cy={stop.y} r={selected === stop.id ? "4.5" : "3.2"} fill={stop.color} stroke="#f8f5ef" strokeWidth="1.8" />
                  <circle cx={stop.x} cy={stop.y} r="7" fill="transparent" stroke={selected === stop.id ? stop.color : "transparent"} strokeWidth="1" opacity=".55" />
                </g>
              ))}
            </svg>
          </div>
          <div className="absolute bottom-7 left-7 right-7 z-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div className="rounded-2xl border border-white/60 bg-[#f8f5ef]/90 px-5 py-4 shadow-[0_8px_24px_rgba(45,63,61,.08)] backdrop-blur">
              <div className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7b8985]"><MapPin size={14} className="text-[#ef8354]" /> Selected stop</div>
              <p className="text-xl font-semibold tracking-[-0.04em]">{active.title}</p>
              <div className="mt-2 flex items-center gap-4 text-[12px] text-[#7f8c88]"><span className="flex items-center gap-1"><Clock3 size={13} /> {active.detail.split(" · ")[1]}</span><span className="flex items-center gap-1"><Fuel size={13} /> {active.distance} leg</span></div>
            </div>
            <button className="flex items-center justify-center gap-2 rounded-xl bg-[#273f48] px-5 py-3.5 text-[12px] font-bold text-[#f8f5ef] shadow-[0_8px_20px_rgba(39,63,72,.2)] transition hover:-translate-y-0.5">
              Open trip details <ArrowRight size={15} />
            </button>
          </div>
          <div className="absolute bottom-[175px] right-[14%] hidden items-center gap-2 rounded-full bg-[#f8f5ef]/80 px-3 py-2 text-[11px] font-semibold text-[#54706d] shadow-sm backdrop-blur sm:flex"><CircleDot size={13} /> Track recorded</div>
          <div className="absolute left-[12%] top-[45%] -rotate-12 text-[10px] font-bold tracking-[0.25em] text-[#70908a]/70">MONTEREY BAY</div>
        </section>
      </div>
    </main>
  );
}