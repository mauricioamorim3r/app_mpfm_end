import React from "react";
import { clamp, fmt3 } from "@/calculations";

// Mapa status → cor da CSS var (substitui ternário encadeado).
const STATUS_FILL = { Apta: "var(--green)", Restrita: "var(--amber)" };
const fillFor = (status) => STATUS_FILL[status] || "var(--red)";

/**
 * Mapa GVF × WLR com zonas (Preferencial / Aceitável / Crítica),
 * histórico colorido por status e ponto atual destacado.
 *
 * Props:
 *   id      — identificador único para defs de gradient/pattern do SVG
 *   height  — altura em px (300–500 ideal)
 *   r       — resultados {gvf, wlr}
 *   history — array com {gvf, wlr, status, t}
 */
export default function EnvelopeChart({ id, height = 330, r, history }) {
  const w = 1000, h = height;
  const ml = 58, mr = 26, mt = 34, mb = 42;
  const iw = w - ml - mr, ih = h - mt - mb;
  const x = (gvf) => ml + clamp(gvf, 0, 1) * iw;
  const y = (wlr) => mt + (1 - clamp(wlr, 0, 1)) * ih;
  const cx = x(r.gvf), cy = y(r.wlr);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height="100%" preserveAspectRatio="none">
      <defs>
        <pattern id={`grid-${id}`} width="64" height="38" patternUnits="userSpaceOnUse">
          <path d="M64 0H0V38" fill="none" stroke="var(--line)" strokeWidth="1" opacity=".55" />
        </pattern>
        <linearGradient id={`zone-${id}`} x1="0" x2="1">
          <stop offset="0" stopColor="var(--green)" stopOpacity=".14" />
          <stop offset=".58" stopColor="var(--amber)" stopOpacity=".13" />
          <stop offset="1" stopColor="var(--red)" stopOpacity=".16" />
        </linearGradient>
      </defs>
      <rect x={ml} y={mt} width={iw} height={ih} rx="8" fill={`url(#zone-${id})`} stroke="var(--line)" />
      <rect x={ml} y={mt} width={iw} height={ih} fill={`url(#grid-${id})`} />
      <path d={`M ${x(.16)} ${y(.78)} C ${x(.32)} ${y(.96)}, ${x(.61)} ${y(.98)}, ${x(.86)} ${y(.78)}`} fill="none" stroke="var(--cyan)" strokeDasharray="10 8" strokeWidth="3" />
      <path d={`M ${x(.12)} ${y(.78)} L ${x(.30)} ${y(0)} M ${x(.88)} ${y(.78)} L ${x(.66)} ${y(0)}`} stroke="var(--magenta)" strokeWidth="3" strokeDasharray="8 6" />
      <path d={`M ${x(.18)} ${y(.52)} C ${x(.37)} ${y(.68)}, ${x(.62)} ${y(.70)}, ${x(.82)} ${y(.52)}`} fill="none" stroke="var(--blue)" strokeWidth="3" />
      <text x={x(.40)} y={y(.83)} fill="var(--cyan)" fontSize="24" fontWeight="800">ZONA PREFERENCIAL</text>
      <text x={x(.42)} y={y(.53)} fill="var(--blue)" fontSize="24" fontWeight="800">ZONA ACEITÁVEL</text>
      <text x={x(.05)} y={y(.25)} fill="var(--magenta)" fontSize="24" fontWeight="800">ZONA CRÍTICA</text>
      <text x={x(.72)} y={y(.25)} fill="var(--magenta)" fontSize="24" fontWeight="800">ZONA CRÍTICA</text>
      {history.map((d) => (
        <circle
          key={`hist-${d.t}`}
          cx={x(d.gvf)} cy={y(d.wlr)} r="4"
          fill={fillFor(d.status)}
          opacity=".75"
        >
          <title>{`${d.t} | GVF ${d.gvf} | WLR ${d.wlr}`}</title>
        </circle>
      ))}
      <line x1={cx} x2={cx} y1={mt} y2={mt + ih} stroke="var(--green)" opacity=".7" />
      <line x1={ml} x2={ml + iw} y1={cy} y2={cy} stroke="var(--green)" opacity=".35" />
      <circle cx={cx} cy={cy} r="10" fill="var(--green)" stroke="var(--surface)" strokeWidth="4" />
      <text x={cx + 18} y={cy - 4} fill="var(--text)" fontSize="18" fontWeight="850">Atual</text>
      <text x={cx + 18} y={cy + 18} fill="var(--text)" fontSize="15">{`GVF ${fmt3.format(r.gvf)} | WLR ${fmt3.format(r.wlr)}`}</text>
      <text x={ml + iw / 2} y={h - 10} fill="var(--muted)" textAnchor="middle" fontSize="15">GVF (-)</text>
      <text transform={`translate(16 ${mt + ih / 2}) rotate(-90)`} fill="var(--muted)" textAnchor="middle" fontSize="15">WLR (m³/m³)</text>
    </svg>
  );
}
