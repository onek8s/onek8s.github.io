/* The lab examples (examples/lab/): draw every ```mermaid block in the browser, light or dark like the page.
   Only those pages load this file and Mermaid; the design's pages show the SVGs that scripts/render.sh made. Without
   JavaScript, or when Mermaid does not load, the source stays on the page as code. The settings are those of
   scripts/mermaid.json (light) and scripts/mermaid-dark.json (dark), which the pictures of the design use. */
(function () {
  'use strict';
  if (!window.mermaid) { return; }

  var layout = {
    flowchart: { nodeSpacing: 30, rankSpacing: 36, padding: 10, subGraphTitleMargin: { top: 2, bottom: 2 }, wrappingWidth: 360 },
    sequence: { actorMargin: 40, messageMargin: 30, width: 130 },
    themeCSS: 'foreignObject { overflow: visible; }'
  };
  var dark = {
    theme: 'dark',
    themeVariables: {
      background: '#161d26', primaryColor: '#1f2a36', primaryBorderColor: '#5b6b7d', primaryTextColor: '#e6edf3',
      lineColor: '#9aa7b4', textColor: '#e6edf3', clusterBkg: '#1a232e', clusterBorder: '#5b6b7d',
      edgeLabelBackground: '#161d26', titleColor: '#e6edf3', mainBkg: '#1f2a36', nodeBorder: '#5b6b7d',
      secondaryColor: '#1a232e', tertiaryColor: '#1a232e'
    }
  };

  var root = document.documentElement;
  var systemDark = window.matchMedia('(prefers-color-scheme: dark)');
  var scheme = function () { return root.getAttribute('data-theme') || (systemDark.matches ? 'dark' : 'light'); };

  // kramdown with Rouge writes <div class="language-mermaid highlighter-rouge"><div class="highlight"><pre><code>;
  // without Rouge it is <pre><code class="language-mermaid">.
  var blocks = [];
  document.querySelectorAll('main div.language-mermaid, main pre > code.language-mermaid').forEach(function (el) {
    var outer = el.tagName === 'CODE' ? el.parentNode : el;
    if (outer.closest('.mermaid-diagram')) { return; }
    var box = document.createElement('div');
    box.className = 'mermaid-diagram';
    outer.parentNode.replaceChild(box, outer);
    blocks.push({ box: box, source: el.textContent, fallback: outer });
  });
  if (!blocks.length) { return; }

  var drawn = null;
  var counter = 0;
  var queue = Promise.resolve();
  var draw = function () {
    var want = scheme();
    if (want === drawn) { return; }
    drawn = want;
    var settings = { startOnLoad: false, securityLevel: 'strict', theme: 'default' };
    Object.keys(layout).forEach(function (k) { settings[k] = layout[k]; });
    if (want === 'dark') { Object.keys(dark).forEach(function (k) { settings[k] = dark[k]; }); }
    // One at a time, also across theme changes: Mermaid's renderer is not reentrant.
    queue = queue.then(function () { window.mermaid.initialize(settings); });
    queue = blocks.reduce(function (done, block) {
      return done.then(function () {
        counter += 1;
        return window.mermaid.render('mermaid-' + counter, block.source).then(function (result) {
          block.box.innerHTML = result.svg;
          block.box.classList.add('zoomable');
        }, function () {
          block.box.classList.remove('zoomable');
          block.box.innerHTML = '';
          block.box.appendChild(block.fallback);
        });
      });
    }, queue);
  };
  // A click opens the drawn diagram full screen (site.js's lightbox): fitted to the window, but never smaller than
  // Mermaid drew it, so a wide one that the column shrank to a strip is readable and scrolls instead.
  blocks.forEach(function (block) {
    block.box.addEventListener('click', function () {
      var svg = block.box.querySelector('svg');
      var box = svg && svg.viewBox && svg.viewBox.baseVal;
      if (!box || !box.width || !window.onek8sLightbox) { return; }
      var copy = svg.cloneNode(true);
      var room = document.getElementById('lightbox');
      var scale = Math.max(1, Math.min((room.clientWidth || window.innerWidth) / box.width,
        (room.clientHeight || window.innerHeight) / box.height) * 0.95);
      copy.style.maxWidth = 'none';
      copy.setAttribute('width', Math.round(box.width * scale));
      copy.setAttribute('height', Math.round(box.height * scale));
      window.onek8sLightbox(copy);
    });
  });
  draw();
  // The theme follows the system setting and the header's toggle (which sets data-theme on <html>).
  systemDark.addEventListener('change', draw);
  new MutationObserver(draw).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
})();
