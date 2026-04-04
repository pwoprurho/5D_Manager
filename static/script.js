// ===== 5D Project Manager - ELECTION RESULTS MANAGEMENT =====
// Clean, focused JavaScript for core functionality

// ===== DOM ELEMENTS =====
const navTabs = document.querySelectorAll(".nav-tab");
const tabContents = document.querySelectorAll(".tab-content");
const resultUploadForm = document.getElementById("result-upload-form");
const uploadStatus = document.getElementById("upload-status");
const loadingOverlay = document.getElementById("loading-overlay");

// ===== GLOBAL STATE =====
let dashboardMap;
let dashboardChart;
let mapMarkers = [];
window.currentElectionId = null; // Global persistence

// ===== UTILITIES: PREMIUM NOTIFICATIONS =====
/**
 * Shows a premium toast notification
 * @param {string} message - The message to display
 * @param {'success' | 'error' | 'info'} type - The type of toast
 */
window.showToast = function (message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'exclamation-triangle';

    toast.innerHTML = `
        <div class="toast-icon"><i class="fas fa-${icon}"></i></div>
        <div class="toast-message">${message}</div>
        <div class="toast-close" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></div>
    `;

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'toast-fade-out 0.4s ease-in forwards';
        setTimeout(() => toast.remove(), 400);
    }, 5000);
};

// Replace window.alert with showToast where appropriate (optional but recommended)
// window.alert = (msg) => window.showToast(msg, 'info');

/**
 * Enhanced fetch with error handling and toast support
 */
window.safeFetch = async function (url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Fetch error [${url}]:`, error);
        window.showToast(error.message || 'A network error occurred', 'error');
        throw error;
    }
};

// ===== SOCKET.IO =====
// Initialize Socket.IO connection
let socket;
try {
    if (typeof io !== 'undefined') {
        socket = io();
        socket.on("connect", () => {
            console.log("Connected to server via WebSocket");
        });
        socket.on("sync_complete", (data) => {
            showToast(data.message, 'success');
            // Refresh lists if on the sync tab
            const activeTab = document.querySelector('.admin-tab.active');
            if (activeTab && activeTab.dataset.tab === 'lgas') {
                loadAdminLgasAndPus();
            }
        });
        socket.on("new_result", (data) => {
            console.log("New result received:", data);
            // Refresh data if on monitor or results tab
            if (document.querySelector('.nav-tab[data-tab="monitor"]')?.classList.contains('active')) {
                loadMonitoringData();
                addLiveUpdate(data);
            }
            if (document.querySelector('.nav-tab[data-tab="results"]')?.classList.contains('active')) {
                loadResultsData();
            }
        });
        socket.on("external_news_detected", (data) => {
            console.log("External news detected:", data);
            if (document.querySelector('.nav-tab[data-tab="news"]')?.classList.contains('active')) {
                addExternalNewsItem(data);
            }
        });
        socket.on("threat_alert_detected", (data) => {
            console.log("THREAT DETECTED:", data);
            if (document.querySelector('.nav-tab[data-tab="monitor"]')?.classList.contains('active')) {
                addEmergingThreat(data);
            }
            window.showToast(`🔥 Emerging Threat: ${data.title}`, 'error');
        });
    } else {
        console.warn("Socket.IO not loaded. Real-time features disabled.");
    }
} catch (e) {
    console.warn("Error initializing Socket.IO:", e);
}

if (socket) {
    socket.on('new_monitoring_alert', (data) => {
        handleRealTimeAlert(data);
    });

    socket.on('new_report', (data) => {
        addLiveUpdate(data);
    });
}

function addLiveUpdate(data) {
    // Filter updates by the currently selected election
    if (window.currentElectionId && data.election_id && String(data.election_id) !== String(window.currentElectionId)) {
        console.log(`[FILTER] Ignoring update for election ${data.election_id} (current: ${window.currentElectionId})`);
        return;
    }

    const list = document.getElementById("live-updates-list");
    if (!list) return;

    if (list.querySelector('p')) {
        list.querySelectorAll('p').forEach(p => p.remove());
    }

    const item = document.createElement("div");
    item.className = "update-item";
    item.style = "border-bottom: 1px solid #eee; padding: 0.5rem 0; margin-bottom: 0.5rem; animation: slideIn 0.3s;";
    item.innerHTML = `
        <div style="font-weight: bold; color: var(--primary-red);">New Result Uploaded</div>
        <div style="font-size: 0.9rem;">PU Code: ${data.pu_code}</div>
        <div style="color: #666; font-size: 0.8rem;">${new Date(data.timestamp).toLocaleTimeString()}</div>
        <div style="margin-top: 5px; font-size: 0.85rem; background: #f9f9f9; padding: 5px; border-radius: 4px;">
            <span style="font-size:0.8em; color:blue; cursor:pointer;" onclick="viewResultDetails('${data.pu_code}')">View OCR Analysis</span>
        </div>
    `;
    list.prepend(item);
}

function handleRealTimeAlert(alert) {
    // Filter alerts by the currently selected election
    if (window.currentElectionId && alert.election_id && String(alert.election_id) !== String(window.currentElectionId)) {
        console.log(`[FILTER] Ignoring alert for election ${alert.election_id} (current: ${window.currentElectionId})`);
        return;
    }

    const newsList = document.getElementById('news-feed-list');
    const socialList = document.getElementById('social-feed-list');
    const alertList = document.getElementById('alerts-list');

    // Determine color based on urgency
    const color = alert.urgency === 'critical' ? '#dc2626' : (alert.urgency === 'warning' ? '#f59e0b' : '#3b82f6');

    // 1. Update News Feed if applicable
    if (newsList && alert.source === 'news') {
        const item = document.createElement('div');
        item.className = "news-item";
        item.style = `border-left: 3px solid ${color}; padding-left: 1rem; margin-bottom: 1.5rem; animation: fadeIn 0.5s;`;
        item.innerHTML = `
            <h4 style="margin-bottom: 0.25rem;">${alert.category}: Ground Report</h4>
            <p style="color: #666; font-size: 0.8rem; margin-bottom: 0.5rem;"><i class="far fa-clock"></i> ${alert.timestamp} • ${alert.source_name}</p>
            <p style="font-size: 0.9rem;">${alert.content}</p>
        `;
        newsList.prepend(item);
    }

    // 2. Update Social Feed if applicable
    if (socialList && alert.source === 'social') {
        const item = document.createElement('div');
        item.className = "social-item";
        item.style = `background: ${alert.urgency === 'critical' ? '#fff1f2' : '#f8fafc'}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid ${alert.urgency === 'critical' ? '#fecaca' : '#e2e8f0'}; animation: slideIn 0.4s;`;
        item.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                <div style="width: 32px; height: 32px; background: ${color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 0.75rem;">${alert.source_name[0].toUpperCase()}</div>
                <strong>@${alert.source_name.replace(' ', '')}</strong>
                <span style="color: #666; font-size: 0.8rem;"> • ${alert.timestamp}</span>
            </div>
            <p style="font-size: 0.9rem;">${alert.content}</p>
            <div style="margin-top:0.5rem;"><span class="badge" style="background:${color}22; color:${color}; font-size:0.65rem;">${alert.category.toUpperCase()} [Sentiment: ${alert.sentiment}]</span></div>
        `;
        socialList.prepend(item);
    }

    // 3. Update Priority Alerts if Critical
    if (alertList && alert.urgency === 'critical') {
        const item = document.createElement('div');
        item.style = `background: #fff5f5; padding: 1rem; border-radius: 8px; border: 1px solid #feb2b2; margin-bottom:1rem; border-left: 5px solid #dc2626; animation: pulse 2s infinite;`;
        item.innerHTML = `
            <h4 style="color: #c53030; margin-bottom: 0.5rem;"><i class="fas fa-exclamation-circle"></i> NEW CRITICAL: ${alert.category.toUpperCase()}</h4>
            <p style="font-size: 0.9rem; font-weight: bold;">${alert.content}</p>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.5rem;">
                 <span style="font-size: 0.8rem; color: #666;">PU: ${alert.pu_code || 'Multiple'}</span>
                 <button class="btn btn-primary btn-sm" onclick="investigateConflict('${alert.pu_code}')">Investigate</button>
            </div>
        `;
        alertList.prepend(item);
        showToast(`CRITICAL EVENT DETECTED: ${alert.category}`, 'error');
    }
}

// ===== ELECTION SELECTOR SYNC =====
function syncAllElectionSelectors(electionId) {
    if (!electionId) return;
    window.currentElectionId = electionId;

    const selectors = [
        "election-select",
        "dashboard-election-select",
        "results-election-select",
        "inc-election-select",
        "dossier-election-select",
        "matrix-election-select"
    ];

    selectors.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.value !== electionId) {
            el.value = electionId;
        }
    });

    console.log(`[SYNC] Election set to: ${electionId}`);

    // Trigger data reload for the current active tab to keep UI in sync
    const activeTab = document.querySelector('.nav-tab.active');
    if (activeTab) {
        const tabName = activeTab.dataset.tab;
        console.log(`[SYNC] Reloading data for active tab: ${tabName}`);
        loadTabData(tabName);
    }
}

// Mock function for view details
window.viewResultDetails = function (puCode) {
    alert("Function to fetch full OCR details for " + puCode + " would go here.");
};

// ===== TAB MANAGEMENT =====
function switchTab(targetTab) {
    // Remove active class from all tabs
    navTabs.forEach(tab => tab.classList.remove("active"));

    // Hide all tab contents
    tabContents.forEach(content => content.classList.remove("active"));

    // Add active class to clicked tab
    const activeTab = document.querySelector(`[data-tab="${targetTab}"]`);
    if (activeTab) {
        activeTab.classList.add("active");
    }

    // Show target tab content
    const targetContent = document.getElementById(`${targetTab}-tab`);
    if (targetContent) {
        targetContent.classList.add("active");
    }

    // Load data for the tab
    loadTabData(targetTab);
}

// Global listener for election changes to trigger sync
document.addEventListener("change", (e) => {
    const electionSelectors = [
        "election-select",
        "dashboard-election-select",
        "results-election-select",
        "inc-election-select",
        "dossier-election-select",
        "matrix-election-select"
    ];

    if (electionSelectors.includes(e.target.id)) {
        syncAllElectionSelectors(e.target.value);
    }
});

// ===== EVENT LISTENERS =====
navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
        const targetTab = tab.getAttribute("data-tab");
        switchTab(targetTab);
    });
});

// ===== FORM HANDLING =====
// When the form uses a standard submit target, bypass JavaScript intercept.
// The backend /login route handles form posts. If you prefer AJAX login, uncomment below.
const loginForm = document.getElementById("login-form");
if (loginForm) {
    // Keep native HTML POST behavior; removing JS intercept avoids 405 issues.
    // loginForm.addEventListener("submit", ...)
}


const registerForm = document.getElementById("register-form"); // Assuming register form id
if (registerForm) {
    // Keep native HTML POST behavior; removing JS intercept avoids 405 issues.
    // registerForm.addEventListener("submit", ...)
}


if (resultUploadForm) {
    resultUploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const formData = new FormData(resultUploadForm);

        // Serialize party results if any
        const partyInputs = document.querySelectorAll('#party-inputs div');
        const partyResults = {};
        partyInputs.forEach(div => {
            const inputs = div.querySelectorAll('input');
            if (inputs.length >= 2) {
                const party = inputs[0].value;
                const votes = inputs[1].value;
                if (party && votes) {
                    partyResults[party] = parseInt(votes);
                }
            }
        });
        formData.append('party_results', JSON.stringify(partyResults));

        // Show loading
        showLoading(true);

        try {
            const response = await fetch("/api/upload-result", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                // Instead of resetting, show verification
                document.getElementById('upload-stage').style.display = 'none';
                document.getElementById('verify-stage').style.display = 'block';

                document.getElementById('report-id-input').value = result.report_id;
                document.getElementById('ocr-markdown-editor').value = result.markdown || "";

                // Trigger initial live preview
                if (window.updateLivePreview) window.updateLivePreview();

                // Show the image preview
                const verifiedImg = document.getElementById('verified-img');
                if (verifiedImg && result.image_url) {
                    verifiedImg.src = result.image_url;
                }

                showStatus("success", "Result processed! Please verify figures.");
            } else {
                showStatus("error", result.error || "Upload failed. Please try again.");
            }
        } catch (error) {
            console.error("Upload error:", error);
            showStatus("error", "Network error. Please check your connection and try again.");
        } finally {
            showLoading(false);
        }
    });
}

// ZOOM LOGIC
function zoomImage() {
    const src = document.getElementById('verified-img')?.src;
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    if (modal && modalImg && src) {
        modalImg.src = src;
        modal.style.display = 'flex';
    }
}
window.zoomImage = zoomImage;

function resetUpload() {
    if (confirm("Are you sure? All current progress will be lost.")) {
        document.getElementById('result-upload-form').reset();
        document.getElementById('party-inputs').innerHTML = '';
        document.getElementById('upload-stage').style.display = 'block';
        document.getElementById('verify-stage').style.display = 'none';
    }
}

async function submitFinalVerification() {
    const reportId = document.getElementById('report-id-input').value;
    const markdown = document.getElementById('ocr-markdown-editor').value;
    const accreditedVoters = parseInt(document.getElementById('accredited-voters-input')?.value || 0);

    // 1. Basic Validation: Detect results
    const parsedData = jsParseMarkdownTable(markdown);
    if (Object.keys(parsedData).length === 0) {
        showStatus("error", "No party results detected. Please format as: | Party | Votes |");
        return;
    }

    // 2. Consistency Check: Accredited vs Total Cast
    const totalVotes = Object.values(parsedData).reduce((a, b) => a + b, 0);
    if (accreditedVoters > 0 && totalVotes > accreditedVoters) {
        if (!confirm(`🚨 DISCREPANCY: Total votes (${totalVotes}) > Accredited Voters (${accreditedVoters}). Proceed anyway?`)) {
            return;
        }
    }

    if (totalVotes === 0) {
        showStatus("error", "Total votes cannot be zero.");
        return;
    }

    showLoading(true);

    try {
        const formData = new FormData();
        formData.append('report_id', reportId);
        formData.append('ocr_markdown', markdown);
        formData.append('accredited_voters', accreditedVoters);

        const response = await fetch("/api/submit-final-markdown", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            showStatus("success", "Submission finalized and verified!");
            // Return to upload after short delay
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            const err = await response.json();
            showStatus("error", err.error || "Final submission failed.");
        }
    } catch (e) {
        showStatus("error", "Network error during finalization.");
    } finally {
        showLoading(false);
    }
}

// Export for inline usage
window.resetUpload = resetUpload;
window.submitFinalVerification = submitFinalVerification;

// ===== UTILITY FUNCTIONS =====
function showLoading(show) {
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? "flex" : "none";
    }
}

function showStatus(type, message) {
    if (uploadStatus) {
        uploadStatus.className = type === 'success' ? 'status-verified' : 'status-disputed';
        uploadStatus.style.color = type === 'success' ? '#10b981' : '#ef4444';
        uploadStatus.textContent = message;
        uploadStatus.style.display = "block";

        // Auto-hide after 5 seconds
        setTimeout(() => {
            uploadStatus.style.display = "none";
        }, 5000);
    }
}

function addPartyInput() {
    const container = document.getElementById('party-inputs');
    if (!container) return;

    const div = document.createElement('div');
    div.style.display = 'flex';
    div.style.gap = '1rem';
    div.style.marginBottom = '0.5rem';
    div.innerHTML = `
        <input type="text" placeholder="Party Name (e.g. APC)" style="flex:1; padding:0.5rem; border:1px solid #ccc; border-radius:var(--radius-md);">
        <input type="number" placeholder="Votes" style="flex:1; padding:0.5rem; border:1px solid #ccc; border-radius:var(--radius-md);">
        <button type="button" onclick="this.parentElement.remove()" style="background:var(--accent-red); color:white; border:none; padding:0 0.5rem; border-radius:var(--radius-md); cursor:pointer;">X</button>
    `;
    container.appendChild(div);
}
// Export for inline usage if needed
window.addPartyInput = addPartyInput;

// ===== DATA LOADING =====
async function loadTabData(tabName) {
    try {
        switch (tabName) {
            case "upload":
                await loadUploadTabDependencies();
                break;
            case "monitor":
                await loadMonitoringData();
                break;
            case "news":
                await fetchMonitoringAlerts();
                await loadConflictsDataInDashboard();
                break;
            case "results":
                await loadResultsData();
                break;
            case "conflicts":
                await loadConflictsData();
                break;
            case "admin":
                await loadAdminPanelData();
                break;
            case "results":
                await loadResultsData();
                break;
            case "incidents":
                await loadFieldIncidents();
                break;
            case "lawfare-dossier":
                const dossierId = window.currentElectionId || document.getElementById("dashboard-election-select")?.value || document.getElementById("results-election-select")?.value;
                if (typeof loadLawfareDossier === 'function') {
                    await loadLawfareDossier(dossierId);
                }
                break;
            case "lawfare-matrix":
                const matrixId = window.currentElectionId || document.getElementById("dashboard-election-select")?.value || document.getElementById("results-election-select")?.value;
                if (typeof loadLawfareMatrix === 'function') {
                    await loadLawfareMatrix(matrixId);
                }
                break;
        }
    } catch (error) {
        console.error(`Error loading ${tabName} data:`, error);
    }
}

async function loadUploadTabDependencies() {
    // Load elections if not already loaded (Target main + independent selectors)
    const electionSelectors = [document.getElementById("election-select"), document.getElementById("inc-election-select")];
    if (electionSelectors.some(s => s && s.options.length <= 1)) {
        await loadElections();
    }
    // Load states if not already loaded
    const stateSelectors = [document.getElementById("state-select"), document.getElementById("inc-state-select")];
    if (stateSelectors.some(s => s && s.options.length <= 1)) {
        await loadStates();
    }
}

// Introduce a global variable to store fetched elections
window.cachedElections = [];

async function loadElections(force = false) {
    // Only fetch if not already cached or if forced
    if (force || window.cachedElections.length === 0) {
        try {
            const response = await fetch("/api/elections");
            window.cachedElections = await response.json();
        } catch (error) {
            console.error("Error loading elections:", error);
            return;
        }
    }

    const electionSelect = document.getElementById("election-select");
    const dashSelect = document.getElementById("dashboard-election-select");
    const resSelect = document.getElementById("results-election-select");
    const incSelect = document.getElementById("inc-election-select");
    const dossierSelect = document.getElementById("dossier-election-select");
    const matrixSelect = document.getElementById("matrix-election-select");

    // Clear and populate selectors
    [electionSelect, dashSelect, resSelect, incSelect, dossierSelect, matrixSelect].forEach(select => {
        if (!select) return;

        // Preserve current value if any
        const currentValue = select.value;

        select.innerHTML = `<option value="">Select ${select.id === 'election-select' ? 'Election' : 'an Election'}</option>`;
        window.cachedElections.forEach(e => {
            const option = document.createElement("option");
            option.value = e.id;
            option.textContent = (select.id === 'election-select') ? e.name : `${e.name} (${e.phase})`;
            select.appendChild(option);
        });

        // Restore value if still valid, otherwise default to active/cached
        if (currentValue && window.cachedElections.some(e => e.id == currentValue)) {
            select.value = currentValue;
        } else if (window.currentElectionId && window.cachedElections.some(e => e.id == window.currentElectionId)) {
            select.value = window.currentElectionId;
        } else if ((select.id === 'dashboard-election-select' || select.id === 'results-election-select' || select.id === 'dossier-election-select' || select.id === 'matrix-election-select') && !select.value) {
            const active = window.cachedElections.find(e => e.phase === 'active') || window.cachedElections[0];
            if (active) select.value = active.id;
        }
    });

    // Ensure window.currentElectionId is set if we have a default selection
    if (!window.currentElectionId) {
        const fallback = document.getElementById("dashboard-election-select") || document.getElementById("results-election-select");
        if (fallback && fallback.value) {
            window.currentElectionId = fallback.value;
        }
    }
}

async function loadStates() {
    try {
        const response = await fetch("/api/states");
        if (!response.ok) throw new Error('States API failed');
        const states = await response.json();

        // Populate ALL state selects marked with the common class or specific IDs including incident form
        const stateSelects = document.querySelectorAll("#state-select, #admin-election-state-select, #inc-state-select, .state-select-common");
        stateSelects.forEach(select => {
            if (select) {
                const currentValue = select.value;
                select.innerHTML = "<option value=\"\">Select State</option>";
                states.forEach(state => {
                    const option = document.createElement("option");
                    option.value = state.id;
                    option.textContent = state.name;
                    select.appendChild(option);
                });
                if (currentValue) select.value = currentValue;
            }
        });

        console.log(`Loaded ${states.length} states into dropdowns`);
    } catch (error) {
        console.error("Error loading states:", error);
    }
}

async function loadMonitoringData() {
    try {
        await loadElections(); // Ensure elections are loaded/cached

        // Populate dashboard election selector
        const dashSelect = document.getElementById("dashboard-election-select");
        if (dashSelect && dashSelect.options.length <= 1) {
            // Force re-populate if empty
            await loadElections(true);
        }

        // Ensure listener is added only once
        if (dashSelect && !dashSelect.dataset.listenerAdded) {
            dashSelect.addEventListener("change", () => {
                const selectedId = dashSelect.value;
                if (selectedId) {
                    loadElectionAnalytics(selectedId);
                }
            });
            dashSelect.dataset.listenerAdded = "true";
        }

        // Auto-load first active election
        const activeElection = window.cachedElections.find(e => e.phase === 'active') || window.cachedElections[0];
        if (activeElection) {
            if (dashSelect && !dashSelect.value) dashSelect.value = activeElection.id;
            loadElectionAnalytics(activeElection.id);
            loadPendingReports(activeElection.id);
        }

        // Load Monitoring Feeds (News, Social, Alerts)
        await fetchMonitoringAlerts();
    } catch (e) {
        console.error("Error loading monitoring data:", e);
    }
}

async function loadConflictsData(targetId = "conflicts-content") {
    const container = document.getElementById(targetId);
    if (!container) return;

    try {
        // Find active election or default to ID 1
        const activeElection = window.cachedElections.find(e => e.phase === 'active') || { id: 1 };
        const summary = await safeFetch(`/api/election/${activeElection.id}/conflicts`);

        if (summary.total_conflicts === 0) {
            container.innerHTML = `
                <div style="background: #f0fdf4; border-radius: 8px; padding: 2rem; border: 1px solid #bbf7d0; display: flex; align-items: center; justify-content: center; gap: 1.5rem;">
                    <i class="fas fa-check-circle" style="color: #16a34a; font-size: 2.5rem;"></i>
                    <div style="text-align: left;">
                        <h3 style="color: #166534; margin: 0;">System Clear</h3>
                        <p style="margin: 0.5rem 0 0; color: #166534;">All election data currently matches integrity rules. No conflicts detected.</p>
                    </div>
                </div>
            `;
            return;
        }

        let html = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                <div class="stat-card premium-card" style="padding: 1.5rem; border-left: 4px solid #64748b;">
                    <div style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; font-weight: 600;">Total Issues</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #1e293b;">${summary.total_conflicts}</div>
                </div>
                <div class="stat-card premium-card" style="padding: 1.5rem; border-left: 4px solid var(--primary-red);">
                    <div style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; font-weight: 600;">Critical Alerts</div>
                    <div style="font-size: 2rem; font-weight: 800; color: var(--primary-red);">${summary.by_severity.critical || 0}</div>
                </div>
                <div class="stat-card premium-card" style="padding: 1.5rem; border-left: 4px solid #f59e0b;">
                    <div style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; font-weight: 600;">Potential Fraud</div>
                    <div style="font-size: 2rem; font-weight: 800; color: #f59e0b;">${summary.by_severity.error || 0}</div>
                </div>
            </div>
            
            <div class="premium-card" style="padding: 1rem; overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="text-align: left; background: #f8fafc;">
                            <th style="padding: 1rem; color: #64748b; font-weight: 600; border-bottom: 2px solid #e2e8f0;">Location</th>
                            <th style="padding: 1rem; color: #64748b; font-weight: 600; border-bottom: 2px solid #e2e8f0;">Type</th>
                            <th style="padding: 1rem; color: #64748b; font-weight: 600; border-bottom: 2px solid #e2e8f0;">Level</th>
                            <th style="padding: 1rem; color: #64748b; font-weight: 600; border-bottom: 2px solid #e2e8f0;">Description</th>
                            <th style="padding: 1rem; color: #64748b; font-weight: 600; border-bottom: 2px solid #e2e8f0;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        summary.conflicts.forEach(conflict => {
            const severityColor = conflict.severity === 'critical' ? 'var(--primary-red)' :
                conflict.severity === 'error' ? '#f59e0b' :
                    conflict.severity === 'warning' ? '#3b82f6' : '#64748b';

            let actionsHtml = `<button class="btn btn-red-block" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; margin-right: 5px;" onclick="investigateConflict('${conflict.id}')">Investigate</button>`;
            if (conflict.details && conflict.details.url) {
                actionsHtml += `<button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="window.open('${conflict.details.url}', '_blank')">Confirm Sources</button>`;
            }

            html += `
                <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.2s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='white'">
                    <td style="padding: 1rem;"><strong>${conflict.pu_code}</strong></td>
                    <td style="padding: 1rem;"><span style="background: ${severityColor}15; color: ${severityColor}; padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">${conflict.type.replace(/_/g, ' ')}</span></td>
                    <td style="padding: 1rem;"><span style="display: flex; align-items: center; gap: 0.4rem; color: ${severityColor}; font-weight: 600; font-size: 0.85rem;"><i class="fas fa-circle" style="font-size: 0.5rem;"></i> ${conflict.severity.toUpperCase()}</span></td>
                    <td style="padding: 1rem; font-size: 0.9rem; color: #334155;">${conflict.description}</td>
                    <td style="padding: 1rem;">${actionsHtml}</td>
                </tr>
            `;
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (error) {
        console.error("Conflict Detection Error:", error);
        container.innerHTML = '<div style="color: #ef4444; background: #fff1f2; padding: 1.5rem; border-radius: 8px; border: 1px solid #fecaca;"><i class="fas fa-exclamation-triangle"></i> Execution Error: Unable to run conflict detection engine.</div>';
    }
}

async function loadConflictsDataInDashboard() {
    await loadConflictsData("dashboard-conflicts-container");
}

window.investigateConflict = function (id) {
    showToast(`Initializing investigation portal for conflict ID: ${id}`, 'info');
}

// ===== NEWS MONITORING =====
async function fetchMonitoringAlerts() {
    try {
        const response = await fetch('/api/monitoring/alerts');
        const alerts = await response.json();

        const newsList = document.getElementById('news-feed-list');
        const socialList = document.getElementById('social-feed-list');
        const alertList = document.getElementById('alerts-list');

        if (newsList) {
            const newsAlerts = alerts.filter(a => a.source === 'news');
            newsList.innerHTML = newsAlerts.length === 0 ? '<p style="color:#666; padding:1rem;">No recent news alerts.</p>' :
                newsAlerts.map(a => `
                <div class="news-item" style="border-left: 3px solid ${a.color}; padding-left: 1rem; margin-bottom: 1.5rem;">
                    <h4 style="margin-bottom: 0.25rem;">
                        <a href="${a.url}" target="_blank" style="color: inherit; text-decoration: none; hover: text-decoration: underline;">
                            ${a.content} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; margin-left: 5px; opacity: 0.6;"></i>
                        </a>
                    </h4>
                    <p style="color: #64748b; font-size: 0.8rem; margin-bottom: 0.5rem;"><i class="far fa-clock"></i> ${a.time} • ${a.source_name}</p>
                    <span class="badge" style="background:${a.color}15; color:${a.color}; border:1px solid ${a.color}30; font-size:0.7rem; font-weight:700;">${a.category.toUpperCase()}</span>
                </div>
            `).join('');
        }

        if (socialList) {
            const socialAlerts = alerts.filter(a => a.source === 'social');
            socialList.innerHTML = socialAlerts.length === 0 ? '<p style="color:#666; padding:1rem;">No recent social alerts.</p>' :
                socialAlerts.map(a => `
                <div class="social-item" style="background: ${a.severity === 'critical' ? '#fff1f2' : '#f8fafc'}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid ${a.severity === 'critical' ? '#fecaca' : '#e2e8f0'};">
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <div style="width: 32px; height: 32px; background: ${a.color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 0.75rem; font-size: 0.8rem;">
                            ${a.source_name[0].toUpperCase()}
                        </div>
                        <div>
                            <strong>@${a.source_name}</strong>
                            <span style="color: #666; font-size: 0.8rem;"> • ${a.time}</span>
                        </div>
                    </div>
                    <p style="font-size: 0.9rem;">${a.content}</p>
                    <div style="margin-top:0.5rem;"><span class="badge" style="background:${a.color}22; color:${a.color}; font-size:0.65rem;">${a.category.replace('_', ' ').toUpperCase()}</span></div>
                </div>
            `).join('');
        }

        if (alertList) {
            const priorityAlerts = alerts.filter(a => a.severity === 'critical' || a.severity === 'high');
            alertList.innerHTML = priorityAlerts.length === 0 ? '<p style="color:#666; padding:1rem;">No critical alerts currently active.</p>' :
                priorityAlerts.map(a => `
                <div class="alert-item flagged-intel" style="background: ${a.color}08; padding: 1.25rem; border-radius: 12px; border: 1.5px solid ${a.color}30; margin-bottom:1.5rem; border-left: 4px solid ${a.color}; transition: all 0.2s ease;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                        <span style="color: ${a.color}; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;">
                            <i class="fas fa-shield-alt"></i> Flagged Intelligence
                        </span>
                        <span class="badge" style="background: ${a.color}; color: white; font-size: 0.65rem;">${a.severity.toUpperCase()}</span>
                    </div>
                    <h4 style="margin-bottom: 0.5rem; line-height: 1.4;">
                        <a href="${a.url || '#'}" target="_blank" style="color: #1e293b; text-decoration: none;">
                            ${a.content}
                        </a>
                    </h4>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1rem; border-top: 1px solid #e2e8f0; padding-top: 0.75rem;">
                         <span style="font-size: 0.75rem; color: #64748b;"><i class="fas fa-broadcast-tower"></i> ${a.source_name}</span>
                         <span style="font-size: 0.75rem; color: #64748b;">${a.category.toUpperCase()}</span>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error("Error fetching monitoring alerts:", e);
    }
}

function addExternalNewsItem(a) {
    const newsList = document.getElementById('news-feed-list');
    const socialList = document.getElementById('social-feed-list');
    if (!newsList || !socialList) return;

    const color = a.hostility_index > 0.6 ? '#ef4444' : (a.category === 'violence' ? '#ef4444' : '#3b82f6');
    const timestamp = new Date().toLocaleTimeString();

    if (a.source_type === 'news') {
        const item = document.createElement('div');
        item.className = 'news-item';
        item.style.cssText = `border-left: 3px solid ${color}; padding-left: 1rem; margin-bottom: 1.5rem; animation: slideIn 0.3s ease;`;
        item.innerHTML = `
            <h4 style="margin-bottom: 0.25rem;">
                <a href="${a.url || '#'}" target="_blank" style="color: inherit; text-decoration: none;">
                    ${a.title} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; margin-left: 5px; opacity: 0.6;"></i>
                </a>
            </h4>
            <p style="color: #64748b; font-size: 0.8rem; margin-bottom: 0.5rem;"><i class="far fa-clock"></i> ${timestamp} • ${a.source_name}</p>
            <div style="display:flex; gap:0.5rem; align-items:center;">
                <span class="badge" style="background:${color}15; color:${color}; border:1px solid ${color}30; font-size:0.7rem; font-weight:700;">${a.category.toUpperCase()}</span>
                ${a.hostility_index > 0.5 ? `<span style="font-size: 0.7rem; color: #ef4444; font-weight: 800;">🔥 HOSTILITY: ${(a.hostility_index * 100).toFixed(0)}%</span>` : ''}
            </div>
        `;
        newsList.prepend(item);
    } else {
        const item = document.createElement('div');
        item.className = 'social-item';
        item.style.cssText = `background: ${a.hostility_index > 0.7 ? '#fff1f2' : '#f8fafc'}; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid ${a.hostility_index > 0.7 ? '#fecaca' : '#e2e8f0'}; animation: slideIn 0.3s ease;`;
        item.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                <div style="width: 32px; height: 32px; background: ${color}; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 0.75rem; font-size: 0.8rem;">
                    ${a.source_name[0].toUpperCase()}
                </div>
                <div>
                    <strong>@${a.source_name}</strong>
                    <span style="color: #666; font-size: 0.8rem;"> • ${timestamp}</span>
                </div>
            </div>
            <p style="font-size: 0.9rem;">${a.content}</p>
            <div style="margin-top:0.5rem; display:flex; gap:0.5rem; align-items:center;">
                <span class="badge" style="background:${color}22; color:${color}; font-size:0.65rem;">${a.category.toUpperCase()}</span>
                ${a.hostility_index > 0.5 ? `<span style="font-size: 0.65rem; color: #ef4444; font-weight: 800;">🔥 HOSTILITY: ${(a.hostility_index * 100).toFixed(0)}%</span>` : ''}
            </div>
        `;
        socialList.prepend(item);
    }
}

function addEmergingThreat(a) {
    const list = document.getElementById('emerging-threats-list');
    if (!list) return;

    // Remove empty state if present
    const empty = list.querySelector('p');
    if (empty && empty.fontStyle === 'italic') empty.remove();

    const item = document.createElement('div');
    item.style.cssText = `background: #fff1f2; border-left: 4px solid #ef4444; padding: 1rem; margin-bottom: 1rem; border-radius: 6px; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.1); animation: pulseAlert 2s infinite;`;
    item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
            <span style="background: #ef4444; color: white; font-size: 0.7rem; font-weight: 800; padding: 0.1rem 0.5rem; border-radius: 4px;">HIGH HOSTILITY</span>
            <span style="font-size: 0.75rem; color: #ef4444; font-weight: bold;">${(a.index * 100).toFixed(0)}% Index</span>
        </div>
        <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem; color: #1e293b;">${a.location}</div>
        <p style="font-size: 0.85rem; color: #475569; margin-bottom: 0.5rem; line-height: 1.4;">${a.title}</p>
        <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Source: ${a.source}</div>
    `;
    list.prepend(item);

    // Auto-scroll to top of list
    list.scrollTop = 0;
}

async function loadPendingReports(electionId) {
    const list = document.getElementById("live-updates-list");
    if (!list) return;

    try {
        const response = await fetch(`/api/election/${electionId}/pending-reports`);
        const groupedData = await response.json();

        if (groupedData.length === 0) {
            list.innerHTML = '<p style="color: #666; font-style: italic;">No pending verified reports.</p>';
            return;
        }

        let html = '';
        groupedData.forEach(group => {
            html += `
                <div style="margin-bottom: 1rem;">
                    <h5 style="background: #fdfdfd; padding: 4px; border-left: 3px solid var(--primary-red); margin-bottom: 4px;">
                        ${group.ward} <small style="color:#666">(${group.lga})</small>
                    </h5>
                    ${group.reports.map(r => `
                        <div class="update-item" style="padding: 0.5rem; border-bottom: 1px solid #eee; margin-left: 0.5rem;">
                             <div style="font-weight: bold; font-size: 0.9rem;">PU: ${r.pu_code}</div>
                             <div style="font-size: 0.8rem; color: #666; display: flex; justify-content: space-between;">
                                <span>${new Date(r.timestamp).toLocaleTimeString()}</span>
                                <span style="color:blue; cursor:pointer;" onclick="viewResultDetails('${r.id}')">View</span>
                             </div>
                        </div>
                    `).join('')}
                </div>
            `;
        });

        list.innerHTML = html;
    } catch (e) {
        console.error("Error loading pending reports:", e);
    }
}

async function loadElectionAnalytics(electionId) {
    try {
        const response = await fetch(`/api/election/${electionId}/analytics`);
        const data = await response.json();

        // 1. Update stat cards
        updateStatCard("stat-registered", data.registered_voters?.toLocaleString() || 0);
        updateStatCard("stat-accredited", data.accredited_voters?.toLocaleString() || 0);
        updateStatCard("stat-total-votes", data.total_votes_cast?.toLocaleString() || 0);
        updateStatCard("stat-voted-pct", `${data.percentage_voted || 0}%`);
        updateStatCard("stat-reported-pus", `${data.reported_pus || 0}/${data.total_pus || 0}`);

        // 2. Render Party Standings PIE CHART
        updatePartyStandingsChart(data.party_standings);

        // 3. Render Party Standings LIST
        const standingsDiv = document.getElementById("party-standings-list");
        if (standingsDiv && data.party_standings) {
            if (data.party_standings.length === 0) {
                standingsDiv.innerHTML = '<p style="color: #666;">No verified results yet.</p>';
            } else {
                standingsDiv.innerHTML = data.party_standings.map((p, idx) => `
                    <div style="display: flex; align-items: center; margin-bottom: 0.75rem; padding: 0.5rem; background: ${p.is_preferred ? '#fff9db' : (idx === 0 ? '#f0f9ff' : '#f9fafb')}; border-radius: 6px; border-left: 4px solid ${p.is_preferred ? '#fcc419' : (idx === 0 ? '#3b82f6' : 'transparent')};">
                        <div style="flex: 0 0 80px;">
                            <span style="font-weight: 700; color: #374151;">${p.party}</span>
                            ${p.is_preferred ? '<i class="fas fa-star" style="color: #fcc419; font-size: 0.8rem;"></i>' : ''}
                        </div>
                        <div style="flex: 1;">
                            <div style="font-size: 0.85rem; font-weight: 600; color: #4b5563;">${p.candidate_name}</div>
                            <div style="background: #e5e7eb; border-radius: 4px; height: 8px; margin-top: 4px; overflow: hidden;">
                                <div style="background: ${p.is_preferred ? '#fcc419' : 'var(--primary-red)'}; height: 100%; width: ${p.percentage}%; transition: width 0.5s;"></div>
                            </div>
                        </div>
                        <div style="flex: 0 0 100px; text-align: right;">
                            <div style="font-weight: 700;">${p.votes.toLocaleString()}</div>
                            <div style="font-size: 0.75rem; color: #6b7280;">${p.percentage}%</div>
                        </div>
                    </div>
                `).join('');
            }
        }


        // 4. Update HEAT MAP - Use the mode selector's current value
        currentMapElectionId = electionId;
        const mapModeSelect = document.getElementById('map-mode-select');
        const currentMode = mapModeSelect ? mapModeSelect.value : 'party_leaders';
        loadMapWithMode(electionId, currentMode);


        // 5. Render Leading Sections
        const sectionsDiv = document.getElementById("leading-sections-list");
        if (sectionsDiv && data.leading_sections) {
            sectionsDiv.innerHTML = data.leading_sections.length === 0 ?
                '<p style="color: #666;">No data yet.</p>' :
                data.leading_sections.map(s => `
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; border-bottom: 1px solid #eee;">
                        <span style="font-weight: 500;">${s.lga}</span>
                        <span><strong>${s.leader}</strong> +${s.margin.toLocaleString()}</span>
                    </div>
                `).join('');
        }

        // 6. Render Trailing Sections
        const trailingDiv = document.getElementById("trailing-sections-list");
        if (trailingDiv && data.trailing_sections) {
            trailingDiv.innerHTML = data.trailing_sections.length === 0 ?
                '<p style="color: #666;">No trailing data.</p>' :
                data.trailing_sections.map(s => `
                    <div class="trailing-section-item">
                        <span style="font-weight: 500;">${s.lga}</span>
                        <span style="color: var(--accent-red);"><strong>${s.leader}</strong> (Low Margin)</span>
                    </div>
                `).join('');
        }

        // 7. Update Ballot Audit Chart
        if (data.exhaustive_stats) {
            updateBallotAuditChart(data.exhaustive_stats);
        }

    } catch (error) {
        console.error("Error loading analytics:", error);
    }
}

let ballotAuditChart;
function updateBallotAuditChart(stats) {
    const ctx = document.getElementById('ballot-audit-chart')?.getContext('2d');
    if (!ctx) return;

    const data = {
        labels: ['Valid Votes', 'Rejected', 'Spoilt', 'Unused'],
        datasets: [{
            data: [
                stats.total_valid_votes || 0,
                stats.rejected_ballots || 0,
                stats.spoilt_ballots || 0,
                stats.unused_ballots || 0
            ],
            backgroundColor: [
                '#10b981', // Valid - Green
                '#ef4444', // Rejected - Red
                '#f59e0b', // Spoilt - Orange
                '#94a3b8'  // Unused - Slate
            ],
            borderWidth: 0
        }]
    };

    if (ballotAuditChart) {
        ballotAuditChart.data = data;
        ballotAuditChart.update();
    } else {
        ballotAuditChart = new Chart(ctx, {
            type: 'polarArea',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } }
                },
                scales: {
                    r: { ticks: { display: false } }
                }
            }
        });
    }

    // Update legend/text audit
    const legendDiv = document.getElementById('ballot-audit-legend');
    if (legendDiv) {
        legendDiv.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 1rem;">
                <div style="padding: 0.5rem; background: #f8fafc; border-radius: 4px; border-left: 3px solid #10b981;">
                    <span style="display: block; font-size: 0.7rem; color: #64748b;">Valid</span>
                    <strong>${(stats.total_valid_votes || 0).toLocaleString()}</strong>
                </div>
                <div style="padding: 0.5rem; background: #f8fafc; border-radius: 4px; border-left: 3px solid #94a3b8;">
                    <span style="display: block; font-size: 0.7rem; color: #64748b;">Unused</span>
                    <strong>${(stats.unused_ballots || 0).toLocaleString()}</strong>
                </div>
            </div>
        `;
    }
}

function updatePartyStandingsChart(standings) {
    const ctx = document.getElementById('party-standings-chart')?.getContext('2d');
    if (!ctx) return;

    const labels = standings.map(p => p.party);
    const votes = standings.map(p => p.votes);
    const colors = [
        '#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#6366f1'
    ];

    if (dashboardChart) {
        dashboardChart.data.labels = labels;
        dashboardChart.data.datasets[0].data = votes;
        dashboardChart.update();
    } else {
        dashboardChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: votes,
                    backgroundColor: colors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.label}: ${context.raw.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Global to track current election for map reloads
let currentMapElectionId = null;
let geoJsonLayer = null;
let nigeriaGeoJson = null;
let heatmapLayer = null;

// Party color mapping
const PARTY_COLORS = {
    'APC': '#3b82f6',   // Blue
    'PDP': '#ef4444',   // Red
    'LP': '#10b981',    // Green
    'NNPP': '#f59e0b',  // Orange
    'APGA': '#8b5cf6',  // Purple
    'ADC': '#06b6d4',   // Cyan
    'YPP': '#ec4899'    // Pink
};

function getPartyColor(party) {
    return PARTY_COLORS[party?.toUpperCase()] || '#6366f1';
}

// Load GeoJSON data once
async function loadGeoJsonData() {
    if (nigeriaGeoJson) return nigeriaGeoJson;

    try {
        const response = await fetch('/static/nigeria_lga.geojson');
        nigeriaGeoJson = await response.json();
        console.log(`Loaded ${nigeriaGeoJson.features.length} LGA boundaries`);
        return nigeriaGeoJson;
    } catch (error) {
        console.error("Error loading GeoJSON:", error);
        return null;
    }
}

function updateDashboardMap(mapData) {
    // This is called with analytics data for backward compatibility
    if (mapData && mapData.length > 0) {
        loadGeoJsonData().then(geoData => {
            if (geoData) {
                renderChoroplethMap('party_leaders', {
                    points: mapData.map(p => ({ ...p, total_votes: p.votes, winner: p.leader || p.winner })),
                    preferred_party: 'APC'
                }, geoData);
            }
        });
    }
}

async function loadMapWithMode(electionId, mode) {
    if (!electionId) return;

    currentMapElectionId = electionId;

    try {
        // Load GeoJSON in parallel with data
        const [geoData, response] = await Promise.all([
            loadGeoJsonData(),
            fetch(`/api/election/${electionId}/map-data?mode=${mode}`)
        ]);

        const data = await response.json();
        renderChoroplethMap(mode, data, geoData);
    } catch (error) {
        console.error("Error loading map data:", error);
        showToast("Failed to load map data", "error");
    }
}

function normalizeLocationName(name) {
    if (!name) return '';
    return name.toUpperCase()
        .replace(/[\s\-\/]+/g, '')
        .replace(/[^A-Z0-9]/g, '');
}

function renderChoroplethMap(mode, data, geoData) {
    const mapContainer = document.getElementById('map');
    const legendContainer = document.getElementById('map-legend');
    if (!mapContainer) return;

    // Initialize map if not exists
    if (!dashboardMap) {
        dashboardMap = L.map('map').setView([9.0820, 8.6753], 6); // Center on Nigeria
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap &copy; CARTO',
            maxZoom: 19
        }).addTo(dashboardMap);
    }

    // Clear existing layers
    if (geoJsonLayer) {
        dashboardMap.removeLayer(geoJsonLayer);
        geoJsonLayer = null;
    }
    if (heatmapLayer) {
        dashboardMap.removeLayer(heatmapLayer);
        heatmapLayer = null;
    }
    mapMarkers.forEach(m => dashboardMap.removeLayer(m));
    mapMarkers = [];

    const points = data.points || [];
    const preferredParty = data.preferred_party;

    if (points.length === 0 || !geoData) {
        if (legendContainer) legendContainer.innerHTML = '<span style="color: #666;">No data available for this view.</span>';
        return;
    }

    // Create a lookup map from API data by normalized LGA name
    const dataLookup = {};
    points.forEach(point => {
        const normalizedName = normalizeLocationName(point.name);
        dataLookup[normalizedName] = point;
    });

    // Get state filter based on where we have data
    const statesWithData = new Set();
    points.forEach(p => {
        if (p.state) statesWithData.add(normalizeLocationName(p.state));
    });

    // Style function for GeoJSON features
    function getFeatureStyle(feature) {
        const lgaName = feature.properties.NAME_2;
        const stateName = feature.properties.NAME_1;
        const normalizedLga = normalizeLocationName(lgaName);
        const normalizedState = normalizeLocationName(stateName);

        const point = dataLookup[normalizedLga];

        // Default style for LGAs without data
        let fillColor = '#e5e7eb';
        let fillOpacity = 0.3;
        let weight = 0.5;
        let color = '#9ca3af';

        if (point) {
            fillOpacity = 0.7;
            weight = 2;
            color = '#fff';

            switch (mode) {
                case 'registered_voters':
                    const maxVoters = Math.max(...points.map(p => p.value || 0));
                    const intensity = (point.value || 0) / maxVoters;
                    fillColor = `hsl(${210 - intensity * 60}, 70%, ${60 - intensity * 25}%)`;
                    break;

                case 'winning_sections':
                    fillColor = '#10b981'; // Green
                    break;

                case 'trailing_sections':
                    fillColor = '#ef4444'; // Red
                    break;

                case 'incidents':
                    const sevScore = point.severity_score || 1;
                    fillColor = sevScore >= 6 ? '#dc2626' : sevScore >= 3 ? '#f59e0b' : '#fbbf24';
                    break;

                case 'party_leaders':
                default:
                    fillColor = getPartyColor(point.winner);
                    break;
            }
        }

        return {
            fillColor: fillColor,
            weight: weight,
            opacity: 1,
            color: color,
            fillOpacity: fillOpacity
        };
    }

    // Filter GeoJSON to only show relevant features (with data or in same state as data)
    const filteredFeatures = geoData.features.filter(feature => {
        const lgaName = normalizeLocationName(feature.properties.NAME_2);
        const stateName = normalizeLocationName(feature.properties.NAME_1);

        // Include if we have data for this LGA
        if (dataLookup[lgaName]) return true;

        // Include if it's in a state where we have data (for context)
        if (statesWithData.size > 0) {
            return statesWithData.has(stateName);
        }

        return false;
    });

    const filteredGeoJson = {
        type: 'FeatureCollection',
        features: filteredFeatures
    };

    // Special handling for hotspots mode
    if (mode === 'hotspots') {
        const heatmapPoints = points.map(p => {
            const intensity = (p.severity_score || 1) / 10;
            return [p.lat, p.lng, intensity];
        }).filter(p => p[0] && p[1]);

        if (heatmapPoints.length > 0) {
            heatmapLayer = L.heatLayer(heatmapPoints, {
                radius: 35,
                blur: 20,
                maxZoom: 10,
                gradient: { 0.4: 'blue', 0.6: 'lime', 0.8: 'yellow', 1: 'red' }
            }).addTo(dashboardMap);
        }
    }

    // Create GeoJSON layer
    geoJsonLayer = L.geoJSON(filteredGeoJson, {
        style: getFeatureStyle,
        onEachFeature: function (feature, layer) {
            const lgaName = feature.properties.NAME_2;
            const stateName = feature.properties.NAME_1;
            const normalizedLga = normalizeLocationName(lgaName);
            const point = dataLookup[normalizedLga];

            let popupContent = '';

            if (point) {
                switch (mode) {
                    case 'registered_voters':
                        popupContent = `
                            <div style="font-family: Inter, sans-serif; padding: 8px; min-width: 180px;">
                                <strong style="font-size: 1.1rem; display: block; margin-bottom: 5px;">${lgaName}</strong>
                                <div style="font-size: 0.85rem; color: #666;">${stateName} State</div>
                                <div style="font-size: 1.2rem; font-weight: 700; color: #1e40af; margin-top: 8px;">
                                    📊 ${point.value?.toLocaleString()} Voters
                                </div>
                            </div>`;
                        break;

                    case 'winning_sections':
                        popupContent = `
                            <div style="font-family: Inter, sans-serif; padding: 8px; min-width: 180px;">
                                <strong style="font-size: 1.1rem; color: #059669; display: block; margin-bottom: 5px;">✅ ${lgaName}</strong>
                                <div style="font-size: 0.85rem; color: #666;">${stateName} State</div>
                                <div style="font-size: 0.95rem; margin-top: 8px;">
                                    <strong>${preferredParty}</strong> is <span style="color: #10b981; font-weight: 700;">WINNING</span>
                                </div>
                                <div style="font-size: 0.9rem; margin-top: 5px;">
                                    Margin: <strong>+${point.margin?.toLocaleString()}</strong> votes
                                </div>
                            </div>`;
                        break;

                    case 'trailing_sections':
                        popupContent = `
                            <div style="font-family: Inter, sans-serif; padding: 8px; min-width: 180px;">
                                <strong style="font-size: 1.1rem; color: #dc2626; display: block; margin-bottom: 5px;">⚠️ ${lgaName}</strong>
                                <div style="font-size: 0.85rem; color: #666;">${stateName} State</div>
                                <div style="font-size: 0.95rem; margin-top: 8px;">
                                    <strong>${preferredParty}</strong> is <span style="color: #ef4444; font-weight: 700;">TRAILING</span>
                                </div>
                                <div style="font-size: 0.9rem; margin-top: 5px;">
                                    Behind by: <strong>${Math.abs(point.margin)?.toLocaleString()}</strong> votes
                                </div>
                                <div style="font-size: 0.85rem; margin-top: 3px;">
                                    Leader: <span style="color: ${getPartyColor(point.winner)}; font-weight: 700;">${point.winner}</span>
                                </div>
                            </div>`;
                        break;

                    case 'incidents':
                    case 'hotspots':
                        const incidentList = (point.incidents || []).slice(0, 3).map(i =>
                            `<li style="margin: 3px 0;"><span style="color: ${i.severity === 'critical' ? '#dc2626' : '#f59e0b'};">●</span> ${i.type?.replace(/_/g, ' ')}</li>`
                        ).join('');
                        popupContent = `
                            <div style="font-family: Inter, sans-serif; padding: 8px; min-width: 180px;">
                                <strong style="font-size: 1.1rem; color: #dc2626; display: block; margin-bottom: 5px;">${mode === 'hotspots' ? '🔥 Heatspot' : '🚨 Incident'}: ${point.name}</strong>
                                <div style="font-size: 0.85rem; color: #666; font-weight: 600;">Status: High Hostility</div>
                                <div style="font-size: 1rem; font-weight: 700; margin-top: 8px;">
                                    ${point.incident_count} Malpractice Events
                                </div>
                                <ul style="font-size: 0.85rem; margin: 5px 0 0 0; padding-left: 15px;">${incidentList}</ul>
                            </div>`;
                        break;

                    case 'party_leaders':
                    default:
                        const partyColor = getPartyColor(point.winner);
                        popupContent = `
                            <div style="font-family: Inter, sans-serif; padding: 8px; min-width: 180px;">
                                <strong style="font-size: 1.1rem; display: block; margin-bottom: 5px;">${lgaName}</strong>
                                <div style="font-size: 0.85rem; color: #666; margin-bottom: 8px;">${stateName} State</div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-top: 1px solid #eee;">
                                    <span>Leading:</span>
                                    <span style="font-weight: 700; color: ${partyColor}; font-size: 1.1rem;">${point.winner}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 0;">
                                    <span>Total Votes:</span>
                                    <span style="font-weight: 700;">${(point.total_votes || point.votes)?.toLocaleString()}</span>
                                </div>
                            </div>`;
                        break;
                }
            } else {
                popupContent = `
                    <div style="font-family: Inter, sans-serif; padding: 8px;">
                        <strong style="font-size: 1rem;">${lgaName}</strong>
                        <div style="font-size: 0.85rem; color: #666;">${stateName} State</div>
                        <div style="font-size: 0.85rem; color: #9ca3af; margin-top: 5px;">No data reported</div>
                    </div>`;
            }

            layer.bindPopup(popupContent);

            // Hover effects
            layer.on({
                mouseover: function (e) {
                    const layer = e.target;
                    layer.setStyle({
                        weight: 3,
                        color: '#1e293b',
                        fillOpacity: 0.85
                    });
                    layer.bringToFront();
                },
                mouseout: function (e) {
                    geoJsonLayer.resetStyle(e.target);
                }
            });
        }
    }).addTo(dashboardMap);

    // Fit map to GeoJSON bounds
    if (filteredFeatures.length > 0) {
        dashboardMap.fitBounds(geoJsonLayer.getBounds(), { padding: [20, 20] });
    }

    // Add numeric labels for registered voters
    if (mode === 'registered_voters') {
        points.forEach(point => {
            if (point.lat && point.lng && point.value > 0) {
                const labelIcon = L.divIcon({
                    className: 'map-voter-label',
                    html: `<div>${(point.value / 1000).toFixed(0)}k</div>`,
                    iconSize: [40, 20],
                    iconAnchor: [20, 10]
                });
                const marker = L.marker([point.lat, point.lng], { icon: labelIcon, interactive: false })
                    .addTo(dashboardMap);
                mapMarkers.push(marker);
            }
        });
    }

    // Update legend
    if (legendContainer) {
        renderMapLegend(legendContainer, mode, data);
    }
}

function renderMapLegend(container, mode, data) {
    let legendHtml = '';
    const preferredParty = data.preferred_party;

    switch (mode) {
        case 'registered_voters':
            legendHtml = `
                <span><span style="display: inline-block; width: 12px; height: 12px; background: hsl(210, 70%, 60%); border-radius: 50%; margin-right: 5px;"></span> Low Density</span>
                <span><span style="display: inline-block; width: 12px; height: 12px; background: hsl(180, 70%, 50%); border-radius: 50%; margin-right: 5px;"></span> Medium Density</span>
                <span><span style="display: inline-block; width: 12px; height: 12px; background: hsl(150, 70%, 40%); border-radius: 50%; margin-right: 5px;"></span> High Density</span>
            `;
            break;
        case 'winning_sections':
            legendHtml = `
                <span><span style="display: inline-block; width: 12px; height: 12px; background: #10b981; border-radius: 50%; margin-right: 5px;"></span> ${preferredParty || 'Our Candidate'} Leading</span>
                <span style="color: #666;">Showing ${data.points?.length || 0} winning LGAs</span>
            `;
            break;
        case 'trailing_sections':
            legendHtml = `
                <span><span style="display: inline-block; width: 12px; height: 12px; background: #ef4444; border-radius: 50%; margin-right: 5px;"></span> ${preferredParty || 'Our Candidate'} Trailing</span>
                <span style="color: #666;">Showing ${data.points?.length || 0} trailing LGAs</span>
            `;
            break;
        case 'incidents':
            legendHtml = `
                <span><span style="display: inline-block; width: 12px; height: 12px; background: #dc2626; border-radius: 50%; margin-right: 5px;"></span> Critical Marker</span>
                <span><span style="display: inline-block; width: 12px; height: 12px; background: #f59e0b; border-radius: 50%; margin-right: 5px;"></span> Warning Marker</span>
                <span style="color: #666;">${data.points?.length || 0} locations</span>
            `;
            break;
        case 'hotspots':
            legendHtml = `
                <span style="display: flex; align-items: center; gap: 5px;">
                    <span style="width: 50px; height: 12px; background: linear-gradient(to right, blue, lime, yellow, red); border-radius: 6px;"></span>
                    <span>Density (Low → High)</span>
                </span>
                <span style="color: #666;"><i class="fas fa-fire-alt"></i> Tactical Disruption Heatmap</span>
            `;
            break;
        case 'party_leaders':
        default:
            const partyLegend = Object.entries(PARTY_COLORS).slice(0, 5).map(([party, color]) =>
                `<span><span style="display: inline-block; width: 12px; height: 12px; background: ${color}; border-radius: 50%; margin-right: 5px;"></span> ${party}</span>`
            ).join('');
            legendHtml = partyLegend;
            break;
    }

    container.innerHTML = legendHtml;
}

// Setup map mode dropdown listener
document.addEventListener('DOMContentLoaded', () => {
    const mapModeSelect = document.getElementById('map-mode-select');
    if (mapModeSelect) {
        mapModeSelect.addEventListener('change', () => {
            const mode = mapModeSelect.value;
            if (currentMapElectionId) {
                loadMapWithMode(currentMapElectionId, mode);
            }
        });
    }
});



async function loadResultsData() {
    const resSelect = document.getElementById("results-election-select");
    const dashSelect = document.getElementById("dashboard-election-select");

    let electionId = resSelect?.value || dashSelect?.value;

    // If we're entering the tab for the first time and only dashSelect has a value, sync it
    if (resSelect && !resSelect.value && dashSelect && dashSelect.value) {
        resSelect.value = dashSelect.value;
        electionId = resSelect.value;
    }

    if (!electionId) return;

    const breakdownDiv = document.getElementById("results-lga-breakdown");
    const legalDiv = document.getElementById("results-legal-analysis");
    const summaryBar = document.getElementById("results-stats-summary");
    const emptyState = document.getElementById("results-empty-state");
    const totalVotesSpan = document.getElementById("results-total-votes");
    const turnoutPctSpan = document.getElementById("results-turnout-pct");

    try {
        // 1. Fetch High-level Analytics
        const analyticsRes = await fetch(`/api/election/${electionId}/analytics`);
        const stats = await analyticsRes.json();

        if (stats) {
            if (emptyState) emptyState.style.display = 'none';
            if (summaryBar) summaryBar.style.display = 'grid'; // Use grid for the new layout

            if (totalVotesSpan) totalVotesSpan.textContent = stats.total_votes_cast?.toLocaleString() || 0;
            if (turnoutPctSpan) turnoutPctSpan.textContent = `${stats.percentage_voted || 0}%`;

            const accreditedSpan = document.getElementById("results-accredited-votes");
            if (accreditedSpan) accreditedSpan.textContent = stats.accredited_voters?.toLocaleString() || 0;

            // Populate Compliance Audit Section
            const complianceDiv = document.getElementById("results-compliance-audit");
            if (complianceDiv && stats.exhaustive_stats) {
                complianceDiv.style.display = 'block';
                const ex = stats.exhaustive_stats;
                document.getElementById("audit-registered").textContent = ex.voters_on_register.toLocaleString();
                document.getElementById("audit-accredited").textContent = ex.accredited_voters.toLocaleString();
                document.getElementById("audit-issued").textContent = ex.ballots_issued.toLocaleString();
                document.getElementById("audit-unused").textContent = ex.unused_ballots.toLocaleString();
                document.getElementById("audit-spoilt").textContent = ex.spoilt_ballots.toLocaleString();
                document.getElementById("audit-rejected").textContent = ex.rejected_ballots.toLocaleString();
                document.getElementById("audit-valid").textContent = ex.total_valid_votes.toLocaleString();
            }
        }

        // 2. Render Party Standings
        const partyStandingsDiv = document.getElementById("results-party-standings");
        if (partyStandingsDiv && stats.party_standings) {
            if (stats.party_standings.length === 0) {
                partyStandingsDiv.innerHTML = '<p style="color:#666; font-style:italic;">No verified results yet.</p>';
            } else {
                partyStandingsDiv.innerHTML = `
                    <table class="premium-table">
                        <thead>
                            <tr>
                                <th>Party</th>
                                <th>Candidate</th>
                                <th>Total Votes</th>
                                <th>Percentage</th>
                                <th style="width: 250px;">Visual</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stats.party_standings.map((p, idx) => `
                                <tr style="${idx === 0 ? 'background: #fdf2f2; border-left: 4px solid var(--primary-red);' : ''}">
                                    <td>
                                        <span class="badge-party party-${p.party.toLowerCase()}">${p.party}</span>
                                        ${idx === 0 ? ' <i class="fas fa-trophy" style="color:#fbbf24; margin-left:5px;"></i>' : ''}
                                    </td>
                                    <td style="font-weight:600;">${p.candidate_name}</td>
                                    <td style="font-weight:700;">${p.votes.toLocaleString()}</td>
                                    <td>${p.percentage}%</td>
                                    <td>
                                        <div style="height:8px; background:#e2e8f0; border-radius:10px; overflow:hidden;">
                                            <div style="width:${p.percentage}%; height:100%; background:${idx === 0 ? 'var(--primary-red)' : '#475569'}; transition:width 1s;"></div>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }
        }

        // 3. Fetch LGA Breakdown
        const response = await fetch(`/api/election/${electionId}/lga-breakdown`);
        const lgas = await response.json();

        if (breakdownDiv) {
            if (lgas.length === 0) {
                breakdownDiv.innerHTML = '<p style="color:#666; font-style:italic;">No verified LGA results yet.</p>';
            } else {
                breakdownDiv.innerHTML = `
                    <table class="premium-table">
                        <thead>
                            <tr>
                                <th>LGA</th>
                                <th>Reported PUs</th>
                                <th>Total Votes</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${lgas.map(lga => `
                                <tr>
                                    <td style="font-weight:600;">${lga.name}</td>
                                    <td>${lga.reporting_pus}</td>
                                    <td>${lga.total_votes.toLocaleString()}</td>
                                    <td><span class="badge" style="background:#f1f5f9; color:#475569;">Verified</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }
        }

        // 2. Fetch Legal Analysis Summary
        const legalRes = await fetch(`/api/legal-analysis/${electionId}`);
        const legalData = await legalRes.json();

        if (legalDiv) {
            if (legalData.loophole_count === 0) {
                legalDiv.innerHTML = `
                    <div style="padding:1rem; background:#ecfdf5; color:#065f46; border-radius:8px; display:flex; align-items:center; gap:0.75rem;">
                        <i class="fas fa-check-circle"></i>
                        <span>No major compliance issues detected in captured data.</span>
                    </div>
                `;
            } else {
                legalDiv.innerHTML = `
                    <div style="display:flex; flex-direction:column; gap:0.5rem;">
                        ${legalData.loopholes.slice(0, 5).map(l => `
                            <div style="padding:0.75rem; background:#fff7ed; border-left:3px solid #f97316; border-radius:4px;">
                                <div style="font-weight:600; font-size:0.85rem; color:#9a3412;">${l.type} - ${l.severity}</div>
                                <div style="font-size:0.8rem; color:#444;">${l.location}: ${l.details}</div>
                            </div>
                        `).join('')}
                        ${legalData.loophole_count > 5 ? `<p style="font-size:0.75rem; color:#666; text-align:center;">+ ${legalData.loophole_count - 5} more anomalies detected.</p>` : ''}
                    </div>
                `;
            }
        }

    } catch (e) {
        console.error("Error loading results detail:", e);
    }

    // Wire up Export Buttons if they exist
    const pdfBtn = document.getElementById('export-pdf-btn');
    const csvBtn = document.getElementById('export-csv-btn');

    if (pdfBtn) pdfBtn.dataset.electionId = electionId;
    if (csvBtn) csvBtn.dataset.electionId = electionId;
}

async function loadElectionStats(electionId) {
    // Deprecated - use loadElectionAnalytics instead
    loadElectionAnalytics(electionId);
}

// ===== FIELD DEPENDENCIES =====
// ===== FIELD DEPENDENCIES (UNIFIED) =====
// ===== FIELD DEPENDENCIES (UNIFIED) =====
function setupFormDependencies() {
    // 1. Unified Election Selection Logic
    document.addEventListener("change", async (e) => {
        if (e.target.id === "election-select" || e.target.id === "dashboard-election-select") {
            const electionId = e.target.value;
            const form = e.target.closest("form") || document;

            if (!electionId) return;

            try {
                // Fetch election details to get scope
                const election = await safeFetch(`/api/election/${electionId}`);
                console.log("Enforcing election scope:", election.election_scope, election.state_id, election.lga_id);

                const stateSelect = form.querySelector("#state-select, #inc-state-select, .state-select-common");
                const lgaSelect = form.querySelector("#lga-select, #inc-lga-select, .lga-select-common");

                if (election.state_id && stateSelect) {
                    stateSelect.value = election.state_id;
                    // Trigger manual change to load LGAs
                    stateSelect.dispatchEvent(new Event('change', { bubbles: true }));

                    // Optional: Lock state if it's fixed scope
                    if (election.election_scope === 'state' || election.election_scope === 'lga') {
                        stateSelect.setAttribute('disabled', 'true');
                        // Ensure it's submitted by adding a hidden field if disabled
                        if (!form.querySelector('input[name="state_id_hidden"]')) {
                            const hidden = document.createElement('input');
                            hidden.type = 'hidden';
                            hidden.name = 'state_id';
                            hidden.id = 'state_id_hidden';
                            hidden.value = election.state_id;
                            form.appendChild(hidden);
                        }
                    } else {
                        stateSelect.removeAttribute('disabled');
                    }
                } else if (stateSelect) {
                    stateSelect.removeAttribute('disabled');
                }

                // Wait a bit for LGAs to load then set LGA if scoped
                if (election.lga_id && lgaSelect) {
                    let attempts = 0;
                    const interval = setInterval(() => {
                        if (lgaSelect.options.length > 1 || attempts > 10) {
                            clearInterval(interval);
                            lgaSelect.value = election.lga_id;
                            lgaSelect.dispatchEvent(new Event('change', { bubbles: true }));

                            if (election.election_scope === 'lga') {
                                lgaSelect.setAttribute('disabled', 'true');
                            } else {
                                lgaSelect.removeAttribute('disabled');
                            }
                        }
                        attempts++;
                    }, 200);
                } else if (lgaSelect) {
                    lgaSelect.removeAttribute('disabled');
                }

            } catch (err) {
                console.error("Failed to enforce election scope:", err);
            }
        }
    });

    // 2. Location Hierarchy Logic
    document.addEventListener("change", async (e) => {
        const form = e.target.closest("form") || document;

        // State changed -> Populate LGAs
        if (e.target.classList.contains("state-select-common") || e.target.id === "state-select" || e.target.id === "admin-election-state-select") {
            const stateId = e.target.value;
            const lgaSelect = form.querySelector("#lga-select, #admin-election-lga-select, #inc-lga-select, .lga-select-common");
            const wardSelect = form.querySelector("#ward-select, #inc-ward-select, .ward-select-common");
            const puSelect = form.querySelector("#pu-code, #inc-pu-select, .pu-select-common");

            if (lgaSelect) {
                lgaSelect.innerHTML = "<option value=\"\">Loading LGAs...</option>";
                if (wardSelect) wardSelect.innerHTML = "<option value=\"\">Select Ward</option>";
                if (puSelect) puSelect.innerHTML = "<option value=\"\">Select Polling Unit</option>";

                if (!stateId) {
                    lgaSelect.innerHTML = "<option value=\"\">Select LGA</option>";
                    return;
                }

                try {
                    const response = await fetch(`/api/state/${stateId}/lgas`);
                    const lgas = await response.json();
                    lgaSelect.innerHTML = "<option value=\"\">Select LGA</option>";
                    lgas.forEach(lga => {
                        const option = document.createElement("option");
                        option.value = lga.id;
                        option.textContent = lga.name;
                        lgaSelect.appendChild(option);
                    });
                } catch (error) {
                    console.error("Error loading LGAs:", error);
                }
            }
        }

        // LGA changed -> Populate Wards
        if (e.target.classList.contains("lga-select-common") || e.target.id === "lga-select" || e.target.id === "inc-lga-select") {
            const lgaId = e.target.value;
            const wardSelect = form.querySelector("#ward-select, #inc-ward-select, .ward-select-common");
            const puSelect = form.querySelector("#pu-code, #inc-pu-select, .pu-select-common");

            if (wardSelect) {
                wardSelect.innerHTML = "<option value=\"\">Loading Wards...</option>";
                if (puSelect) puSelect.innerHTML = "<option value=\"\">Select Polling Unit</option>";

                if (!lgaId) {
                    wardSelect.innerHTML = "<option value=\"\">Select Ward</option>";
                    return;
                }

                try {
                    const response = await fetch(`/api/lga/${lgaId}/wards`);
                    const wards = await response.json();
                    wardSelect.innerHTML = "<option value=\"\">Select Ward</option>";
                    wards.forEach(ward => {
                        const option = document.createElement("option");
                        option.value = ward.id;
                        option.textContent = ward.name;
                        wardSelect.appendChild(option);
                    });
                } catch (error) {
                    console.error("Error loading Wards:", error);
                }
            }
        }

        // Ward changed -> Populate PUs
        if (e.target.classList.contains("ward-select-common") || e.target.id === "ward-select" || e.target.id === "inc-ward-select") {
            const wardId = e.target.value;
            const puSelect = form.querySelector("#pu-code, #inc-pu-select, .pu-select-common");

            if (puSelect) {
                puSelect.innerHTML = "<option value=\"\">Loading PUs...</option>";

                if (!wardId) {
                    puSelect.innerHTML = "<option value=\"\">Select Polling Unit</option>";
                    return;
                }

                try {
                    const response = await fetch(`/api/ward/${wardId}/polling-units`);
                    const pus = await response.json();
                    puSelect.innerHTML = "<option value=\"\">Select Polling Unit</option>";
                    pus.forEach(pu => {
                        const option = document.createElement("option");
                        // Results form (pu-code) expects the string code, Incident form (inc-pu-select) expects the integer ID
                        option.value = (puSelect.id === "pu-code") ? pu.pu_code : pu.id;
                        option.textContent = `${pu.name} (${pu.pu_code})`;
                        puSelect.appendChild(option);
                    });
                } catch (error) {
                    console.error("Error loading PUs:", error);
                }
            }
        }
    });
}

// Export functions for explicit calls
window.loadUploadTabDependencies = loadUploadTabDependencies;
window.setupFormDependencies = setupFormDependencies;
window.addPartyInput = addPartyInput;
window.loadAdminTabData = loadAdminTabData;
window.loadStates = loadStates;

// ===== INITIALIZATION =====
document.addEventListener("DOMContentLoaded", () => {
    // 1. Tab-based initialization (Legacy/Dashboard support)
    if (document.querySelector('.nav-tab[data-tab]')) {
        switchTab("monitor");
    }

    // 2. Setup dependency logic
    setupFormDependencies();

    // 3. Setup Live OCR Preview Listener
    const ocrEditor = document.getElementById('ocr-markdown-editor');
    const accreditedVotersInput = document.getElementById('accredited-voters-input');

    if (ocrEditor) ocrEditor.addEventListener('input', window.updateLivePreview);
    if (accreditedVotersInput) accreditedVotersInput.addEventListener('input', window.updateLivePreview);

    const uploadForm = document.getElementById('result-upload-form');
    if (uploadForm) uploadForm.addEventListener('submit', window.handleResultUpload);
});

// Helper
function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

// ===== ADMIN PANEL LOGIC =====
document.addEventListener("DOMContentLoaded", () => {
    const adminTabs = document.querySelectorAll('.admin-tab');
    if (adminTabs.length > 0) {
        // Load data for the initially active tab
        const activeTab = document.querySelector('.admin-tab.active');
        if (activeTab) {
            loadAdminTabData(activeTab.dataset.tab);
        }

        // Add event listeners for tab switching
        adminTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                loadAdminTabData(tab.dataset.tab);
            });
        });

        // Add form submission listeners
        const userForm = document.getElementById('user-form');
        if (userForm) {
            userForm.addEventListener('submit', handleAdminFormSubmit);
        }
        const lgaForm = document.getElementById('lga-form');
        if (lgaForm) {
            lgaForm.addEventListener('submit', handleAdminFormSubmit);
        }
        const puForm = document.getElementById('pu-form');
        if (puForm) {
            puForm.addEventListener('submit', handleAdminFormSubmit);
        }
        const electionForm = document.getElementById('election-form');
        if (electionForm) {
            electionForm.addEventListener('submit', handleAdminFormSubmit);
        }
        const candidateForm = document.getElementById('candidate-form');
        if (candidateForm) {
            candidateForm.addEventListener('submit', handleAdminFormSubmit);
        }
    }
    setupAdminElectionFormDependencies();
});

function setupAdminElectionFormDependencies() {
    const scopeSelect = document.getElementById('admin-election-scope-select');
    const locationContainer = document.getElementById('admin-location-container');
    const stateSelect = document.getElementById('admin-election-state-select');
    const lgaSelect = document.getElementById('admin-election-lga-select');

    if (scopeSelect && locationContainer && stateSelect && lgaSelect) {

        // Handle Scope Change
        scopeSelect.addEventListener('change', () => {
            const scope = scopeSelect.value;
            console.log("Scope changed to:", scope);

            if (scope === 'national') {
                locationContainer.style.display = 'none';
                stateSelect.value = "";
                lgaSelect.value = "";
            } else {
                locationContainer.style.display = 'grid';
                if (scope === 'state') {
                    lgaSelect.style.display = 'none';
                    lgaSelect.value = "";
                } else if (scope === 'lga') {
                    lgaSelect.style.display = 'block';
                }

                // If scope is visible but states are empty, trigger a reload
                if (stateSelect.options.length <= 1) {
                    loadStates();
                }
            }
        });

        // Add a helper to trigger UI update manually
        window.updateAdminElectionScopeUI = () => {
            scopeSelect.dispatchEvent(new Event('change'));
        };

        // Handle Admin State Change for LGA population
        stateSelect.addEventListener('change', async () => {
            const stateId = stateSelect.value;
            lgaSelect.innerHTML = '<option value="">Loading LGAs...</option>';

            if (!stateId) {
                lgaSelect.innerHTML = '<option value="">Select LGA</option>';
                return;
            }

            try {
                const response = await fetch(`/api/state/${stateId}/lgas`);
                if (!response.ok) throw new Error('LGAs API failed');
                const lgas = await response.json();

                lgaSelect.innerHTML = '<option value="">Select LGA</option>';
                lgas.forEach(lga => {
                    const option = document.createElement("option");
                    option.value = lga.id;
                    option.textContent = lga.name;
                    lgaSelect.appendChild(option);
                });
                console.log(`Loaded ${lgas.length} LGAs for state ${stateId}`);
            } catch (error) {
                console.error("Error loading admin LGAs:", error);
                lgaSelect.innerHTML = '<option value="">Error loading LGAs</option>';
            }
        });
    }
}

async function loadAdminPanelData() {
    // This function is called when the main 'Admin' tab is activated.
    // It should ensure the correct admin sub-tab is displayed and its data loaded.
    const adminTabContent = document.getElementById('admin-tab');
    if (adminTabContent) {
        const activeAdminSubTabButton = adminTabContent.querySelector('.admin-tab.active');
        if (activeAdminSubTabButton) {
            const subTabName = activeAdminSubTabButton.dataset.tab;
            await loadAdminTabData(subTabName);
        }
    }
}

async function loadAdminTabData(tabName) {
    // Hide all admin-sections
    document.querySelectorAll('.admin-section').forEach(section => {
        section.style.display = 'none';
    });
    // Show the active admin-section
    const activeSection = document.getElementById(`${tabName}-tab`);
    if (activeSection) {
        activeSection.style.display = 'block';
    }

    switch (tabName) {
        case 'elections':
            await loadAdminElections();
            break;
        case 'candidates':
            await loadElections(true); // Always force fresh elections for admin linking
            const adminCandSelect = document.getElementById('admin-candidate-election-select');
            const adminPartySelect = document.getElementById('admin-candidate-party-select');

            if (adminCandSelect) {
                adminCandSelect.innerHTML = '<option value="">Select Election</option>';
                window.cachedElections.forEach(e => {
                    const opt = document.createElement('option');
                    opt.value = e.id;
                    opt.textContent = `${e.name} (${e.phase})`;
                    adminCandSelect.appendChild(opt);
                });
            }

            if (adminPartySelect) {
                try {
                    const parties = await safeFetch('/api/admin/parties');
                    adminPartySelect.innerHTML = '<option value="">Select Party</option>';
                    parties.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p.abbreviation;
                        opt.textContent = `${p.abbreviation} - ${p.name}`;
                        adminPartySelect.appendChild(opt);
                    });
                } catch (e) {
                    console.error("Failed to load parties for candidate form", e);
                }
            }
            await loadAdminCandidates();
            break;
        case 'users':
            await loadAdminUsers();
            break;
        case 'lgas':
            await loadAdminLgasAndPus();
            break;
        case 'parties':
            await loadAdminParties();
            break;
        // Add cases for other admin tabs here
    }
}

// Helper to show/hide loading state for admin sections
function showAdminLoading(elementId, show) {
    const element = document.getElementById(elementId);
    if (element) {
        if (show) {
            element.innerHTML = '<p class="loading-message" style="text-align: center; color: #888;">Loading...</p>';
        } else {
            // Only remove if it's our loading message
            const loadingMessage = element.querySelector('.loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }
        }
    }
}

async function loadAdminUsers() {
    const userListDiv = document.getElementById('user-list');
    showAdminLoading('user-list', true); // Show loading

    try {
        const response = await fetch('/api/admin/users');
        if (!response.ok) throw new Error('Failed to fetch users');
        const users = await response.json();

        if (userListDiv) {
            userListDiv.innerHTML = `
                <h4>Users</h4>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Full Name</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${users.map(user => `
                            <tr>
                                <td>${user.id}</td>
                                <td>${user.full_name}</td>
                                <td>${user.email}</td>
                                <td>${user.role}</td>
                                <td>
                                    <button class="btn btn-sm" onclick="editUser(${user.id})">Edit</button>
                                    <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id})">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Error loading users:', error);
        if (userListDiv) userListDiv.innerHTML = '<p class="error">Failed to load users.</p>';
    } finally {
        showAdminLoading('user-list', false); // Hide loading
    }
}

async function loadAdminElections() {
    await loadStates(); // Ensure state dropdowns are populated
    const electionListDiv = document.getElementById('election-list');
    showAdminLoading('election-list', true); // Show loading

    try {
        const response = await fetch('/api/admin/elections');
        if (!response.ok) throw new Error('Failed to fetch elections');
        const elections = await response.json();

        // Helper to generate phase badge with appropriate color
        const getPhaseBadge = (phase) => {
            const label = phase.charAt(0).toUpperCase() + phase.slice(1);
            return `<span class="badge badge-${phase}">${label}</span>`;
        };

        // Helper to generate status action buttons based on current phase
        const getStatusActions = (election) => {
            if (election.phase === 'preparation') {
                return `<button class="btn btn-sm btn-success" onclick="activateElection(${election.id})" title="Activate Election">
                    <i class="fas fa-play"></i> Activate
                </button>`;
            } else if (election.phase === 'active') {
                return `<button class="btn btn-sm btn-warning" onclick="completeElection(${election.id})" title="Mark as Completed">
                    <i class="fas fa-check"></i> Complete
                </button>`;
            } else {
                return `<button class="btn btn-sm" onclick="reopenElection(${election.id})" title="Reopen Election">
                    <i class="fas fa-redo"></i> Reopen
                </button>`;
            }
        };

        if (electionListDiv) {
            electionListDiv.innerHTML = `
                <h4>Elections</h4>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Phase</th>
                            <th>Start Date</th>
                            <th>End Date</th>
                            <th>Validation Scope</th>
                            <th>Status Actions</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${elections.map(election => `
                            <tr>
                                <td>${election.id}</td>
                                <td>${election.name}</td>
                                <td>${getPhaseBadge(election.phase)}</td>
                                <td>${election.start_date ? new Date(election.start_date).toLocaleDateString() : 'N/A'}</td>
                                <td>${election.end_date ? new Date(election.end_date).toLocaleDateString() : 'N/A'}</td>
                                <td><span class="badge" style="background:#f1f5f9; color:#475569;">${election.scope || 'National'}</span></td>
                                <td>${getStatusActions(election)}</td>
                                <td>
                                    <button class="btn btn-sm" onclick="editElection(${election.id})">Edit</button>
                                    <button class="btn btn-sm btn-danger" onclick="deleteElection(${election.id})">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Error loading elections:', error);
        if (electionListDiv) electionListDiv.innerHTML = '<p class="error">Failed to load elections.</p>';
    } finally {
        showAdminLoading('election-list', false); // Hide loading
    }
}

async function loadAdminCandidates() {
    const candidateListDiv = document.getElementById('candidate-list');
    showAdminLoading('candidate-list', true); // Show loading

    try {
        const response = await fetch('/api/admin/candidates');
        if (!response.ok) throw new Error('Failed to fetch candidates');
        const candidates = await response.json();

        if (candidateListDiv) {
            // Group candidates by election
            const grouped = candidates.reduce((acc, c) => {
                const key = c.election_name || 'Unassigned';
                if (!acc[key]) acc[key] = [];
                acc[key].push(c);
                return acc;
            }, {});

            let html = '<h4>Candidates by Election</h4>';

            for (const [electionName, electionCandidates] of Object.entries(grouped)) {
                html += `
                    <div class="election-group" style="margin-top: 1.5rem;">
                        <h5 style="background: #f1f5f9; padding: 0.5rem; border-left: 4px solid var(--primary-red); margin-bottom: 0;">${electionName}</h5>
                        <table style="margin-top: 0;">
                            <thead>
                                <tr>
                                    <th style="width: 50px;">ID</th>
                                    <th>Candidate Name</th>
                                    <th style="width: 120px;">Party</th>
                                    <th style="width: 100px;">Priority</th>
                                    <th style="width: 150px;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${electionCandidates.sort((a, b) => b.priority - a.priority).map(candidate => {
                    const partyClass = `party-${candidate.party.toLowerCase()}`;
                    return `
                                    <tr class="${candidate.is_preferred ? 'preferred-row' : ''}" style="${candidate.is_preferred ? 'background-color: #fff9db;' : ''}">
                                        <td>${candidate.id}</td>
                                        <td style="font-weight: 600;">
                                            ${candidate.full_name} 
                                            ${candidate.is_preferred ? '<i class="fas fa-star" style="color: #fcc419;" title="Preferred"></i>' : ''}
                                        </td>
                                        <td><span class="badge-party ${partyClass}">${candidate.party}</span></td>
                                        <td>${candidate.priority}</td>
                                        <td>
                                            <button class="btn btn-sm" onclick="editCandidate(${candidate.id})">Edit</button>
                                            <button class="btn btn-sm btn-danger" onclick="deleteCandidate(${candidate.id})">Delete</button>
                                        </td>
                                    </tr>
                                    `;
                }).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }
            candidateListDiv.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading candidates:', error);
        if (candidateListDiv) candidateListDiv.innerHTML = '<p class="error">Failed to load candidates.</p>';
    } finally {
        showAdminLoading('candidate-list', false); // Hide loading
    }
}

async function loadAdminLgasAndPus() {
    const lgaListDiv = document.getElementById('lga-list');
    const puListDiv = document.getElementById('pu-list');

    showAdminLoading('lga-list', true); // Show loading for LGAs
    showAdminLoading('pu-list', true); // Show loading for Polling Units

    try {
        // Load LGAs
        const lgaResponse = await fetch('/api/admin/lgas');
        if (!lgaResponse.ok) throw new Error('Failed to fetch LGAs');
        const lgas = await lgaResponse.json();

        if (lgaListDiv) {
            lgaListDiv.innerHTML = `
                <h4>LGAs</h4>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>State ID</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${lgas.map(lga => `
                            <tr>
                                <td>${lga.id}</td>
                                <td>${lga.name}</td>
                                <td>${lga.state_id}</td>
                                <td>
                                    <button class="btn btn-sm" onclick="editLga(${lga.id})">Edit</button>
                                    <button class="btn btn-sm btn-danger" onclick="deleteLga(${lga.id})">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Error loading LGAs:', error);
        if (lgaListDiv) lgaListDiv.innerHTML = '<p class="error">Failed to load LGAs.</p>';
    } finally {
        showAdminLoading('lga-list', false); // Hide loading for LGAs
    }

    try {
        // Load Polling Units
        const puResponse = await fetch('/api/admin/polling-units');
        if (!puResponse.ok) throw new Error('Failed to fetch Polling Units');
        const pus = await puResponse.json();

        if (puListDiv) {
            puListDiv.innerHTML = `
                <h4 style="margin-top: 2rem;">Polling Units</h4>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>PU Code</th>
                            <th>LGA ID</th>
                            <th>Registered Voters</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${pus.map(pu => `
                            <tr>
                                <td>${pu.id}</td>
                                <td>${pu.name}</td>
                                <td>${pu.pu_code}</td>
                                <td>${pu.lga_id}</td>
                                <td>${pu.registered_voters}</td>
                                <td>
                                    <button class="btn btn-sm" onclick="editPu(${pu.id})">Edit</button>
                                    <button class="btn btn-sm btn-danger" onclick="deletePu(${pu.id})">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
    } catch (error) {
        console.error('Error loading LGAs/PUs:', error);
        if (puListDiv) puListDiv.innerHTML = '<p class="error">Failed to load Polling Units.</p>';
    } finally {
        showAdminLoading('pu-list', false); // Hide loading for Polling Units
    }
}

// Helper to clear error states from a form
function clearFormErrors(form) {
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    form.querySelectorAll('.error-message').forEach(el => el.remove());
}

// Helper to show field error
function showFieldError(input, message) {
    input.classList.add('error');
    const msg = document.createElement('div');
    msg.className = 'error-message';
    msg.textContent = message;
    input.parentNode.appendChild(msg);
}

async function handleAdminFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    clearFormErrors(form);

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Basic Validation
    let hasError = false;
    form.querySelectorAll('[required]').forEach(input => {
        if (!input.value.trim()) {
            showFieldError(input, 'This field is required');
            hasError = true;
        }
    });

    if (hasError) {
        showToast('Please fix the errors in the form', 'error');
        return;
    }

    const endpoint = form.id === 'user-form' ? '/api/admin/users' :
        form.id === 'lga-form' ? '/api/admin/lgas' :
            form.id === 'pu-form' ? '/api/admin/polling-units' :
                form.id === 'election-form' ? '/api/admin/elections' :
                    form.id === 'candidate-form' ? '/api/admin/candidates' :
                        '';

    if (!endpoint) return;

    // A simple password field for user creation
    if (form.id === 'user-form') {
        data.password = 'password';
    }

    // Handle is_preferred checkbox for candidates
    if (form.id === 'candidate-form') {
        data.is_preferred = form.querySelector('[name="is_preferred"]').checked;
    }

    try {
        const loadingBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = loadingBtn.innerHTML;
        loadingBtn.disabled = true;
        loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showToast('Item created successfully!', 'success');
            form.reset();
            const activeTab = document.querySelector('.admin-tab.active');
            if (activeTab) {
                loadAdminTabData(activeTab.dataset.tab);
            }
        } else {
            const result = await response.json();
            showToast(result.error || 'Failed to create item.', 'error');

            // If there's a specific field error from backend (if we implemented it)
            if (result.field) {
                const input = form.querySelector(`[name="${result.field}"]`);
                if (input) showFieldError(input, result.error);
            }
        }
        loadingBtn.disabled = false;
        loadingBtn.innerHTML = originalBtnText;
    } catch (error) {
        console.error('Form submission error:', error);
        showToast('A network error occurred.', 'error');
        const loadingBtn = form.querySelector('button[type="submit"]');
        if (loadingBtn) loadingBtn.disabled = false;
    }
}

// Placeholder functions for edit/delete
window.editUser = async function (id) {
    try {
        const user = await safeFetch(`/api/admin/users/${id}`);
        const full_name = prompt("Enter new Full Name:", user.full_name);
        if (full_name === null) return;
        const role = prompt("Enter role (admin, agent, monitor):", user.role);

        await safeFetch(`/api/admin/users/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name, role })
        });
        showToast('User updated successfully.', 'success');
        loadAdminUsers();
    } catch (e) { }
}

window.deleteUser = async function (id) {
    if (confirm(`Are you sure you want to delete user ${id}?`)) {
        try {
            await safeFetch(`/api/admin/users/${id}`, { method: 'DELETE' });
            showToast('User deleted successfully.', 'success');
            loadAdminUsers();
        } catch (e) { }
    }
}

window.editLga = async function (id) {
    try {
        const lga = await safeFetch(`/api/admin/lgas/${id}`);
        const name = prompt("Enter new LGA Name:", lga.name);
        if (name === null) return;
        const state_id = prompt("Enter State ID:", lga.state_id);

        await safeFetch(`/api/admin/lgas/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, state_id })
        });
        showToast('LGA updated successfully.', 'success');
        loadAdminLgasAndPus();
    } catch (e) { }
}

window.deleteLga = async function (id) {
    if (confirm(`Are you sure you want to delete LGA ${id}?`)) {
        try {
            await safeFetch(`/api/admin/lgas/${id}`, { method: 'DELETE' });
            showToast('LGA deleted successfully.', 'success');
            loadAdminLgasAndPus();
        } catch (e) { }
    }
}

window.editPu = async function (id) {
    try {
        const pu = await safeFetch(`/api/admin/polling-units/${id}`);
        const name = prompt("Enter new Polling Unit Name:", pu.name);
        if (name === null) return;
        const pu_code = prompt("Enter Polling Unit Code:", pu.pu_code);
        const registered_voters = prompt("Enter Registered Voters:", pu.registered_voters);

        await safeFetch(`/api/admin/polling-units/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, pu_code, registered_voters: parseInt(registered_voters) })
        });
        showToast('Polling Unit updated successfully.', 'success');
        loadAdminLgasAndPus();
    } catch (e) { }
}

window.deletePu = async function (id) {
    if (confirm(`Are you sure you want to delete Polling Unit ${id}?`)) {
        try {
            await safeFetch(`/api/admin/polling-units/${id}`, { method: 'DELETE' });
            showToast('Polling Unit deleted successfully.', 'success');
            loadAdminLgasAndPus();
        } catch (e) { }
    }
}

// Basic Edit functions for Election management
window.editElection = async function (id) {
    try {
        const election = await safeFetch(`/api/admin/elections/${id}`);
        const name = prompt("Enter new Election Name:", election.name);
        if (name === null) return;
        const description = prompt("Enter new Description:", election.description);
        const phase = prompt("Enter phase (preparation, active, completed):", election.phase);
        const scope = prompt("Enter scope (national, state, lga):", election.election_scope || "national");

        let state_id = election.state_id;
        let lga_id = election.lga_id;

        if (scope === 'state' || scope === 'lga') {
            state_id = prompt("Enter State ID (leave empty for null):", election.state_id || "");
        }
        if (scope === 'lga') {
            lga_id = prompt("Enter LGA ID (leave empty for null):", election.lga_id || "");
        }

        await safeFetch(`/api/admin/elections/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description,
                phase,
                election_scope: scope,
                state_id: state_id ? parseInt(state_id) : null,
                lga_id: lga_id ? parseInt(lga_id) : null
            })
        });
        showToast('Election updated successfully.', 'success');
        await loadElections(true); // Force refresh cache
        loadAdminElections();
    } catch (e) { }
}

window.deleteElection = async function (id) {
    if (confirm(`Are you sure you want to delete Election ${id}?`)) {
        try {
            await safeFetch(`/api/admin/elections/${id}`, { method: 'DELETE' });
            showToast('Election deleted successfully.', 'success');
            loadAdminElections();
        } catch (e) { }
    }
}

// Election Phase Change Functions
window.activateElection = async function (id) {
    if (confirm('Are you sure you want to activate this election? This will make it available for result reporting.')) {
        try {
            const response = await fetch(`/api/admin/elections/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phase: 'active' })
            });
            if (response.ok) {
                alert('Election activated successfully! It is now live for result collection.');
                await loadElections(true);
                loadAdminElections();
            } else {
                const result = await response.json();
                alert(`Error: ${result.error || 'Failed to activate election.'}`);
            }
        } catch (error) {
            console.error('Activate Election error:', error);
            alert('A network error occurred.');
        }
    }
}

window.completeElection = async function (id) {
    if (confirm('Are you sure you want to mark this election as completed? This will close it for further result submissions.')) {
        try {
            const response = await fetch(`/api/admin/elections/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phase: 'completed' })
            });
            if (response.ok) {
                alert('Election marked as completed.');
                await loadElections(true);
                loadAdminElections();
            } else {
                const result = await response.json();
                alert(`Error: ${result.error || 'Failed to complete election.'}`);
            }
        } catch (error) {
            console.error('Complete Election error:', error);
            alert('A network error occurred.');
        }
    }
}

window.reopenElection = async function (id) {
    const newPhase = confirm('Do you want to reopen this election as "Active"? Click OK for Active, or Cancel to set to Preparation.');
    const phase = newPhase ? 'active' : 'preparation';

    try {
        const response = await fetch(`/api/admin/elections/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phase })
        });
        if (response.ok) {
            alert(`Election reopened as "${phase}".`);
            await loadElections(true);
            loadAdminElections();
        } else {
            const result = await response.json();
            alert(`Error: ${result.error || 'Failed to reopen election.'}`);
        }
    } catch (error) {
        console.error('Reopen Election error:', error);
        alert('A network error occurred.');
    }
}

// Basic Edit functions for Candidate management
window.editCandidate = async function (id) {
    try {
        const candidate = await safeFetch(`/api/admin/candidates/${id}`);
        const full_name = prompt("Enter new Candidate Name:", candidate.full_name);
        if (full_name === null) return;
        const party = prompt("Enter new Party:", candidate.party);
        const election_id = prompt("Enter Election ID:", candidate.election_id);
        const is_preferred = confirm("Is this a Preferred Candidate? Click OK for Yes, Cancel for No.");
        const priority = prompt("Enter priority rank (higher shows first):", candidate.priority || "0");

        await safeFetch(`/api/admin/candidates/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name,
                party,
                election_id: parseInt(election_id) || candidate.election_id,
                is_preferred,
                priority: parseInt(priority) || 0
            })
        });
        showToast('Candidate updated successfully.', 'success');
        loadAdminCandidates();
    } catch (e) { }
}

window.deleteCandidate = async function (id) {
    if (confirm(`Are you sure you want to delete Candidate ${id}?`)) {
        try {
            await safeFetch(`/api/admin/candidates/${id}`, { method: 'DELETE' });
            showToast('Candidate deleted successfully.', 'success');
            loadAdminCandidates();
        } catch (e) { }
    }
}
/**
 * Live Parsing for OCR Markdown
 * Ported from Python parse_markdown_to_dict for UI feedback
 */
function jsParseMarkdownTable(markdown) {
    const result = {};
    if (!markdown) return result;

    const lines = markdown.split('\n');
    lines.forEach(line => {
        line = line.trim();
        if (!line || line.includes('---') || !line.includes('|')) return;

        let cells = line.split('|').map(c => c.trim()).filter(c => c !== "");
        if (cells.length < 2) return;

        let partyTitle = cells[0].toLowerCase();
        if (['party', 'parties', 'party name', 'total', 'totals', 'grand total'].includes(partyTitle)) return;

        // Extract alpha party code
        let partyMatch = cells[0].match(/([A-Za-z0-9]+)/);
        if (!partyMatch) return;
        let party = partyMatch[1].toUpperCase();

        // Extract votes
        let votesClean = cells[1].replace(/[^0-9]/g, '');
        if (votesClean) {
            let votes = parseInt(votesClean);
            result[party] = (result[party] || 0) + votes;
        }
    });
    return result;
}

function updateLivePreview() {
    const editor = document.getElementById('ocr-markdown-editor');
    const summaryDiv = document.getElementById('parsed-results-summary');
    const totalValSpan = document.getElementById('extracted-total-val');
    const accreditedInput = document.getElementById('accredited-voters-input');

    if (!editor || !summaryDiv) return;

    const results = jsParseMarkdownTable(editor.value);
    const accreditedVoters = parseInt(accreditedInput?.value || 0);
    let html = '';
    let total = 0;

    const parties = Object.keys(results);
    if (parties.length === 0) {
        summaryDiv.innerHTML = '<p style="color: #999; grid-column: span 2;">Start typing/formatting: | Party | Votes |</p>';
        totalValSpan.textContent = '0';
        totalValSpan.style.color = 'inherit';
        return;
    }

    parties.forEach(party => {
        const votes = results[party];
        total += votes;
        html += `
            <div style="background: #f1f1f1; padding: 4px 8px; border-radius: 4px; display: flex; justify-content: space-between;">
                <span style="font-weight: bold;">${party}</span>
                <span>${votes.toLocaleString()}</span>
            </div>
        `;
    });

    summaryDiv.innerHTML = html;
    totalValSpan.textContent = total.toLocaleString();

    // Visual warning if total > accredited
    if (accreditedVoters > 0 && total > accreditedVoters) {
        totalValSpan.style.color = '#ef4444';
        totalValSpan.title = "Total exceeds accredited voters!";
    } else {
        totalValSpan.style.color = '#10b981';
        totalValSpan.title = "";
    }
}

// ===== RESULT UPLOAD & VERIFICATION FLOW =====

window.initializeManualEntry = async function () {
    const electionId = document.getElementById('upload-election-select').value;
    const puId = document.getElementById('upload-pu-select').value;

    if (!electionId || !puId) {
        alert("Please select Election and Polling Unit first.");
        return;
    }

    // Create a ghost report for manual entry
    try {
        const response = await fetch('/api/upload-result', {
            method: 'POST',
            body: (() => {
                const fd = new FormData();
                fd.append('election_id', electionId);
                fd.append('pu_id', puId);
                // No file sent -> indicates manual mode
                return fd;
            })()
        });

        if (response.ok) {
            const data = await response.json();

            // Switch to verification stage
            document.getElementById('upload-stage').style.display = 'none';
            document.getElementById('verify-stage').style.display = 'block';

            document.getElementById('report-id-input').value = data.report_id;

            // Generate a blank EC8A template
            const elections = window.cachedElections || [];
            const election = elections.find(e => String(e.id) === String(electionId));
            const parties = await fetch(`/api/election/${electionId}/candidates`).then(r => r.json());
            const partyListStr = parties.map(p => p.party).join(', ');

            const template = `
# EC8A - POLLING UNIT LEVEL RESULT (MANUAL ENTRY)
> [!IMPORTANT]
> **INCIDENT FALLBACK MODE**: This report is being filed manually by a party agent.
> **DISRUPTION NOTICE**: Use this form if election processes were halted due to violence, technical failure, or other disruptions.

## 1. HEADER INFORMATION
- Serial Number (S/N): [ENTER S/N]
- Status: [E.G. COMPLETED / DISRUPTED BY VIOLENCE]
- State: [AUTO]
- Local Government Area (LGA): [AUTO]
- Registration Area (Ward): [AUTO]
- Polling Unit Name: [AUTO]
- Polling Unit Code: [AUTO]

## 2. FORM STATISTICS (NUMBERED ITEMS)
1. Number of Voters on the Register: 0
2. Number of Accredited Voters: 0
3. Number of Ballot Papers issued: 0
4. Number of Unused Ballot Papers: 0
5. Number of Spoilt Ballot Papers: 0
6. Number of Rejected Ballots: 0
7. Total Valid Votes: 0
8. Total Number of Used Ballot Papers: 0

## 3. PARTY RESULTS TABLE
| S/N | Political Party | Votes Scored (Figures) | Votes Scored (Words) |
|-----|-----------------|------------------------|----------------------|
${parties.map((p, i) => `| ${i + 1} | ${p.party} | 0 | ZERO |`).join('\n')}

## 4. FINAL VALIDATION & INCIDENT CONTEXT
- Agent Name/ID: [AUTO-DETECTION]
- Final Status: [NORMAL / ABANDONED / HALTED]
- Reason for Manual Entry: [E.G. VIOLENCE AT PU]
- Date: ${new Date().toLocaleDateString()}
`;
            document.getElementById('ocr-markdown-editor').value = template.trim();
            document.getElementById('verified-img').src = ""; // Clear image preview for manual mode

            if (window.updateLivePreview) window.updateLivePreview();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    } catch (e) {
        console.error(e);
        alert("Failed to initialize manual entry.");
    }
};

async function handleResultUpload(event) {
    if (event) event.preventDefault();

    const form = document.getElementById('result-upload-form');
    if (!form) return;

    const formData = new FormData(form);
    const statusDiv = document.getElementById('upload-status');

    // OFFLINE CHECK
    if (!navigator.onLine) {
        try {
            const reportData = {
                type: 'result_upload',
                payload: Object.fromEntries(formData.entries()),
                election_id: formData.get('election_id')
            };

            // Note: Handling File objects in IndexedDB is supported in modern browsers
            // If it's a file, we should keep it as is
            await window.OfflineDB.saveReport(reportData);
            window.showToast('Offline Mode: Result saved to device. Will sync when online.', 'info');
            form.reset();
            return;
        } catch (err) {
            console.error("Offline save failed:", err);
            window.showToast('Failed to save report offline.', 'error');
            return;
        }
    }

    try {
        if (statusDiv) {
            statusDiv.innerHTML = '<p class="loading-message">Uploading & analyzing with AI... Please wait.</p>';
            statusDiv.style.display = 'block';
        }

        const response = await fetch('/api/upload-result', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();

            // Switch to verification stage
            document.getElementById('upload-stage').style.display = 'none';
            document.getElementById('verify-stage').style.display = 'block';

            document.getElementById('report-id-input').value = data.report_id;
            document.getElementById('ocr-markdown-editor').value = data.markdown;
            document.getElementById('verified-img').src = data.image_url;

            // Trigger initial preview
            if (window.updateLivePreview) window.updateLivePreview();

            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            const result = await response.json();
            alert(`Upload Error: ${result.error || 'Failed to process image'}`);
        }
    } catch (err) {
        console.error("Upload failed:", err);
        alert("A network error occurred during upload.");
    } finally {
        if (statusDiv) statusDiv.style.display = 'none';
    }
}

async function submitFinalVerification() {
    const reportId = document.getElementById('report-id-input').value;
    const markdown = document.getElementById('ocr-markdown-editor').value;
    const accredited = document.getElementById('accredited-voters-input').value;

    if (!markdown) {
        alert("Please ensure some results are extracted first.");
        return;
    }

    try {
        const response = await fetch('/api/submit-final-markdown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                report_id: reportId,
                markdown: markdown,
                accredited_voters: parseInt(accredited) || 0
            })
        });

        if (response.ok) {
            alert("Result successfully verified and aggregated!");
            location.reload(); // Refresh to start clean or go to dashboard
        } else {
            const result = await response.json();
            alert(`Verification Error: ${result.error || 'Failed to submit'}`);
        }
    } catch (err) {
        console.error("Verification failed:", err);
        alert("A network error occurred.");
    }
}

function resetUpload() {
    if (confirm("Discard this extraction and start over?")) {
        location.reload();
    }
}

function zoomImage() {
    const src = document.getElementById('verified-img').src;
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    if (modal && modalImg) {
        modalImg.src = src;
        modal.style.display = 'flex';
    }
}

/**
 * Global Admin Action: Trigger INEC Delineation Sync
 */
window.triggerInecSync = async function () {
    if (!confirm("This will synchronize all Wards and Polling Units with INEC's official directory. This process runs in the background. Continue?")) return;
    try {
        const res = await safeFetch('/api/admin/sync-directory', { method: 'POST' });
        showToast(res.message, 'info');
    } catch (e) {
        console.error(e);
        showToast("Failed to trigger sync.", "error");
    }
};

window.triggerIrevSync = async function () {
    if (!confirm("This will scan the IReV portal for new active election cycles. Continue?")) return;
    try {
        const res = await safeFetch('/api/admin/sync-irev', { method: 'POST' });
        showToast(res.message, 'success');
        if (window.loadAdminElections) window.loadAdminElections();
    } catch (e) {
        console.error(e);
        showToast("Failed to sync IReV elections.", "error");
    }
};

// Global Admin Action: Trigger Party Registry Sync
window.triggerPartySync = async function () {
    if (!confirm("Trigger synchronization with official INEC Registered Political Parties?")) return;
    try {
        const res = await safeFetch('/api/admin/sync-parties', { method: 'POST' });
        showToast(res.message, 'info');

        // Listen for completion via Socket.IO
        if (socket) {
            socket.on('party_sync_complete', (results) => {
                showToast(`Party Sync Complete: ${results.new} new, ${results.updated} updated.`, 'success');
                loadAdminParties();
                // socket.off('party_sync_complete');
            });
        }
    } catch (e) { }
};

async function loadAdminParties() {
    const container = document.getElementById('party-list-container');
    if (!container) return;

    showAdminLoading('party-list-container', true);
    try {
        const parties = await safeFetch('/api/admin/parties');
        let html = `
            <table class="premium-table">
                <thead>
                    <tr>
                        <th style="width: 60px;">Logo</th>
                        <th>Abbrev.</th>
                        <th>Party Name</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${parties.map(p => `
                        <tr>
                            <td>
                                <div style="width: 35px; height: 35px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                                    ${p.logo_url ? `<img src="${p.logo_url}" style="width: 100%; height: 100%; object-fit: contain;">` : `<i class="fas fa-flag" style="color: #cbd5e1;"></i>`}
                                </div>
                            </td>
                            <td><span class="badge-party party-${p.abbreviation.toLowerCase()}">${p.abbreviation}</span></td>
                            <td style="font-weight: 600;">${p.name}</td>
                            <td><span class="badge" style="background: #f8fafc; color: #475569; border: 1px solid #e2e8f0;">${p.is_active ? 'Active' : 'Inactive'}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        container.innerHTML = html;
        if (parties.length === 0) {
            container.innerHTML = '<div style="padding: 2rem; text-align: center; color: #666;"><p>No political parties registered yet.</p><p style="font-size: 0.8rem;">Click sync above to fetch the official INEC registry.</p></div>';
        }
    } catch (e) {
        container.innerHTML = '<p style="color: var(--primary-red); padding: 1rem;">Failed to load party registry.</p>';
    } finally {
        showAdminLoading('party-list-container', false);
    }
}

// ===== RAG AGENT LOGIC =====
function toggleRagAgent() {
    const win = document.getElementById('rag-agent-window');
    if (win) {
        win.style.display = win.style.display === 'none' ? 'flex' : 'none';
    }
}

async function sendRagQuery() {
    const input = document.getElementById('rag-agent-input');
    const body = document.getElementById('rag-chat-body');
    const electionId = document.getElementById('dashboard-election-select')?.value;

    const query = input.value.trim();
    if (!query) return;

    // Append user msg
    const userDiv = document.createElement('div');
    userDiv.className = 'user-msg';
    userDiv.style = "background: var(--primary-red); color: white; padding: 0.75rem; border-radius: 12px 12px 0 12px; align-self: flex-end; max-width: 85%; font-size: 0.9rem; margin-top: 0.5rem;";
    userDiv.textContent = query;
    body.appendChild(userDiv);
    input.value = '';
    body.scrollTop = body.scrollHeight;

    // Append typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.style = "font-size: 0.75rem; color: #666; margin-top: 0.25rem;";
    typingDiv.innerHTML = "<em>AI Scout is thinking...</em>";
    body.appendChild(typingDiv);

    try {
        const response = await fetch('/api/ai/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, election_id: electionId })
        });
        const data = await response.json();

        typingDiv.remove();

        const aiDiv = document.createElement('div');
        aiDiv.className = 'ai-msg';
        aiDiv.style = "background: white; padding: 0.75rem; border-radius: 12px 12px 12px 0; max-width: 85%; font-size: 0.9rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); white-space: pre-wrap;";

        // Basic markdown-to-html (bold only for now)
        aiDiv.innerHTML = data.answer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        body.appendChild(aiDiv);
        body.scrollTop = body.scrollHeight;

    } catch (err) {
        typingDiv.innerHTML = "<span style='color:red;'>Error connecting to AI.</span>";
    }
}

// Global Help Function
async function safeFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (e) {
        console.error(`SafeFetch Error (${url}):`, e);
        throw e;
    }
}

// News Sync Handling
async function syncLiveNews() {
    const btn = event?.currentTarget;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-sync fa-spin"></i> Syncing...';
    }

    try {
        const res = await fetch('/api/monitoring/sync', { method: 'POST' });
        if (res.ok) {
            showToast("Real-time live news sync started...", "info");
        }
    } catch (e) {
        console.error("Sync trigger fail:", e);
    } finally {
        if (btn) {
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-sync-alt"></i> Sync Live Data';
            }, 3000);
        }
    }
}

// Export functions
window.syncLiveNews = syncLiveNews;
window.toggleRagAgent = toggleRagAgent;
window.sendRagQuery = sendRagQuery;
window.safeFetch = safeFetch;
window.updateLivePreview = updateLivePreview;
window.triggerInecSync = triggerInecSync;
window.triggerPartySync = triggerPartySync;
// ===== AGENT PORTAL LOGIC =====
window.switchAgentTab = function (tabName) {
    document.querySelectorAll('.agent-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.agent-tab-content').forEach(c => c.style.display = 'none');

    document.querySelector(`[data-agent-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}-agent-tab`).style.display = 'block';
};

async function handleIncidentSubmit(e) {
    e.preventDefault();
    const form = e.target;

    // Enforce HTML5 validation rules (required, minlength, etc)
    if (!form.reportValidity()) return;

    // Performance: Basic validation before even creating FormData
    const electCheck = document.getElementById('inc-election-select')?.value;
    if (!electCheck && !form.querySelector('[name="election_id"]')?.value) {
        showToast("Please select the active election.", "error");
        return;
    }

    const formData = new FormData(form);

    // Auto-inject election_id if visible on page (from main upload form)
    let electionId = formData.get('election_id');
    if (!electionId) {
        electionId = document.getElementById('election-select')?.value;
        if (electionId) formData.set('election_id', electionId);
    }

    // Auto-inject PU ID (Critical for Location)
    const puSelect = document.getElementById('pu-code');
    let puId = puSelect?.value;

    const explicitPu = document.getElementById('inc-pu-select')?.value;
    if (explicitPu) {
        formData.set('pu_id', explicitPu);
    }

    let finalElectionId = formData.get('election_id');
    if (!finalElectionId) {
        finalElectionId = document.getElementById('inc-election-select')?.value;
        if (finalElectionId) formData.set('election_id', finalElectionId);
    }

    // FINAL VALIDATION
    if (!formData.get('election_id')) {
        showToast("Error: Target election not identified.", "error");
        return;
    }

    // OFFLINE CHECK
    if (!navigator.onLine) {
        try {
            const payload = Object.fromEntries(formData.entries());
            const hasSQLite = typeof window.SQLiteDB !== 'undefined';

            if (hasSQLite) {
                await window.SQLiteDB.saveRecord('incident', payload);
            } else {
                await window.OfflineDB.saveReport({ type: 'incident_report', payload });
            }

            window.showToast(`Offline Mode: Incident saved to ${hasSQLite ? 'SQLite' : 'device'}.`, 'info');
            form.reset();
            return;
        } catch (err) {
            console.error("Offline save failed:", err);
            window.showToast('Failed to save incident offline.', 'error');
            return;
        }
    }

    try {
        const res = await safeFetch('/api/report-incident', {
            method: 'POST',
            body: formData
        });
        showToast(res.message, 'success');
        form.reset();

        // Refresh feed if visible
        if (typeof loadFieldIncidents === 'function') loadFieldIncidents();
    } catch (err) {
        console.error("Incident report failed:", err);
        showToast(err.message || "Failed to broadcast incident alert. Check logs.", "error");
    }
}

window.jsParseMarkdownTable = jsParseMarkdownTable;
window.loadAdminTabData = loadAdminTabData;
window.loadAdminPanelData = loadAdminPanelData;
window.loadUploadTabDependencies = loadUploadTabDependencies;
window.setupFormDependencies = setupFormDependencies;
window.submitFinalVerification = submitFinalVerification;
window.resetUpload = resetUpload;
window.zoomImage = zoomImage;
window.handleResultUpload = handleResultUpload;

// Attach RAG listeners
document.addEventListener('DOMContentLoaded', () => {
    const trigger = document.getElementById('rag-agent-trigger');
    if (trigger) trigger.addEventListener('click', toggleRagAgent);

    const sendBtn = document.getElementById('send-rag-query');
    if (sendBtn) sendBtn.addEventListener('click', sendRagQuery);

    const input = document.getElementById('rag-agent-input');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendRagQuery();
        });
    }

    // Results Tab Election Selector
    const resSelect = document.getElementById("results-election-select");
    if (resSelect) {
        resSelect.addEventListener("change", () => {
            loadResultsData();
        });
    }

    // Agent Incident Reporting Form
    const incidentForm = document.getElementById("incident-reporting-form");
    if (incidentForm) {
        incidentForm.addEventListener("submit", handleIncidentSubmit);
    }

    // Export Button Listeners
    const exportPdf = document.getElementById('export-pdf-btn');
    const exportCsv = document.getElementById('export-csv-btn');

    if (exportPdf) {
        exportPdf.addEventListener('click', () => {
            if (exportPdf.dataset.electionId) {
                window.open(`/election/${exportPdf.dataset.electionId}/print-report`, '_blank');
            } else {
                showToast("Please select an election first.", "error");
            }
        });
    }

    if (exportCsv) {
        exportCsv.addEventListener('click', () => {
            if (exportCsv.dataset.electionId) {
                window.location.href = `/api/election/${exportCsv.dataset.electionId}/export/csv`;
            } else {
                showToast("Please select an election first.", "error");
            }
        });
    }
});
async function loadFieldIncidents() {
    const tbody = document.getElementById('field-incidents-tbody');
    const badge = document.getElementById('incident-count-badge');
    if (!tbody) return;

    try {
        const electionId = window.currentElectionId;
        const url = electionId ? `/api/incidents?election_id=${electionId}` : '/api/incidents';
        const incidents = await safeFetch(url);
        if (badge) badge.textContent = incidents.length;

        if (incidents.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:3rem; color:#64748b;">No field incidents reported yet.</td></tr>';
            return;
        }

        tbody.innerHTML = incidents.map(i => {
            const severityColor = i.severity === 'critical' ? '#dc2626' : i.severity === 'high' ? '#f59e0b' : '#3b82f6';
            let evidenceHtml = '<span style="color:#94a3b8;">None</span>';
            if (i.image_url) {
                const isVideo = i.image_url.toLowerCase().match(/\.(mp4|webm|mov)$/);
                const icon = isVideo ? 'fa-video' : 'fa-image';
                const label = isVideo ? 'Play Video' : 'View Image';
                evidenceHtml = `<button class="btn btn-sm btn-primary" onclick="window.open('${i.image_url}', '_blank')"><i class="fas ${icon}"></i> ${label}</button>`;
            }

            return `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 1rem; font-weight: 600;">${i.timestamp}</td>
                    <td style="padding: 1rem;">
                        <strong>${i.location || 'Unknown Location'}</strong>
                        ${i.pu_code && i.pu_code !== 'N/A' ? `<br/><span class="badge" style="font-size:0.7rem; background:#e2e8f0; color:#475569; margin-top:4px;">${i.pu_code}</span>` : ''}
                    </td>
                    <td style="padding: 1rem;"><span class="badge" style="background:#f1f5f9; color:#1e293b; font-size:0.7rem;">${i.type.toUpperCase()}</span></td>
                    <td style="padding: 1rem;"><span style="color: ${severityColor}; font-weight: 700;"><i class="fas fa-circle" style="font-size:0.6rem;"></i> ${i.severity.toUpperCase()}</span></td>
                    <td style="padding: 1rem; font-size: 0.9rem; max-width: 300px;">${i.description}</td>
                    <td style="padding: 1rem;">${evidenceHtml}</td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        console.error("Failed to load incidents:", err);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:red; padding:2rem;">Failed to connect to incident feed.</td></tr>';
    }
}

window.loadFieldIncidents = loadFieldIncidents;

// ===== ADMIN ELECTION SCOPE HANDLER =====
// Handle scope dropdown changes for election creation form
document.addEventListener('DOMContentLoaded', () => {
    const scopeSelect = document.getElementById('admin-election-scope-select');
    const locationContainer = document.getElementById('admin-location-container');
    const stateSelect = document.getElementById('admin-election-state-select');
    const lgaSelect = document.getElementById('admin-election-lga-select');

    if (scopeSelect) {
        scopeSelect.addEventListener('change', async () => {
            const scope = scopeSelect.value;
            console.log("Scope changed to:", scope);

            if (scope === 'national') {
                if (locationContainer) locationContainer.style.display = 'none';
                if (stateSelect) stateSelect.value = '';
                if (lgaSelect) lgaSelect.value = '';
            } else {
                // Show location container as grid
                if (locationContainer) locationContainer.style.display = 'grid';

                // Load states if not already populated
                if (stateSelect && stateSelect.options.length <= 1) {
                    try {
                        const response = await fetch('/api/states');
                        const states = await response.json();
                        stateSelect.innerHTML = '<option value="">Select State</option>';
                        states.forEach(state => {
                            const option = document.createElement('option');
                            option.value = state.id;
                            option.textContent = state.name;
                            stateSelect.appendChild(option);
                        });
                    } catch (error) {
                        console.error('Error loading states:', error);
                    }
                }

                // Toggle LGA visibility based on scope
                if (lgaSelect) {
                    if (scope === 'state') {
                        lgaSelect.style.display = 'none';
                        lgaSelect.value = '';
                    } else if (scope === 'lga') {
                        lgaSelect.style.display = 'block';
                    }
                }
            }
        });
    }
});

// ===== OFFLINE SYNC HANDLER (Tier 1) =====
async function processSyncQueue() {
    if (!navigator.onLine) return;

    try {
        const reports = await window.OfflineDB.getAllReports();
        if (reports.length === 0) return;

        window.showToast(`Restored connection! Syncing ${reports.length} offline records...`, 'info');

        let successCount = 0;

        for (const report of reports) {
            try {
                const endpoint = report.type === 'result_upload' ? '/api/upload-result' : '/api/report-incident';

                // Reconstruct FormData for multipart/form-data
                const formData = new FormData();
                for (const key in report.payload) {
                    const value = report.payload[key];
                    if (value instanceof Blob) {
                        formData.append(key, value, value.name || 'offline_file');
                    } else if (typeof value === 'string' && value.startsWith('data:image')) {
                        const blob = await (await fetch(value)).blob();
                        formData.append(key, blob, 'offline_capture.jpg');
                    } else {
                        formData.append(key, value);
                    }
                }

                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    await window.OfflineDB.deleteReport(report.id);
                    successCount++;
                }
            } catch (e) {
                console.error("Sync failed for item:", report.id, e);
            }
        }

        if (successCount > 0) {
            window.showToast(`Successfully synced ${successCount} offline records!`, 'success');
            // Refresh counts/views
            if (typeof loadMonitoringData === 'function') loadMonitoringData();
            if (typeof loadFieldIncidents === 'function') loadFieldIncidents();
        }
    } catch (err) {
        console.error("Sync process failed:", err);
    }
}

// Background Sync Listeners
window.addEventListener('online', () => {
    document.body.classList.remove('is-offline');
    processSyncQueue();
});
window.addEventListener('offline', () => {
    document.body.classList.add('is-offline');
    window.showToast('You are now offline. Reports will be saved locally.', 'warning');
});
window.addEventListener('load', () => {
    if (!navigator.onLine) document.body.classList.add('is-offline');
    if (navigator.onLine) processSyncQueue();
});
