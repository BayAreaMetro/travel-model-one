Plotly.newPlot('$div_id', [$traces], {
  title: 'TLFD — $trip_title',
  xaxis: {title: 'Distance (miles)'},
  yaxis: {title: 'Share', tickformat: '.1%'}
});
(function() {
  var div = document.getElementById('$div_id');
  var btn = document.createElement('button');
  btn.textContent = 'Toggle Log Scale';
  btn.style.cssText = 'margin:4px 0;padding:4px 10px;font-size:12px;cursor:pointer;';
  btn.onclick = function() {
    var cur = div.layout.yaxis.type;
    var newType = (cur === 'log') ? 'linear' : 'log';
    var fmt = (newType === 'log') ? '.1e' : '.1%';
    Plotly.relayout(div, {'yaxis.type': newType, 'yaxis.tickformat': fmt});
  };
  div.parentNode.insertBefore(btn, div.nextSibling);
})();
