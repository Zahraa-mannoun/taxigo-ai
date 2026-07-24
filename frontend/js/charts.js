/**
 * Weekly earnings bar chart (Chart.js). Reads current theme colors from
 * CSS custom properties so it matches dark/light mode automatically.
 */
(function (global) {
  "use strict";

  let chartInstance = null;

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /**
   * @param {string} canvasId
   * @param {{date: string, earned: number, projected: number}[]} days
   * @param {string} lang
   */
  function renderWeeklyChart(canvasId, days, lang) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") return;

    const textColor = cssVar("--text-muted") || "#9aa1b2";
    const gridColor = cssVar("--border") || "#2a2f3d";
    const earnedColor = cssVar("--success") || "#3ec98d";
    const projectedColor = cssVar("--accent") || "#f5a623";

    const labels = days.map((d) => {
      if (lang === "ar" || lang === "fr") {
        // Same month-name vocabulary as everywhere else in the app; year is
        // dropped here since all 7 bars are always within a single week.
        return TaxiGoI18n.formatDate(d.date, lang, false);
      }
      const date = new Date(`${d.date}T00:00:00`);
      return date.toLocaleDateString("en-US", { weekday: "short", day: "numeric" }); // en: unchanged
    });

    const earnedLabel = TaxiGoI18n.t("earnedLabel", lang);
    const projectedLabel = TaxiGoI18n.t("projectedLabel", lang);

    if (chartInstance) {
      chartInstance.destroy();
    }

    chartInstance = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: earnedLabel,
            data: days.map((d) => Number(d.earned)),
            backgroundColor: earnedColor,
            borderRadius: 6,
            maxBarThickness: 28,
          },
          {
            label: projectedLabel,
            data: days.map((d) => Number(d.projected)),
            backgroundColor: projectedColor,
            borderRadius: 6,
            maxBarThickness: 28,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: textColor, boxWidth: 10, font: { size: 11 } },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${TaxiGoI18n.formatMoney(ctx.parsed.y, lang)}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: textColor, font: { size: 11 } },
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            ticks: { color: textColor, font: { size: 11 } },
            grid: { color: gridColor },
          },
        },
      },
    });
  }

  function destroyChart() {
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
  }

  global.TaxiGoCharts = { renderWeeklyChart, destroyChart };
})(window);
