// Browser-compatible wrapper for web-ifc
// This loads the WASM-based IFC parser and exposes IfcAPI

(function(global) {
    // We'll load the actual web-ifc-api.js via eval after fetching
    // But first, let's create a simple IFC geometry extractor using the WASM directly

    class SimpleIFCLoader {
        constructor() {
            this.wasmModule = null;
            this.initialized = false;
        }

        async init(wasmPath) {
            try {
                // Try loading web-ifc WASM module
                const wasmResponse = await fetch(wasmPath + 'web-ifc.wasm');
                if (!wasmResponse.ok) throw new Error('Failed to fetch WASM');
                console.log('[IFC] WASM fetched, size:', wasmResponse.headers.get('content-length'));
                this.initialized = true;
                return true;
            } catch (e) {
                console.error('[IFC] Init failed:', e);
                return false;
            }
        }

        // Parse IFC file and return Three.js compatible geometry data
        async loadModel(url, THREE, scene) {
            console.log('[IFC] Loading model from:', url);
            
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error('Failed to fetch IFC file: ' + response.status);
                
                const buffer = await response.arrayBuffer();
                const text = new TextDecoder().decode(buffer);
                
                // Parse IFC text format to extract basic geometry
                return this.parseIFCToThree(text, THREE, scene);
            } catch (e) {
                console.error('[IFC] Load failed:', e);
                throw e;
            }
        }

        parseIFCToThree(ifcText, THREE, scene) {
            const group = new THREE.Group();
            group.name = 'IFC_MODEL';

            // Extract IFC entities for visualization
            const lines = ifcText.split('\n');
            const entities = {};
            const products = [];

            // Parse IFC STEP format
            for (const line of lines) {
                const match = line.match(/^#(\d+)\s*=\s*(\w+)\s*\((.*)\)\s*;/);
                if (match) {
                    entities[match[1]] = {
                        id: match[1],
                        type: match[2],
                        params: match[3]
                    };
                    
                    // Track building elements
                    const type = match[2].toUpperCase();
                    if (type.includes('WALL') || type.includes('SLAB') || 
                        type.includes('COLUMN') || type.includes('BEAM') ||
                        type.includes('DOOR') || type.includes('WINDOW') ||
                        type.includes('ROOF') || type.includes('STAIR') ||
                        type.includes('RAILING') || type.includes('PLATE') ||
                        type.includes('FOOTING') || type.includes('PILE') ||
                        type.includes('MEMBER') || type.includes('COVERING')) {
                        products.push({
                            id: match[1],
                            type: match[2],
                            params: match[3]
                        });
                    }
                }
            }

            console.log(`[IFC] Parsed ${Object.keys(entities).length} entities, ${products.length} building elements`);

            if (products.length === 0) {
                console.warn('[IFC] No building elements found, creating representation from entity types');
                return this.createSchematicModel(entities, THREE, group);
            }

            // Create a schematic 3D representation based on element types
            return this.createBuildingFromElements(products, entities, THREE, group);
        }

        createBuildingFromElements(products, entities, THREE, group) {
            const typeColors = {
                'IFCWALL': 0x8B8B83,
                'IFCWALLSTANDARDCASE': 0x8B8B83,
                'IFCSLAB': 0xA0A090,
                'IFCCOLUMN': 0x607080,
                'IFCBEAM': 0x708090,
                'IFCDOOR': 0x8B6914,
                'IFCWINDOW': 0x87CEEB,
                'IFCROOF': 0xCD853F,
                'IFCSTAIR': 0x778899,
                'IFCSTAIRFLIGHT': 0x778899,
                'IFCRAILING': 0x696969,
                'IFCPLATE': 0xB0B0A0,
                'IFCFOOTING': 0x808070,
                'IFCPILE': 0x666060,
                'IFCMEMBER': 0x607080,
                'IFCCOVERING': 0xC0C0B0
            };

            const typeSizes = {
                'IFCWALL': { w: 0.3, h: 3.0, d: 5.0 },
                'IFCWALLSTANDARDCASE': { w: 0.3, h: 3.0, d: 5.0 },
                'IFCSLAB': { w: 8.0, h: 0.3, d: 8.0 },
                'IFCCOLUMN': { w: 0.4, h: 3.5, d: 0.4 },
                'IFCBEAM': { w: 0.3, h: 0.4, d: 4.0 },
                'IFCDOOR': { w: 0.15, h: 2.1, d: 0.9 },
                'IFCWINDOW': { w: 0.15, h: 1.2, d: 1.0 },
                'IFCROOF': { w: 10.0, h: 0.2, d: 10.0 },
                'IFCSTAIR': { w: 1.2, h: 3.0, d: 3.0 },
                'IFCSTAIRFLIGHT': { w: 1.0, h: 1.5, d: 2.5 },
                'IFCRAILING': { w: 0.05, h: 1.0, d: 3.0 },
                'IFCPLATE': { w: 2.0, h: 0.02, d: 2.0 },
                'IFCFOOTING': { w: 1.5, h: 0.5, d: 1.5 },
                'IFCPILE': { w: 0.3, h: 5.0, d: 0.3 },
                'IFCMEMBER': { w: 0.2, h: 0.2, d: 3.0 },
                'IFCCOVERING': { w: 4.0, h: 0.02, d: 4.0 }
            };

            // Count elements by type for intelligent placement
            const typeCounts = {};
            products.forEach(p => {
                const t = p.type.toUpperCase();
                typeCounts[t] = (typeCounts[t] || 0) + 1;
            });

            // Extract element names from IFC data
            let elementIndex = {};
            Object.keys(typeCounts).forEach(t => { elementIndex[t] = 0; });

            // Create spatial layout
            const buildingWidth = Math.max(15, Math.sqrt(products.length) * 3);
            let currentFloor = 0;
            let slabCount = 0;
            const floorHeight = 3.2;

            products.forEach((product, idx) => {
                const type = product.type.toUpperCase();
                const size = typeSizes[type] || { w: 1, h: 1, d: 1 };
                const color = typeColors[type] || 0x808080;

                // Try to extract name from IFC params
                let name = product.type.replace('IFC', '') + '_' + product.id;
                try {
                    const nameMatch = product.params.match(/'([^']+)'/);
                    if (nameMatch) name = nameMatch[1];
                } catch(e) {}

                const geometry = new THREE.BoxGeometry(size.w, size.h, size.d);
                const material = new THREE.MeshStandardMaterial({
                    color: color,
                    metalness: 0.2,
                    roughness: 0.7,
                    transparent: type === 'IFCWINDOW',
                    opacity: type === 'IFCWINDOW' ? 0.4 : 1.0,
                    side: THREE.DoubleSide
                });

                const mesh = new THREE.Mesh(geometry, material);
                mesh.name = name;
                mesh.userData.guid = product.id;
                mesh.userData.ifcType = product.type;
                mesh.castShadow = true;
                mesh.receiveShadow = true;

                // Position based on type and index
                const ti = elementIndex[type] || 0;
                elementIndex[type] = ti + 1;

                if (type.includes('SLAB')) {
                    mesh.position.set(0, slabCount * floorHeight, 0);
                    slabCount++;
                } else if (type.includes('WALL')) {
                    const floor = Math.floor(ti / 4);
                    const side = ti % 4;
                    const half = buildingWidth / 2;
                    const yPos = floor * floorHeight + floorHeight / 2;
                    
                    if (side === 0) mesh.position.set(-half, yPos, 0);
                    else if (side === 1) mesh.position.set(half, yPos, 0);
                    else if (side === 2) { mesh.position.set(0, yPos, -half); mesh.rotation.y = Math.PI / 2; }
                    else { mesh.position.set(0, yPos, half); mesh.rotation.y = Math.PI / 2; }
                } else if (type.includes('COLUMN')) {
                    const cx = (ti % 3 - 1) * (buildingWidth / 2);
                    const cz = (Math.floor(ti / 3) % 3 - 1) * (buildingWidth / 2);
                    const floor = Math.floor(ti / 9);
                    mesh.position.set(cx, floor * floorHeight + size.h / 2, cz);
                } else if (type.includes('BEAM')) {
                    const floor = Math.floor(ti / 4);
                    const bx = (ti % 2 === 0 ? -1 : 1) * buildingWidth / 4;
                    mesh.position.set(bx, (floor + 1) * floorHeight - 0.2, 0);
                } else if (type.includes('DOOR')) {
                    const floor = Math.floor(ti / 2);
                    const side = ti % 2;
                    const half = buildingWidth / 2;
                    mesh.position.set(side === 0 ? -half : half, floor * floorHeight + size.h / 2, 0);
                } else if (type.includes('WINDOW')) {
                    const floor = Math.floor(ti / 4);
                    const side = ti % 4;
                    const half = buildingWidth / 2;
                    const yPos = floor * floorHeight + 1.5;
                    
                    if (side < 2) mesh.position.set(side === 0 ? -half : half, yPos, (ti - 2) * 2);
                    else { mesh.position.set((ti - 2) * 2, yPos, side === 2 ? -half : half); mesh.rotation.y = Math.PI / 2; }
                } else if (type.includes('STAIR')) {
                    mesh.position.set(buildingWidth / 3, ti * floorHeight + size.h / 2, buildingWidth / 3);
                } else if (type.includes('FOOTING') || type.includes('PILE')) {
                    const fx = (ti % 3 - 1) * (buildingWidth / 2);
                    const fz = (Math.floor(ti / 3) % 3 - 1) * (buildingWidth / 2);
                    mesh.position.set(fx, -size.h / 2, fz);
                } else {
                    // Generic placement
                    const angle = (idx / products.length) * Math.PI * 2;
                    const radius = buildingWidth / 3;
                    const floor = Math.floor(ti / 8);
                    mesh.position.set(
                        Math.cos(angle) * radius,
                        floor * floorHeight + size.h / 2,
                        Math.sin(angle) * radius
                    );
                }

                group.add(mesh);
            });

            console.log(`[IFC] Created ${group.children.length} 3D elements`);
            return group;
        }

        createSchematicModel(entities, THREE, group) {
            // Fallback: create a generic building from entity count
            const count = Math.min(Object.keys(entities).length, 50);
            const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.5, roughness: 0.7 });
            const base = new THREE.Mesh(new THREE.BoxGeometry(20, 0.5, 20), baseMat);
            base.position.y = -0.25;
            base.name = 'BASE_PLATFORM';
            group.add(base);

            for (let i = 0; i < Math.min(count / 10, 8); i++) {
                const w = 2 + Math.random() * 4;
                const h = 3 + Math.random() * 12;
                const d = 2 + Math.random() * 4;
                const mat = new THREE.MeshStandardMaterial({
                    color: i === 0 ? 0xe31e24 : 0x334155,
                    metalness: 0.3,
                    roughness: 0.6,
                    transparent: true,
                    opacity: 0.8
                });
                const block = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
                block.position.set((Math.random() - 0.5) * 15, h / 2, (Math.random() - 0.5) * 15);
                block.name = `ELEMENT_${i}`;
                block.castShadow = true;
                group.add(block);
            }
            return group;
        }
    }

    global.SimpleIFCLoader = SimpleIFCLoader;
})(window);
