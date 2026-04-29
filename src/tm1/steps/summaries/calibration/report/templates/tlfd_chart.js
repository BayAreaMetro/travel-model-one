(function() {
  var traces = $traces_json;
  Plotly.newPlot('$div_id', traces, {
    title: 'TLFD — $trip_title',
    xaxis: {title: 'Distance (miles)', rangemode: 'nonnegative'},
    yaxis: {title: 'Share', tickformat: '.1%'},
    legend: {orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center'},
    margin: {b: 60}
  });
  var div = document.getElementById('$div_id');
  var btn = document.createElement('button');
  btn.textContent = 'Log Scale';
  btn.style.cssText = 'margin:4px 0;padding:3px 8px;font-size:11px;cursor:pointer;';
  btn.onclick = function() {
    var cur = div.layout.yaxis.type;
    var newType = (cur === 'log') ? 'linear' : 'log';
    var fmt = (newType === 'log') ? '.1e' : '.1%';
    Plotly.relayout(div, {'yaxis.type': newType, 'yaxis.tickformat': fmt});
    btn.textContent = (newType === 'log') ? 'Linear Scale' : 'Log Scale';
  };
  div.parentNode.insertBefore(btn, div.nextSibling);
})();
