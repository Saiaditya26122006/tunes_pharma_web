/* =====================================================
   PREMIUM ANIMATION ENGINE — Tunes Therapeutics
   Three.js Molecular Network + GSAP + VanillaTilt
   ===================================================== */

function initMolecularNetwork() {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0, 7);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);

  const COUNT     = window.innerWidth < 768 ? 45 : 80;
  const positions = new Float32Array(COUNT * 3);
  const colors    = new Float32Array(COUNT * 3);
  const pts = [], vels = [];

  const palette = [
    new THREE.Color(0x1e40af), new THREE.Color(0x2563eb),
    new THREE.Color(0x0284c7), new THREE.Color(0x0f1e2d),
    new THREE.Color(0xb8892a),
  ];

  for (let i = 0; i < COUNT; i++) {
    const x = (Math.random()-.5)*14, y = (Math.random()-.5)*9, z = (Math.random()-.5)*7;
    pts.push(new THREE.Vector3(x,y,z));
    vels.push(new THREE.Vector3((Math.random()-.5)*.006,(Math.random()-.5)*.006,(Math.random()-.5)*.003));
    positions[i*3]=x; positions[i*3+1]=y; positions[i*3+2]=z;
    const c = palette[Math.floor(Math.random()*palette.length)];
    colors[i*3]=c.r; colors[i*3+1]=c.g; colors[i*3+2]=c.b;
  }

  const ptGeo = new THREE.BufferGeometry();
  ptGeo.setAttribute('position', new THREE.BufferAttribute(positions,3));
  ptGeo.setAttribute('color',    new THREE.BufferAttribute(colors,3));
  const ptMesh = new THREE.Points(ptGeo, new THREE.PointsMaterial({
    size:.055, vertexColors:true, transparent:true, opacity:.85, sizeAttenuation:true
  }));
  scene.add(ptMesh);

  const lineGroup = new THREE.Group();
  scene.add(lineGroup);

  function rebuildLines() {
    while (lineGroup.children.length) {
      const child = lineGroup.children[0];
      lineGroup.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
    }
    for (let i=0; i<COUNT; i++) for (let j=i+1; j<COUNT; j++) {
      const d = pts[i].distanceTo(pts[j]);
      if (d < 2.8) {
        const g = new THREE.BufferGeometry().setFromPoints([pts[i],pts[j]]);
        lineGroup.add(new THREE.Line(g, new THREE.LineBasicMaterial({
          color:0x1e40af, transparent:true, opacity:(1-d/2.8)*.35
        })));
      }
    }
  }

  let mx=0, my=0;
  window.addEventListener('mousemove', e => {
    mx = (e.clientX/window.innerWidth-.5)*.6;
    my = -(e.clientY/window.innerHeight-.5)*.6;
  }, {passive:true});

  // Pause the render loop while the hero is off-screen so the WebGL work
  // doesn't compete with scroll interpolation on the rest of the page.
  let visible = true;
  const io = new IntersectionObserver(
    ([e]) => { visible = e.isIntersecting; if (visible) requestAnimationFrame(animate); },
    { rootMargin: '150px 0px' }
  );
  io.observe(canvas);

  let frame=0, time=0;
  function animate() {
    if (!visible) return;
    requestAnimationFrame(animate);
    time+=.004; frame++;
    for (let i=0; i<COUNT; i++) {
      pts[i].add(vels[i]);
      if (Math.abs(pts[i].x)>7)   vels[i].x*=-1;
      if (Math.abs(pts[i].y)>4.5) vels[i].y*=-1;
      if (Math.abs(pts[i].z)>3.5) vels[i].z*=-1;
      positions[i*3]=pts[i].x; positions[i*3+1]=pts[i].y; positions[i*3+2]=pts[i].z;
    }
    ptGeo.attributes.position.needsUpdate=true;
    // Line rebuild is O(n²) and allocates fresh geometries each pass — throttle
    // it to ~4 Hz to keep GC pressure low during scroll.
    if (frame%15===0) rebuildLines();
    ptMesh.rotation.y=lineGroup.rotation.y=time*.04;
    camera.position.x+=(mx*2-camera.position.x)*.035;
    camera.position.y+=(my*2-camera.position.y)*.035;
    camera.lookAt(scene.position);
    renderer.render(scene,camera);
  }
  animate();

  window.addEventListener('resize', () => {
    camera.aspect=window.innerWidth/window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth,window.innerHeight);
  }, {passive:true});
}

function initScrollReveal() {
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => { if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target);} });
  }, {threshold:.08, rootMargin:'0px 0px -55px 0px'});
  document.querySelectorAll('.p-reveal,.p-reveal-left,.p-reveal-right').forEach(el=>io.observe(el));
}

function animateCounter(el) {
  const target=parseInt(el.dataset.target||el.textContent.replace(/[^0-9]/g,''));
  const suffix=el.dataset.suffix||(el.textContent.includes('+') ? '+' : '');
  const dur=2400, start=performance.now();
  function tick(now) {
    const p=Math.min((now-start)/dur,1);
    el.textContent=Math.round((1-Math.pow(2,-10*p))*target).toLocaleString()+suffix;
    if(p<1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function initCounters() {
  const io=new IntersectionObserver(entries=>{
    entries.forEach(e=>{
      if(e.isIntersecting&&!e.target.dataset.counted){e.target.dataset.counted='1';animateCounter(e.target);io.unobserve(e.target);}
    });
  },{threshold:.5});
  document.querySelectorAll('[data-counter]').forEach(el=>io.observe(el));
}

function initHeader() {
  const h=document.querySelector('.p-header');
  if(!h) return;
  const f=()=>h.classList.toggle('scrolled',window.scrollY>60);
  window.addEventListener('scroll',f,{passive:true}); f();
}

function initHeroGSAP() {
  if(typeof gsap==='undefined') return;
  const tl=gsap.timeline({delay:1.1});
  tl.from('.p-hero-badge',{opacity:0,y:22,duration:.6,ease:'power2.out'})
    .from('.p-hero h1',   {opacity:0,y:34,duration:.9,ease:'power3.out'},'-=.3')
    .from('.p-hero p',    {opacity:0,y:20,duration:.65,ease:'power2.out'},'-=.45')
    .from('.p-hero-btns .p-btn',{opacity:0,y:18,duration:.5,stagger:.12,ease:'power2.out'},'-=.35')
    .from('.p-hero-scroll',{opacity:0,y:10,duration:.5,ease:'power2.out'},'-=.2');
}

function initTilt() {
  if(typeof VanillaTilt==='undefined') return;
  VanillaTilt.init(document.querySelectorAll('[data-tilt]'),{
    max:11,speed:600,glare:true,'max-glare':.12,
    perspective:900,transition:true,reset:true,
    easing:'cubic-bezier(.03,.98,.52,.99)',
  });
}

function initMagnetic() {
  document.querySelectorAll('.p-btn-primary,.p-ai-btn').forEach(btn=>{
    btn.addEventListener('mousemove',e=>{
      const r=btn.getBoundingClientRect();
      btn.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.18}px,${(e.clientY-r.top-r.height/2)*.18}px)`;
    });
    btn.addEventListener('mouseleave',()=>{btn.style.transform='';});
  });
}

/* ── Mobile hamburger menu ── */
function initMobileMenu() {
  const header  = document.getElementById('p-header');
  const actions = header && header.querySelector('.p-header-actions');
  const nav     = header && header.querySelector('.p-nav');
  if (!header || !actions || !nav) return;

  // Build hamburger button
  const btn = document.createElement('button');
  btn.className = 'p-hamburger';
  btn.setAttribute('aria-label', 'Toggle menu');
  btn.innerHTML = '<span></span><span></span><span></span>';
  actions.prepend(btn);

  // Build overlay + panel
  const overlay = document.createElement('div');
  overlay.className = 'p-mobile-menu';

  // Collect nav links — handle both plain <a> and .p-nav-drop
  let navHTML = '<div class="p-mobile-nav">';
  nav.childNodes.forEach(node => {
    if (node.nodeType !== 1) return;
    if (node.classList.contains('p-nav-drop')) {
      // Products with sub-links
      const trigger = node.querySelector('.p-nav-drop-trigger');
      const links   = node.querySelectorAll('.p-nav-drop-menu a');
      if (trigger) {
        navHTML += `<a href="${trigger.href}" class="${trigger.classList.contains('active') ? 'active' : ''}">${trigger.textContent.replace('▾','').trim()}</a>`;
        navHTML += '<div class="p-mobile-sub">';
        links.forEach(l => { navHTML += `<a href="${l.href}">${l.textContent.trim()}</a>`; });
        navHTML += '</div>';
      }
    } else if (node.tagName === 'A') {
      navHTML += `<a href="${node.href}" class="${node.classList.contains('active') ? 'active' : ''}">${node.textContent.trim()}</a>`;
    }
  });
  navHTML += '</div>';

  // Action buttons
  const contactHref = (actions.querySelector('.p-contact-btn') || {}).href || '/contact';
  const doctorHref  = (actions.querySelector('.p-doctor-btn') || {}).href  || '/doctor-portal';
  navHTML += `
    <div class="p-mobile-divider"></div>
    <div class="p-mobile-actions">
      <a href="${doctorHref}" class="p-doctor-btn-full">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a5 5 0 1 0 0 10A5 5 0 0 0 12 2z"/><path d="M2 20c0-4 4-7 10-7s10 3 10 7"/><path d="M17 13v4m-2-2h4"/></svg>
        Doctor Portal
      </a>
      <a href="${contactHref}" class="p-contact-btn">Contact Us</a>
    </div>`;

  overlay.innerHTML = `<div class="p-mobile-menu-panel">${navHTML}</div>`;
  document.body.appendChild(overlay);

  // Toggle
  function open()  { btn.classList.add('open'); overlay.classList.add('open'); document.body.style.overflow='hidden'; }
  function close() { btn.classList.remove('open'); overlay.classList.remove('open'); document.body.style.overflow=''; }

  btn.addEventListener('click', () => overlay.classList.contains('open') ? close() : open());
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  // Close on link click
  overlay.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
}

/* ── Smooth scroll (Lenis) + GSAP ScrollTrigger sync ── */
function initSmoothScroll() {
  if (typeof Lenis === 'undefined') return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const lenis = new Lenis({
    duration: 1.15,
    easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    smoothTouch: false,
  });

  function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
  requestAnimationFrame(raf);

  if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add(t => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
  }

  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const id = a.getAttribute('href');
      if (id.length > 1) {
        const target = document.querySelector(id);
        if (target) { e.preventDefault(); lenis.scrollTo(target, { offset: -80 }); }
      }
    });
  });
}

/* ── Line-mask reveal on section headings (SplitType + GSAP) ── */
function initSplitHeadings() {
  if (typeof SplitType === 'undefined' || typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const targets = document.querySelectorAll('.p-section-title, .ht-title, .p-hero-title-oneline, .t-hero-tagline-text');
  targets.forEach(el => {
    const split = new SplitType(el, { types: 'lines,words', lineClass: 'split-line', wordClass: 'split-word' });
    gsap.set(split.words, { yPercent: 110, opacity: 0 });
    gsap.to(split.words, {
      yPercent: 0,
      opacity: 1,
      duration: 0.9,
      ease: 'power3.out',
      stagger: 0.06,
      scrollTrigger: { trigger: el, start: 'top 85%', once: true },
    });
  });
}

document.addEventListener('DOMContentLoaded',()=>{
  initHeader(); initScrollReveal(); initCounters();
  initHeroGSAP(); initMagnetic(); initMobileMenu();
  initSmoothScroll(); initSplitHeadings();
  setTimeout(initTilt,120);
  if(document.getElementById('hero-canvas')&&typeof THREE!=='undefined') initMolecularNetwork();
});
