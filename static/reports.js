(function() {
  const annotationPlugin = {
    id: 'reportAnnotations',
    afterDraw(chart, args, opts) {
      const { ctx, chartArea, scales } = chart;
      if (!chartArea) return;
      const yScale = scales.y;
      const xScale = scales.x;
      ctx.save();
      if (opts.band) {
        const from = opts.band.from;
        const to = opts.band.to;
        if (from !== undefined && to !== undefined && yScale) {
          const yTop = yScale.getPixelForValue(to);
          const yBottom = yScale.getPixelForValue(from);
          ctx.fillStyle = opts.band.color || 'rgba(14,165,164,0.08)';
          ctx.fillRect(chartArea.left, Math.min(yTop, yBottom), chartArea.right - chartArea.left, Math.abs(yBottom - yTop));
        }
      }
      if (opts.horizontal && yScale) {
        opts.horizontal.forEach(line => {
          const y = yScale.getPixelForValue(line.value);
          ctx.strokeStyle = line.color || 'rgba(249, 115, 22, 0.7)';
          ctx.setLineDash([6, 6]);
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(chartArea.left, y);
          ctx.lineTo(chartArea.right, y);
          ctx.stroke();
          if (line.label) {
            ctx.fillStyle = line.color || '#334155';
            ctx.fillText(line.label, chartArea.left + 6, y - 6);
          }
        });
      }
      if (opts.vertical && xScale) {
        opts.vertical.forEach(line => {
          const x = xScale.getPixelForValue(line.label);
          ctx.strokeStyle = line.color || 'rgba(99,102,241,0.6)';
          ctx.setLineDash([4, 4]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(x, chartArea.top);
          ctx.lineTo(x, chartArea.bottom);
          ctx.stroke();
          if (line.labelText) {
            ctx.fillStyle = line.color || '#334155';
            ctx.fillText(line.labelText, x + 4, chartArea.top + 12);
          }
        });
      }
      ctx.restore();
    },
  };

  function applyMode(isBeginner) {
    document.body.classList.toggle('expert-mode', !isBeginner);
  }

  function labelFromIso(iso) {
    if (!iso) return '';
    try {
      return iso.substring(11, 16);
    } catch (_) {
      return iso;
    }
  }

  function renderLightChart(data) {
    const el = document.getElementById('lightChart');
    if (!el || !window.Chart) return;
    const hourly = Array.isArray(data.hourly) ? data.hourly : [];
    const labels = hourly.map(h => labelFromIso(h.time));
    const lux = hourly.map(h => h.lux);
    const shortwave = hourly.map(h => h.shortwave);
    const gti = hourly.map(h => h.gti);
    const threshold = data.indoor?.light?.threshold;
    const sunrise = labelFromIso(data.weather?.sunrise);
    const sunset = labelFromIso(data.weather?.sunset);
    new Chart(el, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'İç Lux', data: lux, borderColor: '#0ea5a4', backgroundColor: 'rgba(14,165,164,0.2)', tension: 0.3, spanGaps: true },
          { label: 'Kısa dalga (dış)', data: shortwave, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.15)', tension: 0.3, spanGaps: true, yAxisID: 'y1' },
          { label: 'GTI (dış)', data: gti, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.12)', tension: 0.3, spanGaps: true, yAxisID: 'y1' },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: 'Lux' } },
          y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'W/m²' } },
        },
        plugins: {
          legend: { display: true },
          reportAnnotations: {
            horizontal: threshold ? [{ value: threshold, label: `Eşik ${threshold} lux`, color: 'rgba(244,63,94,0.6)' }] : [],
            vertical: [
              sunrise ? { label: sunrise, labelText: 'Gündoğumu', color: 'rgba(16,185,129,0.5)' } : null,
              sunset ? { label: sunset, labelText: 'Günbatımı', color: 'rgba(239,68,68,0.5)' } : null,
            ].filter(Boolean),
          },
        },
      },
      plugins: [annotationPlugin],
    });
  }

  function renderTempChart(data) {
    const el = document.getElementById('tempChart');
    if (!el || !window.Chart) return;
    const hourly = Array.isArray(data.hourly) ? data.hourly : [];
    const labels = hourly.map(h => labelFromIso(h.time));
    const tempIn = hourly.map(h => h.temp_in);
    const dew = hourly.map(h => h.dew_point);
    const tempOut = hourly.map(h => h.temp_out);
    const delta = hourly.map(h => h.temp_delta);
    const margin = hourly.map(h => h.dew_margin);
    const bandFrom = data.thresholds?.TEMP_OK_MIN;
    const bandTo = data.thresholds?.TEMP_OK_MAX;
    new Chart(el, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'İç sıcaklık', data: tempIn, borderColor: '#0ea5a4', backgroundColor: 'rgba(14,165,164,0.2)', tension: 0.3, spanGaps: true },
          { label: 'Çiğ noktası', data: dew, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.15)', tension: 0.3, spanGaps: true },
          { label: 'Dış sıcaklık', data: tempOut, borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.12)', tension: 0.3, spanGaps: true },
          { label: 'ΔT (iç-dış)', data: delta, borderColor: '#64748b', backgroundColor: 'rgba(100,116,139,0.12)', tension: 0.3, spanGaps: true, yAxisID: 'y1' },
          { label: 'Dew marjı', data: margin, borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.14)', tension: 0.3, spanGaps: true, yAxisID: 'y1' },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        scales: {
          y: { title: { display: true, text: '°C' } },
          y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'ΔT' } },
        },
        plugins: {
          legend: { display: true },
          reportAnnotations: {
            band: (bandFrom !== undefined && bandTo !== undefined) ? { from: bandFrom, to: bandTo, color: 'rgba(16,185,129,0.08)' } : null,
          },
        },
      },
      plugins: [annotationPlugin],
    });
  }

  function renderWeeklyChart(data) {
    const el = document.getElementById('weeklyChart');
    if (!el || !window.Chart) return;
    const days = Array.isArray(data.days) ? data.days : [];
    const labels = days.map(d => d.date || d.end_date || '');
    const light = days.map(d => d.indoor?.light?.light_dose_lux_hours);
    const stress = days.map(d => d.plants?.stress_hours);
    const gdd = days.map(d => d.plants?.gdd);
    new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Işık dozu', data: light, backgroundColor: 'rgba(14,165,164,0.5)' },
          { label: 'Stres saatleri', data: stress, backgroundColor: 'rgba(248,113,113,0.6)' },
          { label: 'GDD', data: gdd, backgroundColor: 'rgba(99,102,241,0.6)' },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  function initDailyReport() {
    const data = window.reportData || {};
    const toggle = document.getElementById('modeToggle');
    const defaultBeginner = data.config?.BEGINNER_MODE_DEFAULT !== false;
    applyMode(defaultBeginner);
    if (toggle) {
      toggle.checked = defaultBeginner;
      toggle.addEventListener('change', () => applyMode(toggle.checked));
    }
    renderLightChart(data);
    renderTempChart(data);
  }

  function initWeeklyReport() {
    const data = window.reportData || {};
    const toggle = document.getElementById('modeToggle');
    const defaultBeginner = data.config?.BEGINNER_MODE_DEFAULT !== false;
    applyMode(defaultBeginner);
    if (toggle) {
      toggle.checked = defaultBeginner;
      toggle.addEventListener('change', () => applyMode(toggle.checked));
    }
    renderWeeklyChart(data);
  }

  window.initDailyReport = initDailyReport;
  window.initWeeklyReport = initWeeklyReport;
})();
