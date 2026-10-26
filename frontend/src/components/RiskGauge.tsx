import { RISK_STYLE } from "../lib";

interface Props {
  probability: number;
  level: keyof typeof RISK_STYLE;
  bands: [number, string][];
}

const R = 88;
const CX = 110;
const CY = 104;

function polar(t: number, r = R) {
  const a = Math.PI * (1 - t);
  return [CX + r * Math.cos(a), CY - r * Math.sin(a)];
}

function arc(t0: number, t1: number) {
  const [x0, y0] = polar(t0);
  const [x1, y1] = polar(t1);
  return `M ${x0} ${y0} A ${R} ${R} 0 0 1 ${x1} ${y1}`;
}

export default function RiskGauge({ probability, level, bands }: Props) {
  const style = RISK_STYLE[level];
  const cuts = [0, ...bands.map((b) => b[0]), 1];
  const colors = ["#10b981", "#f59e0b", "#ef4444"];
  const angle = -90 + probability * 180;

  return (
    <svg viewBox="0 0 220 128" className="w-full max-w-[280px]" role="img"
         aria-label={`Predicted risk ${Math.round(probability * 100)} percent`}>
      {cuts.slice(0, -1).map((c, i) => (
        <path key={i} d={arc(c + 0.004, cuts[i + 1] - 0.004)} stroke={colors[i]} strokeOpacity={0.18}
              strokeWidth={16} fill="none" strokeLinecap="butt" />
      ))}
      <path d={arc(0, 1)} stroke={style.color} strokeWidth={16} fill="none" pathLength={1}
            strokeDasharray={1} strokeDashoffset={1 - probability}
            style={{ transition: "stroke-dashoffset 0.6s cubic-bezier(.2,.8,.2,1), stroke 0.4s" }} />
      <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: `${CX}px ${CY}px`,
                  transition: "transform 0.6s cubic-bezier(.2,.8,.2,1)" }}>
        <line x1={CX} y1={CY} x2={CX} y2={CY - R + 22} stroke="#0f172a" strokeWidth={3} strokeLinecap="round" />
      </g>
      <circle cx={CX} cy={CY} r={7} fill="#0f172a" />
      <circle cx={CX} cy={CY} r={3} fill="white" />
      <text x={CX - R} y={CY + 18} textAnchor="middle" className="fill-slate-400 text-[10px]">0%</text>
      <text x={CX + R} y={CY + 18} textAnchor="middle" className="fill-slate-400 text-[10px]">100%</text>
    </svg>
  );
}
