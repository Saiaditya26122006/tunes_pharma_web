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

  const COUNT     = window.innerWidth < 768 ? 60 : 110;
  const positions = new Float32Array(COUNT * 3);
  const colors    = new Float32Array(COUNT * 3);
  const pts = [], vels = [];

  const palette = [
    new THREE.Color(0x60a5fa), new THREE.Color(0x93c5fd),
    new THREE.Color(0x00b4ff), new THREE.Color(0xffffff),
    new THREE.Color(0xe8c98f),
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
    while (lineGroup.children.length) lineGroup.remove(lineGroup.children[0]);
    for (let i=0; i<COUNT; i++) for (let j=i+1; j<COUNT; j++) {
      const d = pts[i].distanceTo(pts[j]);
      if (d < 2.8) {
        const g = new THREE.BufferGeometry().setFromPoints([pts[i],pts[j]]);
        lineGroup.add(new THREE.Line(g, new THREE.LineBasicMaterial({
          color:0x3b82f6, transparent:true, opacity:(1-d/2.8)*.28
        })));
      }
    }
  }

  let mx=0, my=0;
  window.addEventListener('mousemove', e => {
    mx = (e.clientX/window.innerWidth-.5)*.6;
    my = -(e.clientY/window.innerHeight-.5)*.6;
  }, {passive:true});

  let frame=0, time=0;
  (function animate() {
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
    if (frame%4===0) rebuildLines();
    ptMesh.rotation.y=lineGroup.rotation.y=time*.04;
    camera.position.x+=(mx*2-camera.position.x)*.035;
    camera.position.y+=(my*2-camera.position.y)*.035;
    camera.lookAt(scene.position);
    renderer.render(scene,camera);
  })();

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

document.addEventListener('DOMContentLoaded',()=>{
  initHeader(); initScrollReveal(); initCounters();
  initHeroGSAP(); initMagnetic();
  setTimeout(initTilt,120);
  if(document.getElementById('hero-canvas')&&typeof THREE!=='undefined') initMolecularNetwork();
});
