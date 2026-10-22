"use client";

/**
 * Small inline SVG charts. They follow one system: thin marks (≤24px) with
 * 4px rounded data-ends anchored to the baseline, a 2px surface gap between
 * adjacent fills, recessive hairline grid, text in ink tokens (never the
 * series color), a legend whenever two series are shown, and a hover tooltip
 * on every mark. The data tables beside them remain the accessible view.
 */

import { ReactNode, useId, useState } from "react";
import { compactMoney, money, percent } from "@/lib/format";

const SERIES = ["var(--color-series-1)", "var(--color-series-2)"] as const;

type Bar = { label: string; values: [number, number?] };

export function CashFlowChart({ years, recurring, exit, onPanel }: { years: number[]; recurring: number[]; exit: number; onPanel?: boolean }) {
  const [hover, setHover] = useState<number | null>(null);
  const id = useId();
  const bars: Bar[] = years.map((year, index) => ({
    label: "Year " + year,
    values: [recurring[index], index === years.length - 1 ? exit : undefined],
  }));
  const width = 560;
  const height = 200;
  const pad = { top: 16, right: 12, bottom: 28, left: 56 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const totals = bars.map((bar) => (bar.values[0] > 0 ? bar.values[0] : 0) + (bar.values[1] ?? 0));
  const minimum = Math.min(0, ...bars.map((bar) => bar.values[0]));
  const maximum = Math.max(1, ...totals);
  const scale = (value: number) => pad.top + plotH - ((value - minimum) / (maximum - minimum)) * plotH;
  const baseline = scale(0);
  const slot = plotW / bars.length;
  const barW = Math.min(24, slot * 0.6);
  const ticks = niceTicks(minimum, maximum, 4);
  const ink = onPanel ? "var(--color-panel-muted)" : "var(--color-ink-muted)";
  const grid = onPanel ? "var(--color-panel-line)" : "var(--color-line)";
  const surface = onPanel ? "var(--color-panel)" : "var(--color-surface)";

  return (
    <figure className="m-0">
      <div className="mb-2 flex flex-wrap items-center gap-4 text-xs" style={{ color: ink }}>
        <LegendSwatch color={SERIES[0]}>Recurring cash flow</LegendSwatch>
        <LegendSwatch color={SERIES[1]}>Net exit proceeds</LegendSwatch>
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={id} className="block h-auto w-full">
          <title id={id}>Equity cash flow by year, recurring cash flow with exit proceeds in the final year</title>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={pad.left} x2={width - pad.right} y1={scale(tick)} y2={scale(tick)} stroke={grid} strokeWidth={1} />
              <text x={pad.left - 8} y={scale(tick)} dy="0.32em" textAnchor="end" fontSize={10} fill={ink}>
                {compactMoney(tick)}
              </text>
            </g>
          ))}
          <line x1={pad.left} x2={width - pad.right} y1={baseline} y2={baseline} stroke={ink} strokeWidth={1} />
          {bars.map((bar, index) => {
            const x = pad.left + slot * index + (slot - barW) / 2;
            const recurringValue = bar.values[0];
            const exitValue = bar.values[1];
            const recurringTop = scale(Math.max(recurringValue, 0));
            const recurringBottom = scale(Math.min(recurringValue, 0));
            const recurringH = Math.max(recurringBottom - recurringTop, 0);
            const exitTop = exitValue !== undefined ? scale(Math.max(recurringValue, 0) + exitValue) : null;
            const dim = hover !== null && hover !== index;
            return (
              <g key={bar.label} opacity={dim ? 0.45 : 1} onMouseEnter={() => setHover(index)} onMouseLeave={() => setHover(null)}>
                <rect x={pad.left + slot * index} y={pad.top} width={slot} height={plotH} fill="transparent" />
                {recurringH > 0 && <path d={roundedRect(x, recurringTop, barW, recurringH, 4, recurringValue >= 0 ? "top" : "bottom")} fill={SERIES[0]} />}
                {exitTop !== null && exitValue !== undefined && exitValue > 0 && (
                  <>
                    <rect x={x} y={recurringTop - 2} width={barW} height={2} fill={surface} />
                    <path d={roundedRect(x, exitTop, barW, recurringTop - 2 - exitTop, 4, "top")} fill={SERIES[1]} />
                  </>
                )}
                <text x={x + barW / 2} y={height - 10} textAnchor="middle" fontSize={11} fill={ink}>
                  {bar.label.replace("Year ", "Y")}
                </text>
              </g>
            );
          })}
        </svg>
        {hover !== null && (
          <Tooltip left={((pad.left + slot * hover + slot / 2) / width) * 100}>
            <p className="font-semibold">{bars[hover].label}</p>
            <p className="tabular">Recurring: {money(bars[hover].values[0])}</p>
            {bars[hover].values[1] !== undefined && <p className="tabular">Exit proceeds: {money(bars[hover].values[1])}</p>}
          </Tooltip>
        )}
      </div>
    </figure>
  );
}

/** Distribution of simulated outcomes with the target and base case marked. */
export function Histogram({
  bins,
  target,
  base,
  format = percent,
}: {
  bins: { lower: number; upper: number; count: number }[];
  target?: number | null;
  base?: number | null;
  format?: (value: number) => string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const id = useId();
  const width = 560;
  const height = 200;
  const pad = { top: 18, right: 12, bottom: 30, left: 40 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const low = bins[0]?.lower ?? 0;
  const high = bins[bins.length - 1]?.upper ?? 1;
  const span = high - low || 1;
  const x = (value: number) => pad.left + ((value - low) / span) * plotW;
  const maxCount = Math.max(1, ...bins.map((bin) => bin.count));
  const total = bins.reduce((sum, bin) => sum + bin.count, 0) || 1;
  const y = (count: number) => pad.top + plotH - (count / maxCount) * plotH;
  const ticks = niceTicks(0, maxCount, 3);
  const xTicks = [low, low + span * 0.25, low + span * 0.5, low + span * 0.75, high];
  const ink = "var(--color-ink-muted)";
  const grid = "var(--color-line)";
  return (
    <figure className="m-0">
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={id} className="block h-auto w-full">
          <title id={id}>Histogram of simulated levered IRR outcomes</title>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke={grid} strokeWidth={1} />
              <text x={pad.left - 6} y={y(tick)} dy="0.32em" textAnchor="end" fontSize={10} fill={ink}>
                {tick}
              </text>
            </g>
          ))}
          {bins.map((bin, index) => {
            const left = x(bin.lower) + 1;
            const right = x(bin.upper) - 1;
            const barW = Math.max(right - left, 1);
            const top = y(bin.count);
            const h = pad.top + plotH - top;
            const dim = hover !== null && hover !== index;
            return (
              <g key={index} opacity={dim ? 0.45 : 1} onMouseEnter={() => setHover(index)} onMouseLeave={() => setHover(null)}>
                <rect x={x(bin.lower)} y={pad.top} width={x(bin.upper) - x(bin.lower)} height={plotH} fill="transparent" />
                {h > 0 && <path d={roundedRect(left, top, barW, h, Math.min(4, barW / 2), "top")} fill={SERIES[0]} />}
              </g>
            );
          })}
          <line x1={pad.left} x2={width - pad.right} y1={pad.top + plotH} y2={pad.top + plotH} stroke={ink} strokeWidth={1} />
          {xTicks.map((tick) => (
            <text key={tick} x={x(tick)} y={height - 10} textAnchor="middle" fontSize={10} fill={ink}>
              {format(tick)}
            </text>
          ))}
          {base !== null && base !== undefined && base >= low && base <= high && (
            <g>
              <line x1={x(base)} x2={x(base)} y1={pad.top - 4} y2={pad.top + plotH} stroke="var(--color-ink)" strokeWidth={2} />
              <text x={x(base)} y={pad.top - 7} textAnchor="middle" fontSize={10} fill="var(--color-ink)">
                base
              </text>
            </g>
          )}
          {target !== null && target !== undefined && target >= low && target <= high && (
            <g>
              <line x1={x(target)} x2={x(target)} y1={pad.top - 4} y2={pad.top + plotH} stroke={ink} strokeWidth={2} strokeDasharray="4 3" />
              <text x={x(target)} y={pad.top - 7} textAnchor="middle" fontSize={10} fill={ink}>
                target
              </text>
            </g>
          )}
        </svg>
        {hover !== null && bins[hover] && (
          <Tooltip left={((x(bins[hover].lower) + x(bins[hover].upper)) / 2 / width) * 100}>
            <p className="font-semibold">
              {format(bins[hover].lower)} to {format(bins[hover].upper)}
            </p>
            <p className="tabular">
              {bins[hover].count.toLocaleString()} cases · {percent(bins[hover].count / total)}
            </p>
          </Tooltip>
        )}
      </div>
    </figure>
  );
}

/** Horizontal tornado: each driver's IRR at its sampled P10 and P90 around the base case. */
export function Tornado({
  items,
  base,
  format = percent,
}: {
  items: { label: string; low: number; high: number; lowInput: string; highInput: string }[];
  base: number;
  format?: (value: number) => string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const id = useId();
  const width = 560;
  const rowH = 30;
  const pad = { top: 22, right: 16, bottom: 10, left: 120 };
  const height = pad.top + items.length * rowH + pad.bottom;
  const plotW = width - pad.left - pad.right;
  const extent = Math.max(0.005, ...items.flatMap((item) => [Math.abs(item.low - base), Math.abs(item.high - base)]));
  const x = (value: number) => pad.left + plotW / 2 + ((value - base) / extent) * (plotW / 2);
  const ink = "var(--color-ink-muted)";
  const sorted = [...items].sort((a, b) => Math.abs(b.high - b.low) - Math.abs(a.high - a.low));
  return (
    <figure className="m-0">
      <div className="mb-2 flex flex-wrap items-center gap-4 text-xs" style={{ color: ink }}>
        <LegendSwatch color={SERIES[1]}>IRR at the driver&apos;s P10 draw</LegendSwatch>
        <LegendSwatch color={SERIES[0]}>IRR at the driver&apos;s P90 draw</LegendSwatch>
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={id} className="block h-auto w-full">
          <title id={id}>Tornado chart of levered IRR by driver</title>
          <line x1={x(base)} x2={x(base)} y1={pad.top - 8} y2={height - pad.bottom} stroke="var(--color-ink)" strokeWidth={1} />
          <text x={x(base)} y={pad.top - 11} textAnchor="middle" fontSize={10} fill="var(--color-ink)">
            base {format(base)}
          </text>
          {sorted.map((item, index) => {
            const yTop = pad.top + index * rowH + 6;
            const h = rowH - 12;
            const dim = hover !== null && hover !== index;
            const segments = [
              { value: item.low, color: SERIES[1] },
              { value: item.high, color: SERIES[0] },
            ];
            return (
              <g key={item.label} opacity={dim ? 0.45 : 1} onMouseEnter={() => setHover(index)} onMouseLeave={() => setHover(null)}>
                <rect x={0} y={pad.top + index * rowH} width={width} height={rowH} fill="transparent" />
                <text x={pad.left - 10} y={yTop + h / 2} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--color-ink)">
                  {item.label}
                </text>
                {segments.map((segment) => {
                  const start = Math.min(x(base), x(segment.value));
                  const end = Math.max(x(base), x(segment.value));
                  const w = Math.max(end - start - 1, 0);
                  if (w <= 0) return null;
                  const leftSide = segment.value < base;
                  return <path key={segment.color} d={roundedRect(leftSide ? start : start + 1, yTop, w, h, 4, leftSide ? "left" : "right")} fill={segment.color} />;
                })}
              </g>
            );
          })}
        </svg>
        {hover !== null && sorted[hover] && (
          <Tooltip left={50}>
            <p className="font-semibold">{sorted[hover].label}</p>
            <p className="tabular">
              At P10 input {sorted[hover].lowInput}: IRR {format(sorted[hover].low)}
            </p>
            <p className="tabular">
              At P90 input {sorted[hover].highInput}: IRR {format(sorted[hover].high)}
            </p>
          </Tooltip>
        )}
      </div>
    </figure>
  );
}

/** A P10–P90 range bar with the median marked, used for simulation summaries. */
export function RangeBar({
  low,
  median,
  high,
  target,
  minimum,
  maximum,
  format = percent,
}: {
  low: number;
  median: number;
  high: number;
  target?: number | null;
  minimum: number;
  maximum: number;
  format?: (value: number) => string;
}) {
  const span = maximum - minimum || 1;
  const position = (value: number) => ((value - minimum) / span) * 100;
  return (
    <div className="pt-5">
      <div className="relative h-3 rounded-full bg-surface-muted ring-1 ring-inset ring-line">
        <div className="absolute inset-y-0 rounded-full bg-primary/30" style={{ left: `${position(low)}%`, width: `${Math.max(position(high) - position(low), 1)}%` }} />
        <div className="absolute -inset-y-1 w-0.5 rounded bg-primary" style={{ left: `calc(${position(median)}% - 1px)` }} />
        {target !== null && target !== undefined && (
          <div className="absolute -inset-y-2 w-0.5 border-l-2 border-dashed border-ink-muted" style={{ left: `calc(${position(target)}% - 1px)` }} title={"Target " + format(target)} />
        )}
      </div>
      <div className="tabular relative mt-1.5 h-4 text-[11px] text-ink-muted">
        <span className="absolute -translate-x-1/2" style={{ left: `${position(low)}%` }}>
          P10 {format(low)}
        </span>
        <span className="absolute -translate-x-1/2 font-semibold text-ink" style={{ left: `${position(median)}%` }}>
          {format(median)}
        </span>
        <span className="absolute -translate-x-1/2" style={{ left: `${position(high)}%` }}>
          P90 {format(high)}
        </span>
      </div>
    </div>
  );
}

function Tooltip({ left, children }: { left: number; children: ReactNode }) {
  return (
    <div
      className="pointer-events-none absolute top-2 z-10 rounded-lg border border-line bg-surface px-3 py-2 text-xs text-ink shadow-md"
      style={{ left: `${Math.min(Math.max(left, 15), 85)}%`, transform: "translateX(-50%)" }}
    >
      {children}
    </div>
  );
}

function LegendSwatch({ color, children }: { color: string; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {children}
    </span>
  );
}

function roundedRect(x: number, y: number, w: number, h: number, r: number, end: "top" | "bottom" | "left" | "right") {
  const radius = Math.max(0, Math.min(r, w / 2, h / 2));
  if (end === "top") {
    return `M${x},${y + h} V${y + radius} Q${x},${y} ${x + radius},${y} H${x + w - radius} Q${x + w},${y} ${x + w},${y + radius} V${y + h} Z`;
  }
  if (end === "bottom") {
    return `M${x},${y} H${x + w} V${y + h - radius} Q${x + w},${y + h} ${x + w - radius},${y + h} H${x + radius} Q${x},${y + h} ${x},${y + h - radius} Z`;
  }
  if (end === "right") {
    return `M${x},${y} H${x + w - radius} Q${x + w},${y} ${x + w},${y + radius} V${y + h - radius} Q${x + w},${y + h} ${x + w - radius},${y + h} H${x} Z`;
  }
  return `M${x + w},${y} H${x + radius} Q${x},${y} ${x},${y + radius} V${y + h - radius} Q${x},${y + h} ${x + radius},${y + h} H${x + w} Z`;
}

function niceTicks(minimum: number, maximum: number, count: number): number[] {
  const range = maximum - minimum || 1;
  const rough = range / count;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((candidate) => candidate >= rough) ?? magnitude;
  const ticks: number[] = [];
  for (let tick = Math.ceil(minimum / step) * step; tick <= maximum + 1e-9; tick += step) ticks.push(Math.round(tick));
  return ticks;
}
