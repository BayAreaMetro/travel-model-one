(function() {
  var purposes = $purposes;
  var btnCss = 'margin:4px 0;padding:3px 8px;font-size:11px;cursor:pointer;';
  purposes.forEach(function(p) {
    Plotly.newPlot(p.div_id, p.traces, {
      title: {text: p.title, font: {size: 13}},
      xaxis: {title: 'Distance (miles)', rangemode: 'nonnegative', range: [0, 30]},
      yaxis: {tickformat: '.1%'},
      legend: {orientation: 'h', y: -0.25, x: 0.5, xanchor: 'center'},
      margin: {t: 35, b: 60, l: 45, r: 10}
    }, {responsive: true});

    var div = document.getElementById(p.div_id);
    var btn = document.createElement('button');
    btn.textContent = 'Log Scale';
    btn.style.cssText = btnCss;
    btn.onclick = function() {
      var cur = div.layout.yaxis.type;
      var newType = (cur === 'log') ? 'linear' : 'log';
      var fmt = (newType === 'log') ? '.1e' : '.1%';
      Plotly.relayout(div, {'yaxis.type': newType, 'yaxis.tickformat': fmt});
      btn.textContent = (newType === 'log') ? 'Linear Scale' : 'Log Scale';
    };
    div.after(btn);
  });
})();
