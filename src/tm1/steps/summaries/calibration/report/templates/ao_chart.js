Plotly.newPlot('$div_id', [$traces], {
  barmode: 'stack',
  title: 'Auto Ownership Distribution by County',
  xaxis: {tickformat: '.0%', title: 'Share', range: [0, 1]},
  yaxis: {automargin: true},
  legend: {orientation: 'h', y: -0.08, x: 0.5, xanchor: 'center', traceorder: 'normal'},
  margin: {l: 220, b: 60}
}, {responsive: true});
