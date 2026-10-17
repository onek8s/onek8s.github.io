/* Progressive enhancements: everything on the page works without this file. */
(function () {
  'use strict';

  // Light / dark toggle. Follows the system setting until the reader picks one, which is then remembered.
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  if (btn) {
    var systemDark = window.matchMedia('(prefers-color-scheme: dark)');
    var current = function () { return root.getAttribute('data-theme') || (systemDark.matches ? 'dark' : 'light'); };
    var label = function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      btn.textContent = next === 'dark' ? '☾ Dark' : '☀ Light';
      btn.setAttribute('aria-label', 'Switch to ' + next + ' mode');
    };
    btn.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) { /* storage may be blocked */ }
      label();
    });
    systemDark.addEventListener('change', label);
    label();
    btn.hidden = false;
  }

  // Pictures: wrap each stand-alone image in a figure with its alt text as the caption, and open it full
  // screen on click.
  var box = document.getElementById('lightbox');
  var big = box ? box.querySelector('img') : null;
  var close = function () {
    if (!box) { return; }
    box.classList.remove('open');
    if (document.fullscreenElement) { document.exitFullscreen(); }
  };
  document.querySelectorAll('main > p > img:only-child').forEach(function (img) {
    var p = img.parentNode;
    var figure = document.createElement('figure');
    figure.className = 'figure';
    figure.appendChild(img);
    if (img.alt) {
      var caption = document.createElement('figcaption');
      caption.textContent = img.alt;
      figure.appendChild(caption);
    }
    p.parentNode.replaceChild(figure, p);
    if (!box) { return; }
    img.addEventListener('click', function () {
      big.src = img.src;
      big.alt = img.alt;
      box.classList.add('open');
      if (box.requestFullscreen) { box.requestFullscreen().catch(function () { /* fine without */ }); }
    });
  });
  if (box) {
    box.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { close(); } });
    document.addEventListener('fullscreenchange', function () { if (!document.fullscreenElement) { box.classList.remove('open'); } });
  }

  // Keep the current page visible in the sidebar.
  var current = document.querySelector('.sidebar li.current');
  if (current && current.scrollIntoView) {
    current.scrollIntoView({ block: 'center' });
    window.scrollTo(0, 0);
  }
})();
