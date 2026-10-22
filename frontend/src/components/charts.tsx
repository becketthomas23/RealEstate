"use client";

/**
 * Small inline SVG charts. They follow one system: thin marks with 4px
 * rounded data-ends anchored to the baseline, a 2px surface gap between
 * adjacent fills, recessive grid lines, text in ink tokens (never the series
 * color), a legend whenever two series are shown, and a hover tooltip on
 * every mark. The data tables beside them remain the accessible view.
 */

import { useId, useState } from "react";
import { compactMoney, money, percent } from "@/lib/format";

const SERIES = ["var(--color-series-1)", "var(--color-series-2)"] as const;

type Bar = { label: string; values: [number, number?]; };

export function CashFlowChart({
  years,
  recurring,
  exit,
  onPanel,
}: {
  years: number[];
  recurring: number[];
  exit: number;
  onPanel?: boolean;
}) {
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
  const barW = Math.min(44, slot * 0.6);
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
                {recurringH > 0 && (
                  <path d={roundedRect(x, recurringTop, barW, recurringH, 4, recurringValue >= 0 ? "top" : "bottom")} fill={SERIES[0]} />
                )}
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
          <div
            className="pointer-events-none absolute top-2 rounded-lg border border-line bg-surface px-3 py-2 text-xs text-ink shadow-md"
            style={{ left: `${((pad.left + slot * hover + slot / 2) / width) * 100}%`, transform: "translateX(-50%)" }}
          >
            <p className="font-semibold">{bars[hover].label}</p>
            <p className="tabular">Recurring: {money(bars[hover].values[0])}</p>
            {bars[hover].values[1] !== undefined && <p className="tabular">Exit proceeds: {money(bars[hover].values[1])}</p>}
          </div>
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
        <div
          className="absolute inset-y-0 rounded-full bg-primary/30"
          style={{ left: `${position(low)}%`, width: `${Math.max(position(high) - position(low), 1)}%` }}
        />
        <div className="absolute -inset-y-1 w-0.5 rounded bg-primary" style={{ left: `calc(${position(median)}% - 1px)` }} />
        {target !== null && target !== undefined && (
          <div
            className="absolute -inset-y-2 w-0.5 border-l-2 border-dashed border-ink-muted"
            style={{ left: `calc(${position(target)}% - 1px)` }}
            title={"Target " + format(target)}
          />
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

function LegendSwatch({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {children}
    </span>
  );
}

function roundedRect(x: number, y: number, w: number, h: number, r: number, end: "top" | "bottom") {
  const radius = Math.min(r, w / 2, h);
  if (end === "top") {
    return `M${x},${y + h} V${y + radius} Q${x},${y} ${x + radius},${y} H${x + w - radius} Q${x + w},${y} ${x + w},${y + radius} V${y + h} Z`;
  }
  return `M${x},${y} H${x + w} V${y + h - radius} Q${x + w},${y + h} ${x + w - radius},${y + h} H${x + radius} Q${x},${y + h} ${x},${y + h - radius} Z`;
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
