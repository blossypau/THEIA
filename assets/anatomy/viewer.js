import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { GLTFLoader } from 'three/addons/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/DRACOLoader.js';

let scene, camera, renderer, controls;
let raycaster, mouse;
let clickableObjects = [];
let highlightedObject = null;
let selectedObject = null;
let movedObjects = new Map(); // uuid -> { object, material, position, underneathUUIDs: [] }
let originalPositions = new Map(); // uuid -> original position
let visibleTypes = new Set(['muscle', 'bone']); // Currently visible types
let axesHelper;

function getViewportDimensions() {
    const fallbackWidth = 960;
    const fallbackHeight = 760;
    const width = (typeof window.innerWidth === 'number' && window.innerWidth > 0) ? window.innerWidth : fallbackWidth;
    const height = (typeof window.innerHeight === 'number' && window.innerHeight > 0) ? window.innerHeight : fallbackHeight;
    return { width, height };
}

function classifyMeshName(name) {
    const normalized = String(name || '').trim();
    const lower = normalized.toLowerCase();

    if (lower.includes('muscle')) {
        return { type: 'muscle', system: 'Musculoskeletal', label: normalizeStructureLabel(normalized) };
    }

    if (lower.includes('bone') || lower.includes('rib') || lower.includes('vertebra') || lower.includes('sternum') || lower.includes('clavicle') || lower.includes('pelvis') || lower.includes('scapula') || lower.includes('femur') || lower.includes('humerus') || lower.includes('skull') || lower.includes('mandible') || lower.includes('coccyx') || lower.includes('sacrum') || lower.includes('cartilage')) {
        return { type: 'bone', system: 'Musculoskeletal', label: normalizeStructureLabel(normalized) };
    }

    return { type: 'anatomical', system: 'Musculoskeletal', label: normalizeStructureLabel(normalized) };
}

function normalizeStructureLabel(name) {
    if (!name) return 'Unidentified structure';

    const cleaned = name
        .replace(/_/g, ' ')
        .replace(/\s+/g, ' ')
        .replace(/\s+\d+$/, '')
        .replace(/\(([^)]+)\)/g, '$1')
        .trim();

    const titleWords = cleaned.split(' ').map((word) => {
        if (!word) return word;
        const lower = word.toLowerCase();
        if (['of', 'the', 'and', 'to', 'a', 'an'].includes(lower)) return lower;
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    });

    const readable = titleWords.join(' ');
    if (readable.toLowerCase().includes('vertebra')) {
        return readable.replace(/Vertebra\s+/i, 'Vertebra ');
    }

    return readable;
}
const PILE_Y = -1.5; // Feet level for piles
const PILE_RADIUS = 0.3; // Pile radius

function init() {
    const { width, height } = getViewportDimensions();
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06111f);

    camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.set(5, 5, 5);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    document.getElementById('canvas-container').appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0x82dbea, 1.1);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0x9feaff, 1.4);
    directionalLight.position.set(10, 10, 5);
    scene.add(directionalLight);

    const directionalLight2 = new THREE.DirectionalLight(0x438bff, 1.0);
    directionalLight2.position.set(-10, -10, -5);
    scene.add(directionalLight2);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false;
    controls.minDistance = 1;
    controls.maxDistance = 50;

    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    // Add axes helper with labels
    axesHelper = new THREE.Group();
    axesHelper.visible = false;

    const grid = new THREE.GridHelper(4,28,0x1b6580,0x0d2d41);grid.position.y=-1.25;scene.add(grid);
    const pedestal = new THREE.Mesh(new THREE.TorusGeometry(.6,.006,6,100),new THREE.MeshBasicMaterial({color:0x45e0f5,transparent:true,opacity:.5}));pedestal.rotation.x=Math.PI/2;pedestal.position.y=-1.23;scene.add(pedestal);
    const axes = new THREE.AxesHelper(2);
    axesHelper.add(axes);

    // Add labels (X=red, Y=green, Z=blue)
    axesHelper.add(createAxisLabel('X', 2.2, 0, 0, 0xff0000));
    axesHelper.add(createAxisLabel('Y', 0, 2.2, 0, 0x00ff00));
    axesHelper.add(createAxisLabel('Z', 0, 0, 2.2, 0x0000ff));

    scene.add(axesHelper);

    loadModel();

    window.addEventListener('resize', onWindowResize);
    renderer.domElement.addEventListener('click', onMouseClick);
    document.getElementById('close-btn').addEventListener('click', closeInfoPanel);
    document.getElementById('reset-btn').addEventListener('click', resetAllObjects);
    document.getElementById('toggle-muscles').addEventListener('click', () => toggleType('muscle'));
    document.getElementById('toggle-bones').addEventListener('click', () => toggleType('bone'));
    document.getElementById('toggle-axes').addEventListener('click', toggleAxes);

    document.getElementById('isolate-btn').addEventListener('click', () => {
        if (!selectedObject) { document.getElementById('model-status').textContent = 'Select a structure before isolating it'; return; }
        const isolated = clickableObjects.some(obj => !obj.visible);
        clickableObjects.forEach(obj => { obj.visible = isolated || obj === selectedObject; });
        document.getElementById('isolate-btn').textContent = isolated ? 'Isolate selected' : 'Show all structures';
    });
    document.getElementById('opacity-control').addEventListener('input', event => {
        const opacity = Number(event.target.value);
        clickableObjects.forEach(obj => {
            obj.material.transparent = opacity < 1;
            obj.material.opacity = opacity;
            obj.material.depthWrite = opacity >= 1;
        });
    });
    document.getElementById('wireframe-btn').addEventListener('click', event => {
        const enabled = event.currentTarget.getAttribute('aria-pressed') !== 'true';
        event.currentTarget.setAttribute('aria-pressed', String(enabled));
        clickableObjects.forEach(obj => { obj.material.wireframe = enabled; });
    });
    animate();
}

function loadModel() {
    const loader = new GLTFLoader();
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('./libs/draco/');
    loader.setDRACOLoader(dracoLoader);

    loader.load(
        'body.glb',
        (gltf) => {
            const model = gltf.scene;
            scene.add(model);

            const box = new THREE.Box3().setFromObject(model);
            const center = box.getCenter(new THREE.Vector3());
            model.position.sub(center);

            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            const cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.5;
            camera.position.set(0, 0, cameraZ * 0.85);
            camera.lookAt(0, 0, 0);
            controls.update();
            controls.saveState();

            const meshNames = [];
            model.traverse((child) => {
                if (child.isMesh) {
                    const association = gltf.parser.associations.get(child);
                    const originalNodeName = association && association.nodes !== undefined ? gltf.parser.json.nodes[association.nodes].name : child.name;
                    child.userData.theiaIdentifier = originalNodeName;
                    const metadata = classifyMeshName(child.name || 'Unnamed mesh');
                    child.userData = {
                        ...child.userData,
                        ...metadata,
                        name: metadata.label,
                        type: metadata.type,
                    };
                    child.material = new THREE.MeshPhongMaterial({
                        color: metadata.type === 'bone' ? 0xb8f0ff : 0x45cfe8,
                        emissive: 0x0c465c, shininess: 80, transparent: true, opacity: .48,
                        depthWrite: false, side: THREE.DoubleSide
                    });
                    clickableObjects.push(child);
                    originalPositions.set(child.uuid, child.position.clone());
                    meshNames.push(child.name || child.geometry?.uuid || 'unnamed-mesh');
                }
            });
            window.__THEIA_MODEL_DEBUG__ = { meshNames, count: meshNames.length };
            document.getElementById('model-status').textContent = `${meshNames.length} structures loaded`;
            console.log('Model loaded successfully', meshNames.slice(0, 50));
        },
        (progress) => console.log('Loading:', (progress.loaded / progress.total * 100) + '%'),
        (error) => { console.error('Error loading model:', error); document.getElementById('model-status').textContent = 'Model load failed. Verify body.glb and local Draco files.'; }
    );
}

function onWindowResize() {
    const { width, height } = getViewportDimensions();
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

function onMouseClick(event) {
    const { width, height } = getViewportDimensions();
    mouse.x = (event.clientX / width) * 2 - 1;
    mouse.y = -(event.clientY / height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(clickableObjects, false);

    if (intersects.length > 0) {
        handleObjectClick(intersects[0].object);
    }
}

function clearSelection() {
    if (selectedObject) {
        unhighlightObject(selectedObject);
        selectedObject = null;
        highlightedObject = null;
    }
    document.getElementById('info-panel').classList.add('hidden');
    notifyTheiaBridge('', 'selection-cleared', '', 'Musculoskeletal');
}

function handleObjectClick(object) {
    if (movedObjects.has(object.uuid)) {
        restoreObject(object.uuid, true);
        return;
    }

    if (selectedObject === object) {
        clearSelection();
        return;
    }

    if (selectedObject) {
        unhighlightObject(selectedObject);
    }

    selectedObject = object;
    highlightedObject = object;
    highlightObject(object);
}

function highlightObject(object) {
    if (!object.userData.originalMaterial) {
        object.userData.originalMaterial = object.material;
    }

    object.material = object.material.clone();
    object.material.emissive = new THREE.Color(0x9c78ff);
    object.material.emissiveIntensity = 1.5;
    object.material.opacity = .9;

    highlightedObject = object;
    showObjectInfo(object);
}

function unhighlightObject(object) {
    if (object.userData.originalMaterial) {
        object.material = object.userData.originalMaterial;
        delete object.userData.originalMaterial;
    }
}

function getPilePosition(type) {
    const xOffset = type === 'muscle' ? -0.9 : 0.9;
    return {
        x: xOffset + (Math.random() - 0.5) * PILE_RADIUS * 2,
        y: PILE_Y + Math.random() * 0.2,  // 0.2 units vertical spread
        z: (Math.random() - 0.5) * PILE_RADIUS * 2
    };
}

function moveToPile(object, duration = 800) {
    const pile = getPilePosition(object.userData?.type);
    animateSmoothArc(object, pile, duration);
}

function moveObjectAway(object) {
    if (!object.userData.originalMaterial) return;

    const underneathUUIDs = findObjectsUnderneath(object);

    movedObjects.set(object.uuid, {
        object: object,
        material: object.userData.originalMaterial,
        position: object.position.clone(),
        underneathUUIDs: underneathUUIDs
    });

    object.material = object.material.clone();
    object.material.transparent = true;
    object.material.opacity = 0.3;
    object.material.color.set(0xff0000);
    object.material.emissive = new THREE.Color(0x000000);
    object.material.depthWrite = false;

    moveToPile(object);

    delete object.userData.originalMaterial;
    highlightedObject = null;
}

function findObjectsUnderneath(object) {
    const objectBox = new THREE.Box3().setFromObject(object);
    const underneathUUIDs = [];

    // Check which objects overlap with this one
    clickableObjects.forEach(obj => {
        if (obj.uuid === object.uuid) return;

        const objBox = new THREE.Box3().setFromObject(obj);

        // If bounding boxes intersect, object is underneath
        if (objectBox.intersectsBox(objBox)) {
            underneathUUIDs.push(obj.uuid);
        }
    });

    return underneathUUIDs;
}

function restoreObject(uuid, shouldHighlight = false) {
    const state = movedObjects.get(uuid);
    if (!state) return;

    const object = state.object;

    if (shouldHighlight && highlightedObject) {
        unhighlightObject(highlightedObject);
    }

    const current = object.position.clone();
    const target = state.position;
    const height = Math.max(current.y, target.y) + 0.5;
    const mid1 = {
        x: current.x * 0.7 + target.x * 0.3,
        y: current.y * 0.5 + height * 0.5,
        z: current.z * 0.7 + target.z * 0.3
    };
    const mid2 = {
        x: current.x * 0.3 + target.x * 0.7,
        y: target.y * 0.5 + height * 0.5,
        z: current.z * 0.3 + target.z * 0.7
    };

    new TWEEN.Tween(object.position)
        .to(mid1, 240)
        .easing(TWEEN.Easing.Sinusoidal.Out)
        .chain(
            new TWEEN.Tween(object.position)
                .to(mid2, 240)
                .easing(TWEEN.Easing.Sinusoidal.InOut)
                .chain(
                    new TWEEN.Tween(object.position)
                        .to(target, 320)
                        .easing(TWEEN.Easing.Sinusoidal.In)
                        .onComplete(() => {
                            object.material = state.material;
                            if (shouldHighlight) {
                                highlightObject(object);
                            }
                        })
                )
        )
        .start();

    movedObjects.delete(uuid);

    state.underneathUUIDs.forEach(underneathUUID => {
        if (movedObjects.has(underneathUUID)) {
            restoreObject(underneathUUID, false);
        }
    });
}

function notifyTheiaBridge(objectName, action = 'select', identifier = '', system = 'Musculoskeletal') {
    const normalizedName = String(objectName || '').trim();
    const payload = {
        identifier: action === 'selection-cleared' ? '' : (identifier || normalizedName || 'unknown-structure'),
        organ: action === 'selection-cleared' ? '' : (normalizedName || 'Unknown structure'),
        system: system || 'Musculoskeletal',
        action,
        source: 'body-anatomy-3d-viewer',
        timestamp: new Date().toISOString(),
    };

    try {
        const targetOrigin = new URL(document.referrer || 'http://localhost:8507').origin;
        window.parent.postMessage({ type: 'THEIA_ORGAN_SELECTED', payload }, targetOrigin);
    } catch (error) {
        console.warn('parent message failed', error);
    }


}

function showObjectInfo(object) {
    const { type, name, nameDetail, wikiLink, system } = object?.userData || {};
    const selectedName = name || object.name || 'Unnamed Object';
    const selectedSystem = system || inferSystemFromName(selectedName);

    document.getElementById('info-type').textContent = type || '';
    document.getElementById('info-title').textContent = selectedName;
    document.getElementById('info-detail').textContent = nameDetail || `Selected structure: ${selectedName} (${selectedSystem})`;

    const wikiLinkEl = document.getElementById('info-wiki-link');
    if (wikiLink) {
        wikiLinkEl.href = wikiLink;
        wikiLinkEl.style.display = 'block';
    } else {
        wikiLinkEl.style.display = 'none';
    }

    notifyTheiaBridge(selectedName, 'select', object.userData.theiaIdentifier || object.name || selectedName, selectedSystem);
    document.getElementById('info-panel').classList.remove('hidden');
}

function closeInfoPanel() {
    document.getElementById('info-panel').classList.add('hidden');
}

function createAxisLabel(text, x, y, z, color) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 64;
    canvas.height = 64;

    context.fillStyle = '#' + color.toString(16).padStart(6, '0');
    context.font = 'bold 48px Arial';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, 32, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.position.set(x, y, z);
    sprite.scale.set(0.3, 0.3, 1);

    return sprite;
}

function toggleAxes() {
    const btn = document.getElementById('toggle-axes');
    axesHelper.visible = !axesHelper.visible;
    if (axesHelper.visible) {
        btn.classList.add('active');
    } else {
        btn.classList.remove('active');
    }
}

function toggleType(type) {
    const btn = document.getElementById(`toggle-${type}s`);

    if (visibleTypes.has(type)) {
        visibleTypes.delete(type);
        btn.classList.remove('active');
        hideObjectsOfType(type);
    } else {
        visibleTypes.add(type);
        btn.classList.add('active');
        showObjectsOfType(type);
    }
}

function hideObjectsOfType(type) {
    clickableObjects.forEach(obj => {
        if (obj.userData?.type === type) {
            moveToPile(obj);
        }
    });
}

function showObjectsOfType(type) {
    clickableObjects.forEach(obj => {
        if (obj.userData?.type === type) {
            const originalPos = originalPositions.get(obj.uuid);
            if (originalPos) {
                const movedState = movedObjects.get(obj.uuid);
                const targetPos = movedState ? movedState.position : originalPos;
                animateSmoothArc(obj, targetPos, 800);
            }
        }
    });
}

function animateSmoothArc(object, target, duration) {
    const start = object.position.clone();
    const height = Math.max(start.y, target.y) + 0.5;

    // Create smooth curve with 4 control points
    const curve = new THREE.CatmullRomCurve3([
        start,
        new THREE.Vector3(
            start.x * 0.75 + target.x * 0.25,
            start.y * 0.25 + height * 0.75,
            start.z * 0.75 + target.z * 0.25
        ),
        new THREE.Vector3(
            start.x * 0.25 + target.x * 0.75,
            target.y * 0.25 + height * 0.75,
            start.z * 0.25 + target.z * 0.75
        ),
        new THREE.Vector3(target.x, target.y, target.z)
    ]);

    const tweenObj = { t: 0 };
    new TWEEN.Tween(tweenObj)
        .to({ t: 1 }, duration)
        .easing(TWEEN.Easing.Linear.None)
        .onUpdate(() => {
            const point = curve.getPointAt(tweenObj.t);
            object.position.copy(point);
        })
        .start();
}

function inferSystemFromName(name) {
    const lower = String(name || '').toLowerCase();
    if (lower.includes('muscle') || lower.includes('bone') || lower.includes('rib') || lower.includes('vertebra') || lower.includes('clavicle') || lower.includes('femur') || lower.includes('humerus') || lower.includes('sternum') || lower.includes('scapula') || lower.includes('pelvis')) return 'Musculoskeletal';
    if (lower.includes('brain') || lower.includes('spinal') || lower.includes('cerebellum')) return 'Nervous';
    if (lower.includes('heart') || lower.includes('aorta')) return 'Cardiovascular';
    if (lower.includes('lung') || lower.includes('trachea') || lower.includes('airway')) return 'Respiratory';
    if (lower.includes('liver') || lower.includes('stomach') || lower.includes('intestine') || lower.includes('pancreas')) return 'Digestive';
    if (lower.includes('kidney') || lower.includes('bladder')) return 'Urinary';
    if (lower.includes('skin')) return 'Integumentary';
    return 'Musculoskeletal';
}

function resetAllObjects() {
    controls.reset();
    clearSelection();
    visibleTypes = new Set(['muscle','bone']);
    document.getElementById('toggle-muscles').classList.add('active');
    document.getElementById('toggle-bones').classList.add('active');
    document.getElementById('wireframe-btn').setAttribute('aria-pressed','false');
    clickableObjects.forEach(obj => { obj.visible = true; obj.material.opacity = .48; obj.material.transparent = true; obj.material.depthWrite = false; obj.material.wireframe = false; });
    document.getElementById('opacity-control').value = .48;
    document.getElementById('isolate-btn').textContent = 'Isolate selected';
    clearSelection();
    if (highlightedObject) {
        unhighlightObject(highlightedObject);
        highlightedObject = null;
    }
    selectedObject = null;

    movedObjects.forEach((state) => {
        const originalPos = originalPositions.get(state.object.uuid);
        const isVisible = visibleTypes.has(state.object.userData?.type);

        if (isVisible) {
            animateSmoothArc(state.object, originalPos, 800);
            setTimeout(() => {
                state.object.material = state.material;
            }, 800);
        } else {
            moveToPile(state.object);
            state.object.material = state.material;
        }
    });

    setTimeout(() => movedObjects.clear(), 850);
    closeInfoPanel();
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    TWEEN.update();
    renderer.render(scene, camera);
}

init();
