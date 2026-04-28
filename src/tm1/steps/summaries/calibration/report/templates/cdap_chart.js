Plotly.newPlot('$div_id', [$traces], {
  barmode: 'group',
  title: 'Activity Pattern Shares by Person Type',
  yaxis: {tickformat: '.0%'},
  legend: {orientation: 'h', y: -0.25, x: 0.5, xanchor: 'center'},
  margin: {l: 60, r: 30, t: 40, b: 80},
  width: 900
});
