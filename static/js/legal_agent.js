document.addEventListener('DOMContentLoaded', () => {
    const selector = document.getElementById('report-election-select');
    if (selector) {
        loadReportElections();
        selector.addEventListener('change', () => {
            const electionId = selector.value;
            if (electionId) {
                loadResultsForElection(electionId);
            }
        });
    }
});

async function loadReportElections() {
    const selector = document.getElementById('report-election-select');
    if (!selector) return;
    try {
        const res = await fetch('/api/elections');
        const elections = await res.json();

        selector.innerHTML = '<option value="">Select Election</option>';
        elections.forEach(e => {
            const opt = document.createElement('option');
            opt.value = e.id;
            opt.textContent = `${e.name} (${e.phase})`;
            selector.appendChild(opt);
        });

        // Auto-select first active if available
        const active = elections.find(e => e.phase === 'active');
        if (active) {
            selector.value = active.id;
            loadResultsForElection(active.id);
        }
    } catch (e) {
        console.error("Failed to load elections", e);
    }
}

async function loadResultsForElection(electionId) {
    try {
        const res = await fetch(`/api/election-results/${electionId}`);
        const data = await res.json();

        // Update Stats
        document.getElementById('rep-total-votes').textContent = data.total_votes.toLocaleString();
        document.getElementById('rep-total-pus').textContent = data.reporting_pus;
        document.getElementById('rep-accredited').textContent = data.total_accredited.toLocaleString();

        // Render Table
        renderResultsTable(data.party_standings, data.total_valid);

        // Reset Legal Panel
        document.getElementById('legal-agent-panel').style.display = 'none';

    } catch (e) {
        console.error("Error loading results", e);
    }
}

function renderResultsTable(standings, totalValid) {
    const container = document.getElementById('results-table-container');
    if (!standings || standings.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding: 2rem; color: #94a3b8;">No verified results available yet.</p>';
        return;
    }

    let html = '';
    standings.forEach((party, index) => {
        const color = getPartyColor(party.party);
        html += `
            <div class="result-row">
                <div style="width: 50px; font-weight: 700; color: #334155;">${party.party}</div>
                <div class="result-bar-bg">
                    <div class="result-bar-fill" style="width: ${party.percentage}%; background-color: ${color};"></div>
                </div>
                <div style="width: 120px; text-align: right;">
                    <div style="font-weight: 700;">${party.votes.toLocaleString()}</div>
                    <div style="font-size: 0.8rem; color: #64748b;">${party.percentage}%</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Re-using the color logic from script.js simpler here
const PARTY_COLORS_LEGAL = {
    'APC': '#3b82f6', 'PDP': '#ef4444', 'LP': '#10b981',
    'NNPP': '#f59e0b', 'APGA': '#8b5cf6', 'ADC': '#06b6d4'
};
function getPartyColor(party) {
    return PARTY_COLORS_LEGAL[party] || '#6366f1';
}

async function runLegalAnalysis() {
    const electionId = document.getElementById('report-election-select').value;
    if (!electionId) {
        alert("Please select an election first.");
        return;
    }

    const btn = document.getElementById('btn-run-analysis');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    btn.disabled = true;

    try {
        const res = await fetch(`/api/legal-analysis/${electionId}`);
        const analysis = await res.json();

        renderLegalVerdict(analysis);

    } catch (e) {
        console.error(e);
        alert("Analysis failed.");
    } finally {
        btn.innerHTML = '<i class="fas fa-gavel"></i> Consult Legal Agent';
        btn.disabled = false;
    }
}

function renderLegalVerdict(data) {
    const panel = document.getElementById('legal-agent-panel');
    const content = document.getElementById('legal-content');

    const isClean = data.loopholes.length === 0;
    const verdictColor = isClean ? '#10b981' : (data.loopholes.length > 5 ? '#ef4444' : '#f59e0b');

    let html = `
        <div style="background: white; padding: 1.5rem; border-radius: 8px; border-left: 4px solid ${verdictColor}; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <h3 style="margin-top:0; color: ${verdictColor};">${data.verdict}</h3>
            <p style="font-size: 1.1rem; line-height: 1.6; color: #334155;">${data.winner_analysis}</p>
        </div>
    `;

    if (!isClean) {
        html += `
            <div style="margin-top: 1.5rem;">
                <h4 style="color: #ef4444; margin-bottom: 1rem;"><i class="fas fa-exclamation-triangle"></i> Identified Irregularities (${data.loophole_count})</h4>
                <div style="background: #fff1f2; border: 1px solid #fecaca; border-radius: 6px; max-height: 300px; overflow-y: auto;">
                    ${data.loopholes.map(loop => `
                        <div style="padding: 1rem; border-bottom: 1px solid #ffe4e6;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
                                <strong style="color:#991b1b;">${loop.type}</strong>
                                <span style="font-size:0.8rem; background:#fee2e2; color:#b91c1c; padding:2px 6px; border-radius:4px;">${loop.severity}</span>
                            </div>
                            <div style="font-size:0.9rem; color:#7f1d1d;">${loop.details}</div>
                            <div style="font-size:0.8rem; color:#9ca3af; margin-top:0.25rem;">Location: ${loop.location}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else {
        html += `
            <div style="margin-top: 1.5rem; padding: 1rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; color: #166534;">
                <i class="fas fa-check-circle"></i> No significant loopholes detected in the reported data so far.
            </div>
        `;
    }

    content.innerHTML = html;
    panel.style.display = 'block';

    // Scroll to panel
    panel.scrollIntoView({ behavior: 'smooth' });
}

// ===== LAWFARE: PETITION DOSSIER =====
async function loadLawfareDossier(electionId) {
    const loader = document.getElementById('dossier-loader');
    const content = document.getElementById('dossier-content');
    const empty = document.getElementById('dossier-empty-state');

    if (!electionId) {
        empty.style.display = 'block';
        content.style.display = 'none';
        return;
    }

    // Sync selector if called from outside
    const dossierSelect = document.getElementById('dossier-election-select');
    if (dossierSelect && dossierSelect.value !== electionId) {
        dossierSelect.value = electionId;
    }

    empty.style.display = 'none';
    content.style.display = 'none';
    loader.style.display = 'block';

    try {
        const res = await fetch(`/api/legal-analysis/${electionId}/petition-dossier-data`);
        const data = await res.json();
        renderLawfareDossier(data);
        content.style.display = 'block';
    } catch (e) {
        console.error("Dossier load failed", e);
        showToast("Failed to generate petition dossier", "error");
    } finally {
        loader.style.display = 'none';
    }
}

function renderLawfareDossier(data) {
    const container = document.getElementById('dossier-content');
    const analysis = data.analysis;
    const election = data.election;

    let html = `
        <div class="premium-card" style="padding: 3rem; font-family: 'Inter', serif; background: #fff; box-shadow: var(--shadow-lg); border: 1px solid #e2e8f0; border-radius: 4px;">
            <div style="text-align: center; border-bottom: 3px solid var(--primary-red); padding-bottom: 2rem; margin-bottom: 2.5rem;">
                <h1 style="color: var(--primary-red); font-size: 2.2rem; margin-bottom: 0.5rem; letter-spacing: 0.1em;">ELECTION PETITION DOSSIER</h1>
                <h2 style="font-size: 1.2rem; font-weight: 500; color: #334155;">${election.name}</h2>
            </div>

            <div style="display: flex; justify-content: space-between; background: #f8fafc; padding: 1.5rem; border-radius: 6px; margin-bottom: 3rem; font-size: 0.9rem; border: 1px solid #e2e8f0;">
                <div><strong>Election ID:</strong> ${election.id}</div>
                <div><strong>Generated:</strong> ${new Date().toLocaleString()}</div>
                <div><strong>Classification:</strong> <span style="color:var(--primary-red); font-weight:700;">CONFIDENTIAL / LEGAL USE</span></div>
            </div>

            <section style="margin-bottom: 3rem;">
                <h3 style="font-size: 1.3rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1.5rem; color: var(--primary-red);">1. EXECUTIVE SUMMARY</h3>
                <div style="padding: 1.5rem; border-radius: 8px; border-left: 5px solid ${analysis.verdict.includes('CONTESTED') ? '#ef4444' : '#10b981'}; background: ${analysis.verdict.includes('CONTESTED') ? '#fff1f2' : '#f0fdf4'}; margin-bottom: 2rem;">
                    <h4 style="font-size: 1.2rem; margin-bottom: 0.5rem;">${analysis.verdict}</h4>
                    <p>${analysis.winner_analysis}</p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                    <div style="background: #f8fafc; padding: 1rem; text-align: center; border-radius: 6px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-red);">${analysis.stats.total_pus_analyzed}</div>
                        <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase;">PUs Analyzed</div>
                    </div>
                    <div style="background: #f8fafc; padding: 1rem; text-align: center; border-radius: 6px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-red);">${analysis.stats.total_votes.toLocaleString()}</div>
                        <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase;">Total Votes</div>
                    </div>
                    <div style="background: #f8fafc; padding: 1rem; text-align: center; border-radius: 6px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-red);">${analysis.loophole_count}</div>
                        <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase;">Irregularities</div>
                    </div>
                    <div style="background: #f8fafc; padding: 1rem; text-align: center; border-radius: 6px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-red);">${analysis.section_51_summary.count}</div>
                        <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase;">Section 51(2)</div>
                    </div>
                </div>
            </section>

            <section style="margin-bottom: 3rem;">
                <h3 style="font-size: 1.3rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1.5rem; color: var(--primary-red);">2. STATUTORY NON-COMPLIANCE (Section 51(2))</h3>
                <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; background: #fffbeb; padding: 1rem; border-radius: 6px; border: 1px solid #fde68a;">
                    <strong>Legal Basis:</strong> Section 51(2) of the Electoral Act 2022 mandates cancellation where votes exceed accredited voters. This dossier identifies units where total votes exceeded registered voters (Absolute Over-voting).
                </p>
                
                ${analysis.section_51_violations.length > 0 ? `
                <table class="premium-table" style="font-size: 0.85rem;">
                    <thead>
                        <tr>
                            <th>PU Code</th>
                            <th>Location</th>
                            <th>Registered</th>
                            <th>Votes Cast</th>
                            <th>Excess</th>
                            <th>Evidence</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${analysis.section_51_violations.map(v => `
                            <tr style="background: #fff1f2;">
                                <td>${v.pu_code}</td>
                                <td>${v.location}</td>
                                <td>${v.registered.toLocaleString()}</td>
                                <td>${v.ballots.toLocaleString()}</td>
                                <td style="color: #ef4444; font-weight: 700;">+${v.excess_votes}</td>
                                <td><button class="btn btn-sm" onclick="viewEvidence('${v.image_path}')">View EC8A</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ` : '<p style="text-align: center; padding: 2rem; color: #94a3b8;">No Section 51(2) violations detected.</p>'}
            </section>

            <section style="margin-bottom: 3rem;">
                <h3 style="font-size: 1.3rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1.5rem; color: var(--primary-red);">3. EVIDENCE APPENDIX (EC8A Result Sheets)</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;">
                    ${analysis.section_51_violations.filter(v => v.image_path).map(v => `
                        <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f8fafc;">
                            <img src="${v.image_path.startsWith('/') ? v.image_path : '/' + v.image_path}" style="width: 100%; height: 150px; object-fit: cover; cursor: pointer;" onclick="window.zoomImageFromPath('${v.image_path}')">
                            <div style="padding: 0.75rem; font-size: 0.75rem;">
                                <strong>EC8A: ${v.pu_code}</strong><br>
                                Excess: ${v.excess_votes}
                            </div>
                        </div>
                    `).join('')}
                    ${analysis.section_51_violations.filter(v => v.image_path).length === 0 ? '<p style="grid-column: span 3; text-align: center; color: #94a3b8; padding: 1rem;">No EC8A evidence images linked to Section 51(2) violations.</p>' : ''}
                </div>
            </section>

            <section style="margin-bottom: 3rem;">
                <h3 style="font-size: 1.3rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-bottom: 1.5rem; color: var(--primary-red);">4. FIELD INCIDENT EVIDENCE</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;">
                    ${analysis.incident_evidence.filter(i => i.image_path).map(inc => `
                        <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f8fafc;">
                            <img src="${inc.image_path.startsWith('/') ? inc.image_path : '/' + inc.image_path}" style="width: 100%; height: 150px; object-fit: cover; cursor: pointer;" onclick="window.zoomImageFromPath('${inc.image_path}')">
                            <div style="padding: 0.75rem; font-size: 0.75rem;">
                                <strong>${inc.type}: ${inc.pu_code}</strong><br>
                                <span style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${inc.description}</span>
                            </div>
                        </div>
                    `).join('')}
                    ${analysis.incident_evidence.filter(i => i.image_path).length === 0 ? '<p style="grid-column: span 3; text-align: center; color: #94a3b8; padding: 1rem;">No recorded field incident pictures for this election.</p>' : ''}
                </div>
            </section>
        </div>
    `;

    container.innerHTML = html;
}

// ===== LAWFARE: LEGAL MATRIX =====
async function loadLawfareMatrix(electionId) {
    const loader = document.getElementById('matrix-loader');
    const content = document.getElementById('matrix-content');
    const empty = document.getElementById('matrix-empty-state');

    if (!electionId) {
        empty.style.display = 'block';
        content.style.display = 'none';
        return;
    }

    // Sync selector if called from outside
    const matrixSelect = document.getElementById('matrix-election-select');
    if (matrixSelect && matrixSelect.value !== electionId) {
        matrixSelect.value = electionId;
    }

    empty.style.display = 'none';
    content.style.display = 'none';
    loader.style.display = 'block';

    try {
        const res = await fetch(`/api/legal-analysis/${electionId}/discrepancy-matrix`);
        const data = await res.json();
        renderLawfareMatrix(data.matrix);
        content.style.display = 'block';
    } catch (e) {
        console.error("Matrix load failed", e);
        showToast("Failed to load discrepancy matrix", "error");
    } finally {
        loader.style.display = 'none';
    }
}

function renderLawfareMatrix(matrix) {
    const tbody = document.getElementById('matrix-tbody');
    const issueCount = document.getElementById('matrix-discrepancy-count');

    let issues = 0;
    let html = '';

    matrix.forEach(row => {
        const hasIssue = row.discrepancy !== null && Math.abs(row.discrepancy) > 0;
        if (hasIssue) issues++;

        html += `
            <tr style="${hasIssue ? 'background: #fff1f2;' : ''}">
                <td style="font-weight: 700;">${row.pu_code}</td>
                <td><div style="font-size: 0.8rem;">${row.pu_name}</div><div style="font-size: 0.7rem; color: #64748b;">${row.lga}</div></td>
                <td>${row.agent.registered.toLocaleString()}</td>
                <td>${row.agent.accredited.toLocaleString()}</td>
                <td><strong>${row.agent.valid_votes.toLocaleString()}</strong></td>
                <td>${row.inec.accredited ? row.inec.accredited.toLocaleString() : '-'}</td>
                <td><strong>${row.inec.valid_votes ? row.inec.valid_votes.toLocaleString() : '-'}</strong></td>
                <td style="font-weight: 700; color: ${hasIssue ? '#ef4444' : '#10b981'};">
                    ${row.discrepancy !== null ? (row.discrepancy > 0 ? '+' : '') + row.discrepancy.toLocaleString() : 'N/A'}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="window.zoomImageFromPath('${row.image_path}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
    issueCount.textContent = issues;
}

window.viewEvidence = (path) => {
    window.zoomImageFromPath(path);
};

window.zoomImageFromPath = (path) => {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    if (modal && modalImg && path) {
        modalImg.src = path.startsWith('/') ? path : '/' + path;
        modal.style.display = 'flex';
    }
};

// ===== LEGAL AI ADVISOR (RAG) =====
document.addEventListener('DOMContentLoaded', () => {
    const askBtn = document.getElementById('ask-legal-ai');
    const queryInput = document.getElementById('legal-ai-query');

    if (askBtn && queryInput) {
        askBtn.addEventListener('click', () => performLegalConsultation());
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performLegalConsultation();
        });
    }
});

async function performLegalConsultation() {
    const query = document.getElementById('legal-ai-query').value;
    const loader = document.getElementById('legal-ai-loader');
    const resultsDiv = document.getElementById('legal-ai-results');
    const sectionsDiv = document.getElementById('legal-ai-sections');
    const opinionDiv = document.getElementById('legal-ai-opinion');

    if (!query.trim()) return;

    loader.style.display = 'block';
    resultsDiv.style.display = 'none';

    try {
        const response = await fetch('/api/legal/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ violation_text: query })
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        // Render Sections
        sectionsDiv.innerHTML = data.sections.map(s => `
            <div style="background: white; padding: 0.75rem; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 0.85rem;">
                <div style="font-weight: 700; color: var(--primary-red); margin-bottom: 0.25rem;">${s.section} ${s.subsection || ''}</div>
                <div style="display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; color: #64748b;">${s.content}</div>
                <button class="btn btn-sm btn-link" style="padding: 0; font-size: 0.75rem; margin-top: 0.5rem;" onclick="alert('${s.content.replace(/'/g, "\\'")}')">Read Full Section</button>
            </div>
        `).join('');

        // Render Opinion (Markdown-like formatting)
        opinionDiv.innerHTML = data.analysis
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        resultsDiv.style.display = 'grid';

    } catch (e) {
        console.error("Legal AI fail:", e);
        showToast("AI Consultation failed", "error");
    } finally {
        loader.style.display = 'none';
    }
}
