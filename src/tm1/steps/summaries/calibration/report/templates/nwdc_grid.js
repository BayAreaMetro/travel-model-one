(function() {
  var purposes = $purposes;
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
    btn.textContent = 'Log';
    btn.style.cssText = 'position:absolute;top:4px;right:4px;padding:2px 6px;font-size:10px;cursor:pointer;z-index:10;opacity:0.7;';
    btn.onclick = function() {
      var cur = div.layout.yaxis.type;
      var newType = (cur === 'log') ? 'linear' : 'log';
      var fmt = (newType === 'log') ? '.1e' : '.1%';
      Plotly.relayout(div, {'yaxis.type': newType, 'yaxis.tickformat': fmt});
      btn.textContent = (newType === 'log') ? 'Lin' : 'Log';
    };
    div.style.position = 'relative';
    div.appendChild(btn);
  });
})();
