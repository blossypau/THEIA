import * as THREE from 'three';
import {OrbitControls} from 'three/addons/OrbitControls.js';
try {
const scene=new THREE.Scene(); scene.background=new THREE.Color('#071623');
const camera=new THREE.PerspectiveCamera(42,innerWidth/innerHeight,.1,100);camera.position.set(9,7,12);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));document.body.prepend(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=8;controls.maxDistance=28;controls.target.set(0,0,0);controls.update();controls.saveState();
scene.add(new THREE.AmbientLight('#719db4',1.5));const sun=new THREE.DirectionalLight('#d4f3ff',3);sun.position.set(5,8,4);scene.add(sun);
const station=new THREE.Group();scene.add(station);station.rotation.z=-.28;
const metal=new THREE.MeshStandardMaterial({color:'#a9c6cf',metalness:.65,roughness:.36});const dark=new THREE.MeshStandardMaterial({color:'#0e293d',metalness:.6,roughness:.35});
const cyan=new THREE.MeshBasicMaterial({color:'#45e0f5'});
function box(w,h,d,mat,x,y,z){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y,z);station.add(m);return m;}
box(9,.16,.16,metal,0,0,0);
for(const x of [-2.5,-.7,1.1]){const m=new THREE.Mesh(new THREE.CylinderGeometry(.48,.48,1.8,20),metal);m.rotation.z=Math.PI/2;m.position.x=x;station.add(m);const ring=new THREE.Mesh(new THREE.TorusGeometry(.5,.035,8,40),cyan);ring.rotation.y=Math.PI/2;ring.position.x=x+.75;station.add(ring);}
for(const x of [-3.8,-2.3,2.3,3.8])for(const z of [-1.7,1.7]){
 const panel=box(1.12,.065,2.5,dark,x,0,z);const edges=new THREE.LineSegments(new THREE.EdgesGeometry(panel.geometry),new THREE.LineBasicMaterial({color:'#438bff',transparent:true,opacity:.65}));panel.add(edges);
 for(let dz=-1;dz<=1;dz+=.25)box(1.08,.075,.012,new THREE.MeshBasicMaterial({color:'#235478'}),x,0,z+dz);
}
const earth=new THREE.Mesh(new THREE.SphereGeometry(7,56,40),new THREE.MeshStandardMaterial({color:'#12446a',roughness:1}));earth.position.set(0,-10,-5);scene.add(earth);
const wire=new THREE.LineSegments(new THREE.WireframeGeometry(new THREE.SphereGeometry(7.025,32,20)),new THREE.LineBasicMaterial({color:'#45b8da',transparent:true,opacity:.13}));wire.position.copy(earth.position);scene.add(wire);
const orbit=new THREE.Mesh(new THREE.TorusGeometry(6.5,.012,6,160),new THREE.MeshBasicMaterial({color:'#45e0f5',transparent:true,opacity:.32}));orbit.rotation.x=1.25;orbit.position.y=-2;scene.add(orbit);
const positions=new Float32Array(450);let seed=19;function random(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;}
for(let i=0;i<positions.length;i++)positions[i]=(random()-.5)*70;
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));scene.add(new THREE.Points(geometry,new THREE.PointsMaterial({color:'#a4d6e6',size:.05,transparent:true,opacity:.7})));
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches;const button=document.getElementById('motion');function label(){button.textContent=paused?'Resume orbit':'Pause orbit';button.setAttribute('aria-pressed',String(paused));}label();button.onclick=()=>{paused=!paused;label();};document.getElementById('reset').onclick=()=>controls.reset();
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
let last=performance.now();function animate(now){requestAnimationFrame(animate);if(!paused&&document.visibilityState==='visible')station.rotation.y+=Math.min(now-last,50)*.000035;last=now;controls.update();renderer.render(scene,camera);}requestAnimationFrame(animate);window.__THEIA_ORBIT_READY__=true;
} catch(error){document.getElementById('status').textContent='Interactive scene unavailable: '+error.message;}
