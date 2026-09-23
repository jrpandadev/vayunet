import { useEffect, useRef } from "react";
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
  type Plugin,
  type ScriptableContext,
} from "chart.js";

Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip
);

// 72h horizon, 3h resolution → 25 samples. Markers at 0 / 24 / 48 / 72.
const HOURS = Array.from({ length: 25 }, (_, i) => i * 3);
const SERIES = [
  142, 146, 150, 155, 160, 165, 170, 175, 180, 184, 188, 191, 194, 196, 197,
  198, 198, 196, 192, 186, 179, 171, 163, 155, 149,
];
const MARKED = [0, 8, 16, 24];
const MARK_LABELS = ["NOW", "+24H", "+48H", "+72H"];

function lineGradient(ctx: ScriptableContext<"line">) {
  const { chart } = ctx;
  const { ctx: c, chartArea } = chart;
  if (!chartArea) return "#f5a524";
  const g = c.createLinearGradient(chartArea.left, 0, chartArea.right, 0);
  g.addColorStop(0, "#f5a524");
  g.addColorStop(0.5, "#ef4444");
  g.addColorStop(1, "#f87171");
  return g;
}

function fillGradient(ctx: ScriptableContext<"line">) {
  const { chart } = ctx;
  const { ctx: c, chartArea } = chart;
  if (!chartArea) return "rgba(239,68,68,0.15)";
  const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  g.addColorStop(0, "rgba(239,68,68,0.30)");
  g.addColorStop(0.6, "rgba(239,68,68,0.08)");
  g.addColorStop(1, "rgba(239,68,68,0)");
  return g;
}

/** Dashed vertical guides at the 24 / 48 / 72h markers. */
const dashedGuides: Plugin<"line"> = {
  id: "dashedGuides",
  beforeDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    const x = scales.x;
    if (!x || !chartArea) return;
    ctx.save();
    ctx.strokeStyle = "rgba(148,163,184,0.16)";
    ctx.setLineDash([3, 4]);
    ctx.lineWidth = 1;
    for (const i of MARKED.slice(1)) {
      const px = x.getPixelForValue(i);
      ctx.beginPath();
      ctx.moveTo(px, chartArea.top);
      ctx.lineTo(px, chartArea.bottom);
      ctx.stroke();
    }
    ctx.restore();
  },
};

export default function ForecastChart() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const mono = { family: "'IBM Plex Mono', monospace", size: 10 };

    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: HOURS.map(String),
        datasets: [
          {
            data: SERIES,
            borderColor: lineGradient,
            backgroundColor: fillGradient,
            fill: true,
            borderWidth: 2,
            tension: 0.42,
            pointRadius: (c) => (MARKED.includes(c.dataIndex) ? 3.5 : 0),
            pointHoverRadius: (c) => (MARKED.includes(c.dataIndex) ? 5 : 3),
            pointBackgroundColor: "#0a1626",
            pointBorderColor: (c) =>
              c.dataIndex <= 8 ? "#f5a524" : "#ef4444",
            pointBorderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1500, easing: "easeOutQuart" },
        layout: { padding: { top: 6, right: 4 } },
        plugins: {
          tooltip: {
            backgroundColor: "rgba(10,22,38,0.95)",
            borderColor: "rgba(53,219,232,0.3)",
            borderWidth: 1,
            titleFont: { ...mono, size: 10 },
            bodyFont: { ...mono, size: 11 },
            titleColor: "#7d8ea6",
            bodyColor: "#e6edf6",
            displayColors: false,
            padding: 10,
            cornerRadius: 6,
            callbacks: {
              title: (items) => `T+${items[0].label}H`,
              label: (item) => `PM2.5  ${item.parsed.y} µg/m³`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              autoSkip: false,
              maxRotation: 0,
              font: mono,
              color: "#64748b",
              padding: 6,
              callback: (_v, index) => {
                const m = MARKED.indexOf(index);
                return m === -1 ? "" : MARK_LABELS[m];
              },
            },
          },
          y: {
            min: 50,
            max: 250,
            grid: { color: "rgba(148,163,184,0.08)" },
            border: { display: false, dash: [3, 4] },
            ticks: {
              stepSize: 100,
              font: mono,
              color: "#64748b",
              padding: 8,
            },
          },
        },
      },
      plugins: [dashedGuides],
    });

    return () => chart.destroy();
  }, []);

  return (
    <div className="relative h-[176px] w-full">
      <canvas ref={canvasRef} role="img" aria-label="72 hour PM2.5 forecast for Delhi NCR, peaking near 198 micrograms per cubic metre at plus 48 hours" />
    </div>
  );
}
