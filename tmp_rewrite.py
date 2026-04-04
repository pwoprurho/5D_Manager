import re

with open(r"c:\Users\Administrator\outbound-caller-python\templates\project_updates.html", "r", encoding="utf-8") as f:
    html = f.read()

new_scripts = """{% block scripts %}

<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.135.0/build/three.module.js",
    "orbit-controls": "https://unpkg.com/three@0.135.0/examples/jsm/controls/OrbitControls.js",
    "gltf-loader": "https://unpkg.com/three@0.135.0/examples/jsm/loaders/GLTFLoader.js",
    "ifc-loader": "https://unpkg.com/three@0.135.0/examples/jsm/loaders/IFCLoader.js"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'orbit-controls';
import { GLTFLoader } from 'gltf-loader';
import { IFCLoader } from 'ifc-loader';

const userRole = "{{ user.role|string }}".replace("UserRole.", "").toLowerCase();
let scene, camera, renderer, modelObject, controls;

// Initialize native IFCLoader from Three.js!
const ifcLoader = new IFCLoader();
ifcLoader.ifcManager.setWasmPath('https://unpkg.com/three@0.135.0/examples/jsm/loaders/ifc/');

window.init3D = function(modelUrl) {
    console.log("[VIEWER] Initializing web-ifc with URL:", modelUrl);
    const canvas = document.getElementById('three-canvas');
    if (!canvas) return;

    const container = canvas.parentElement;
    const w = container.clientWidth;
    const h = container.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020617);

    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 2;
    controls.maxDistance = 500;

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    // Intersection tooltip
    canvas.addEventListener('mousemove', (event) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        if (modelObject) {
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects([modelObject], true);
            const tooltip = document.getElementById('viewer-tooltip');
            if (intersects.length > 0) {
                document.getElementById('tooltip-text').textContent = "BIM ARCHITECTURE ELEMENT";
                tooltip.style.display = 'block';
                canvas.style.cursor = 'pointer';
            } else {
                tooltip.style.display = 'none';
                canvas.style.cursor = 'crosshair';
            }
        }
    });

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.8);
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);
    
    // Grid
    const gridHelper = new THREE.GridHelper(100, 50, 0x1e293b, 0x0f172a);
    scene.add(gridHelper);

    camera.position.set(20, 20, 20);
    controls.target.set(0, 0, 0);
    controls.update();

    if (modelUrl) {
        document.getElementById('viewer-loading').style.display = 'flex';
        const urlLower = modelUrl.toLowerCase();
        if (urlLower.includes('.ifc')) {
            window.loadIFCModel(modelUrl);
        } else if (urlLower.includes('.gltf') || urlLower.includes('.glb')) {
            window.loadGLTFModel(modelUrl);
        } else {
            window.loadIFCModel(modelUrl).catch(() => window.loadGLTFModel(modelUrl));
        }
    } else {
        window.showPlaceholder("AWAITING_DESIGN_LINK");
    }

    window.addEventListener('resize', () => {
        const nw = container.clientWidth;
        const nh = container.clientHeight;
        camera.aspect = nw / nh;
        camera.updateProjectionMatrix();
        renderer.setSize(nw, nh);
    });

    (function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    })();
};

window.loadIFCModel = async function(url) {
    return new Promise((resolve, reject) => {
        ifcLoader.load(url, (ifcModel) => {
            modelObject = ifcModel;
            scene.add(modelObject);
            window.fitCameraToModel();
            document.getElementById('viewer-loading').style.display = 'none';
            console.log("[VIEWER] Authentic Web-IFC model loaded successfully");
            resolve(ifcModel);
        }, undefined, (err) => {
            console.error("[VIEWER] Web-IFC load error:", err);
            window.showPlaceholder("IFC_LOAD_ERROR");
            reject(err);
        });
    });
};

window.loadGLTFModel = function(url) {
    const loader = new GLTFLoader();
    loader.load(url, (gltf) => {
        modelObject = gltf.scene;
        scene.add(modelObject);
        window.fitCameraToModel();
        document.getElementById('viewer-loading').style.display = 'none';
    }, undefined, (err) => {
        console.error("[VIEWER] GLTF load error:", err);
        window.showPlaceholder("MODEL_TRANSFER_ERROR");
    });
};

window.fitCameraToModel = function() {
    if (!modelObject) return;
    const box = new THREE.Box3().setFromObject(modelObject);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    // Move camera so it's far out enough to see the whole object
    let dist = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.5;
    camera.position.set(center.x + dist, center.y + dist, center.z + dist);
    controls.target.copy(center);
    controls.update();
};

window.showPlaceholder = function(msg) {
    const group = new THREE.Group();
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.5, roughness: 0.7 });
    const base = new THREE.Mesh(new THREE.BoxGeometry(20, 0.5, 20), baseMat);
    base.position.y = -0.25;
    group.add(base);

    const blockMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.3, roughness: 0.6 });
    const accentMat = new THREE.MeshStandardMaterial({ color: 0xe31e24, metalness: 0.4, roughness: 0.5 });

    [{w:4,h:8,d:4,x:-5,z:-5},{w:3,h:12,d:3,x:0,z:0},{w:5,h:6,d:4,x:5,z:-3},{w:3,h:10,d:3,x:-3,z:5},{w:4,h:5,d:5,x:5,z:5}]
    .forEach((p, i) => {
        const mat = i === 1 ? accentMat : blockMat;
        const block = new THREE.Mesh(new THREE.BoxGeometry(p.w, p.h, p.d), mat);
        block.position.set(p.x, p.h / 2, p.z);
        group.add(block);
    });

    modelObject = group;
    scene.add(modelObject);
    window.fitCameraToModel();
    document.getElementById('viewer-loading').style.display = 'none';
    console.warn("[VIEWER] Placeholder active:", msg);
};

window.highlightElementByName = function(name) {
    // Basic implementation since raw geometry vertices are harder to individually color without subset handling in simple mode.
    console.log("Highlight requested:", name);
};

window.resetCamera = function() {
    window.fitCameraToModel();
};

async function loadContext() {
    const pid = localStorage.getItem('currentProjectId');
    if (!pid) return;

    try {
        const [projResp, elementsResp] = await Promise.all([
            fetch('/api/v1/projects/'),
            fetch(`/api/v1/projects/${pid}/bim-elements`)
        ]);

        const projects = await projResp.json();
        const project = projects.find(p => p.id == pid);
        const bimData = await elementsResp.json();

        if (project) {
            document.getElementById('projectTitleHeader').textContent = project.name.toUpperCase();
            document.getElementById('projectBadge').style.display = 'block';
            window.init3D(bimData.model_url);
        }

        if (['admin', 'director', 'manager'].includes(userRole)) {
            const card = document.getElementById('createUpdateCard');
            if (card) card.style.display = 'block';
        }

        loadUpdates(pid);
    } catch (err) { console.error("CONTEXT_LOAD_ERROR", err); }
}

async function loadUpdates(pid) {
    const container = document.getElementById('updateGridBody');
    try {
        const resp = await fetch(`/api/v1/projects/${pid}/project-updates`);
        const updates = await resp.json();

        if (updates.length === 0) {
            container.innerHTML = '<div style="padding: 5rem; text-align: center; color: var(--text-muted); font-weight: 900; text-transform: uppercase; letter-spacing: 0.25em; opacity: 0.5;">No active project updates detected</div>';
            return;
        }

        const statusColors = { not_started: '#94a3b8', in_progress: '#FF9800', completed: '#3B82F6', inspected: '#8B5CF6', approved: '#10B981', blocked: '#E31E24' };

        container.innerHTML = updates.map((upd, idx) => `
            <div class="glass-card update-card reveal-text reveal-delay-${(idx % 4) + 1}"
                 style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); border-left: 5px solid ${statusColors[upd.status] || '#94a3b8'}; padding: 2.5rem; cursor: pointer;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                        <span style="font-size: 0.55rem; background: rgba(227,30,36,0.1); color: var(--brand-red); padding: 4px 10px; border-radius: 4px; font-weight: 900;">STATUS_UPDATE</span>
                    </div>
                    <h4 style="font-size: 1.5rem; font-weight: 900; margin-bottom: 1.5rem; color: white;">${upd.name}</h4>
                    <div class="progress-bar" style="max-width: 400px; margin-bottom: 1rem;"><div class="progress-fill" style="width: ${upd.progress_pct}%"></div></div>
                    <div style="display: flex; gap: 2rem; font-size: 0.7rem; color: var(--text-muted); font-weight: 900; text-transform: uppercase;">
                        <span>STATUS: ${upd.status.replace('_', ' ')}</span>
                        <span>PROGRESS: ${upd.progress_pct}%</span>
                        <span>BUDGET: ₦${Number(upd.budget_amount).toLocaleString()}</span>
                    </div>
                </div>
                <div style="display: flex; gap: 1rem;">
                    ${['admin','manager','director'].includes(userRole) ? `<button onclick="event.stopPropagation(); window.deleteUpdate(${upd.id})" class="btn-modern btn-ghost" style="padding: 0.6rem; border-color: rgba(227,30,36,0.2); color: var(--brand-red);">&times;</button>` : ''}
                </div>
            </div>
        `).join('');
    } catch (err) { console.error("UPDATE_LOAD_ERROR", err); }
}

document.getElementById('createUpdateForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pid = localStorage.getItem('currentProjectId');
    const fd = new FormData(e.target);
    const body = {
        project_id: parseInt(pid),
        name: fd.get('name').toUpperCase(),
        budget_amount: parseFloat(fd.get('budget_amount')) || 0,
        priority: fd.get('priority'),
        status: 'not_started',
        start_date: fd.get('start_date') ? new Date(fd.get('start_date')).toISOString() : null,
        due_date: fd.get('due_date') ? new Date(fd.get('due_date')).toISOString() : null
    };

    const r = await fetch('/api/v1/project-updates/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (r.ok) { e.target.reset(); loadContext(); } else { alert("Failed to create update."); }
});

window.deleteUpdate = async function(id) {
    if (!confirm('Delete this project update?')) return;
    const r = await fetch(`/api/v1/project-updates/${id}`, { method: 'DELETE' });
    if (r.ok) { location.reload(); }
};

loadContext();
</script>
{% endblock %}"""

out_html = re.sub(r'\{% block scripts %}.*?\{% endblock %\}', new_scripts, html, flags=re.DOTALL)
with open(r"c:\Users\Administrator\outbound-caller-python\templates\project_updates.html", "w", encoding="utf-8") as f:
    f.write(out_html)
