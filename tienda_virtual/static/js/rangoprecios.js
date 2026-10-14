(function(){
  var slider = document.getElementById('price-slider');
  if (!slider) return;

  var sliderOne = document.getElementById('precio-min-range');
  var sliderTwo = document.getElementById('precio-max-range');
  var displayMin = document.getElementById('precio-min-val');
  var displayMax = document.getElementById('precio-max-val');
  var fill = slider.querySelector('.range-fill');

  function updateFill(){
    var min = parseFloat(sliderOne.min) || 0;
    var max = parseFloat(sliderOne.max) || 0;
    var v1 = parseFloat(sliderOne.value);
    var v2 = parseFloat(sliderTwo.value);
    var left = Math.min(v1, v2);
    var right = Math.max(v1, v2);
    var p1 = ((left - min) / (max - min)) * 100;
    var p2 = ((right - min) / (max - min)) * 100;
    fill.style.left = p1 + '%';
    fill.style.width = (p2 - p1) + '%';
    if (displayMin) displayMin.textContent = (left).toFixed(2);
    if (displayMax) displayMax.textContent = (right).toFixed(2);
  }

  var active = null;

  function pageX(e){ return e.touches ? e.touches[0].pageX : e.pageX; }

  function startDrag(e){
    var rect = slider.getBoundingClientRect();
    var x = pageX(e) - rect.left;
    var w = rect.width;
    var min = parseFloat(sliderOne.min) || 0;
    var max = parseFloat(sliderOne.max) || 0;
    var v1 = ((parseFloat(sliderOne.value) - min) / (max - min)) * w;
    var v2 = ((parseFloat(sliderTwo.value) - min) / (max - min)) * w;
    var d1 = Math.abs(x - v1);
    var d2 = Math.abs(x - v2);
    active = (d1 <= d2) ? sliderOne : sliderTwo;
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('touchmove', onDrag, {passive:false});
    document.addEventListener('mouseup', stopDrag);
    document.addEventListener('touchend', stopDrag);
    e.preventDefault();
    onDrag(e);
  }

  function onDrag(e){
    if (!active) return;
    var rect = slider.getBoundingClientRect();
    var x = pageX(e) - rect.left;
    var w = rect.width;
    var min = parseFloat(sliderOne.min) || 0;
    var max = parseFloat(sliderOne.max) || 0;
    var percent = clamp(x / w, 0, 1);
    var value = min + percent * (max - min);
    var step = parseFloat(active.step) || 1;
    value = Math.round(value / step) * step;
    active.value = clamp(value, min, max);
    updateFill();
    if (e.cancelable) e.preventDefault();
  }

  function stopDrag(){
    active = null;
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('touchmove', onDrag);
    document.removeEventListener('mouseup', stopDrag);
    document.removeEventListener('touchend', stopDrag);
  }

  function clamp(v,a,b){ return Math.max(a, Math.min(b, v)); }

  slider.addEventListener('mousedown', startDrag);
  slider.addEventListener('touchstart', startDrag, {passive:false});

  sliderOne.addEventListener('input', updateFill);
  sliderTwo.addEventListener('input', updateFill);

  updateFill();
})();
