/**
 * RFP Compliance Auditor — Frontend Application
 * Design System: Nexus Audit Pro / The Obsidian Audit
 */

// ─── State ───
let rfpFile = null;
let proposalFile = null;
let auditData = null;
let activeFilter = 'all';

// ─── DOM Elements ───
const rfpZone = document.getElementById('rfpZone');
const proposalZone = document.getElementById('proposalZone');
const rfpInput = document.getElementById('rfpInput');
const proposalInput = document.getElementById('proposalInput');
const rfpFileName = document.getElementById('rfpFileName');
const proposalFileName = document.getElementById('proposalFileName');
const analyzeBtn = document.getElementById('analyzeBtn');
const demoBtn = document.getElementById('demoBtn');
const uploadSection = document.getElementById('uploadSection');
const loadingOverlay = document.getElementById('loadingOverlay');
const dashboard = document.getElementById('dashboard');
const progressText      = document.getElementById('progressText');
const ringComplete      = document.getElementById('ringComplete');
const ringPartial       = document.getElementById('ringPartial');
const ringIncomplete    = document.getElementById('ringIncomplete');
const completeCount     = document.getElementById('completeCount');
const partialCount      = document.getElementById('partialCount');
const incompleteCount   = document.getElementById('incompleteCount');
const categoriesContainer = document.getElementById('categoriesContainer');
const rfpTitle          = document.getElementById('rfpTitle');
const proposalId        = document.getElementById('proposalId');
const exportCsvBtn      = document.getElementById('exportCsvBtn');
const newAuditBtn       = document.getElementById('newAuditBtn');
const filterBar         = document.getElementById('filterBar');

// Routing elements
const navDashboard      = document.getElementById('navDashboard');
const navLibrary        = document.getElementById('navLibrary');
const complianceLibrary = document.getElementById('complianceLibrary');
const libraryTableBody  = document.getElementById('libraryTableBody');
const libraryEmptyState = document.getElementById('libraryEmptyState');


// ─── Category Material Icons ───
const CATEGORY_ICONS = {
    'Safety':                   'health_and_safety',
    'Insurance':                'shield',
    'Bonding':                  'link',
    'Credentials':              'workspace_premium',
    'Environmental':            'eco',
    'Materials':                'construction',
    'Timeline':                 'event',
    'Staffing':                 'engineering',
    'Financial':                'account_balance',
    'References':               'menu_book',
    'Quality Control':          'verified',
    'Legal':                    'gavel',
    'Equipment':                'precision_manufacturing',
    'Permits':                  'assignment',
    'Technical Specifications': 'architecture',
};

// ─── File Upload Handlers ───
function setupDropZone(zone, input, fileNameEl, fileType) {
    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, e => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, e => {
            e.preventDefault();
            zone.classList.remove('dragover');
        });
    });

    zone.addEventListener('drop', e => {
        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            setFile(file, fileType, fileNameEl, zone);
        }
    });

    input.addEventListener('change', e => {
        const file = e.target.files[0];
        if (file) {
            setFile(file, fileType, fileNameEl, zone);
        }
    });
}

function setFile(file, type, fileNameEl, zone) {
    if (type === 'rfp') {
        rfpFile = file;
    } else {
        proposalFile = file;
    }
    fileNameEl.textContent = `✓ ${file.name}`;
    zone.classList.add('has-file');
    updateAnalyzeButton();
}

function updateAnalyzeButton() {
    analyzeBtn.disabled = !(rfpFile && proposalFile);
}

setupDropZone(rfpZone, rfpInput, rfpFileName, 'rfp');
setupDropZone(proposalZone, proposalInput, proposalFileName, 'proposal');

// ─── API Calls ───
async function runFullAudit() {
    showLoading();

    const formData = new FormData();
    formData.append('rfp', rfpFile);
    formData.append('proposal', proposalFile);

    try {
        const res = await fetch('/api/full-audit', {
            method: 'POST',
            body: formData,
        });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        auditData = await res.json();
        renderDashboard(auditData);
    } catch (err) {
        hideLoading();
        alert(`Audit failed: ${err.message}\n\nMake sure the server is running.`);
    }
}

async function runDemoAudit() {
    showLoading();
    try {
        const res = await fetch('/api/demo-audit', { method: 'POST' });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        auditData = await res.json();
        renderDashboard(auditData);
    } catch (err) {
        hideLoading();
        alert(`Demo audit failed: ${err.message}\n\nMake sure the server is running on http://localhost:8000`);
    }
}

// ─── UI State Management ───
function showLoading() {
    uploadSection.style.display = 'none';
    loadingOverlay.classList.add('active');
    dashboard.classList.remove('active');
}

function hideLoading() {
    loadingOverlay.classList.remove('active');
    uploadSection.style.display = 'block';
}

function showDashboard() {
    loadingOverlay.classList.remove('active');
    uploadSection.style.display = 'none';
    complianceLibrary.classList.remove('active');
    dashboard.classList.add('active');
}

function resetToUpload() {
    dashboard.classList.remove('active');
    complianceLibrary.classList.remove('active');
    uploadSection.style.display = 'block';
    rfpFile = null;
    proposalFile = null;
    rfpFileName.textContent = '';
    proposalFileName.textContent = '';
    rfpZone.classList.remove('has-file');
    proposalZone.classList.remove('has-file');
    rfpInput.value = '';
    proposalInput.value = '';
    updateAnalyzeButton();
    auditData = null;
}

// ─── Routing ───
navDashboard.addEventListener('click', () => {
    navDashboard.classList.add('active');
    navLibrary.classList.remove('active');
    complianceLibrary.classList.remove('active');
    if (auditData) {
        dashboard.classList.add('active');
    } else {
        uploadSection.style.display = 'block';
    }
});

navLibrary.addEventListener('click', () => {
    navLibrary.classList.add('active');
    navDashboard.classList.remove('active');
    dashboard.classList.remove('active');
    uploadSection.style.display = 'none';
    complianceLibrary.classList.add('active');
    loadLibrary();
});

// ─── Compliance Library Logic ───
async function loadLibrary() {
    libraryTableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 2rem;">Loading audits...</td></tr>';
    libraryEmptyState.style.display = 'none';
    
    try {
        const res = await fetch('/api/audits');
        if (!res.ok) throw new Error('Failed to load audits');
        const audits = await res.json();
        
        if (audits.length === 0) {
            libraryTableBody.innerHTML = '';
            libraryEmptyState.style.display = 'block';
            return;
        }
        
        libraryTableBody.innerHTML = audits.map(audit => {
            const date = new Date(audit.created_at).toLocaleDateString(undefined, {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
            
            return `
                <tr>
                    <td>
                        <div class="lib-title">${escapeHtml(audit.rfp_name)}</div>
                        <div class="lib-id">${audit.id}</div>
                    </td>
                    <td class="lib-date">${date}</td>
                    <td>
                        <span class="lib-score" style="color: ${getScoreColor(audit.overall_percentage)}">
                            ${audit.overall_percentage.toFixed(1)}%
                        </span>
                    </td>
                    <td>
                        <div class="category-stats" style="margin:0;">
                            <span class="mini-badge complete-badge">${audit.complete_count} ✓</span>
                            ${audit.partial_count > 0 ? `<span class="mini-badge partial-badge">${audit.partial_count} ~</span>` : ''}
                            ${audit.incomplete_count > 0 ? `<span class="mini-badge incomplete-badge">${audit.incomplete_count} ✗</span>` : ''}
                        </div>
                    </td>
                    <td>
                        <div class="lib-actions">
                            <button class="btn-icon" title="View Report" onclick="viewAudit('${audit.id}')">
                                <span class="material-symbols-outlined">visibility</span>
                            </button>
                            <a href="/api/export-csv/${audit.id}" class="btn-icon" title="Export CSV" download>
                                <span class="material-symbols-outlined">download</span>
                            </a>
                            <button class="btn-icon danger" title="Delete Audit" onclick="deleteAudit('${audit.id}')">
                                <span class="material-symbols-outlined">delete</span>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
    } catch (err) {
        libraryTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--incomplete); padding: 2rem;">Error: ${err.message}</td></tr>`;
    }
}

function getScoreColor(pct) {
    if (pct >= 85) return 'var(--complete)';
    if (pct >= 60) return 'var(--partial)';
    return 'var(--incomplete)';
}

window.viewAudit = async function(id) {
    showLoading();
    try {
        const res = await fetch(`/api/audits/${id}`);
        if (!res.ok) throw new Error('Audit not found');
        auditData = await res.json();
        
        // Switch nav state manually
        navDashboard.classList.add('active');
        navLibrary.classList.remove('active');
        complianceLibrary.classList.remove('active');
        
        renderDashboard(auditData);
    } catch (err) {
        hideLoading();
        alert(`Failed to load audit: ${err.message}`);
    }
};

window.deleteAudit = async function(id) {
    if (!confirm('Are you sure you want to delete this audit report? This cannot be undone.')) return;
    
    try {
        const res = await fetch(`/api/audits/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete audit');
        
        // If viewing the deleted audit, reset to upload
        if (auditData && auditData.proposal_id === id) {
            resetToUpload();
            navLibrary.click(); // force library view
        } else {
            loadLibrary();      // just refresh table
        }
    } catch (err) {
        alert(`Failed to delete: ${err.message}`);
    }
};

// ─── Dashboard Rendering ───
function renderDashboard(data) {
    showDashboard();

    // Header info
    rfpTitle.textContent = data.rfp_name || 'RFP Document';
    proposalId.textContent = `AUDIT ID: ${data.proposal_id || ''}`;

    // Stats
    animateNumber(completeCount, data.complete);
    animateNumber(partialCount, data.partial);
    animateNumber(incompleteCount, data.incomplete);

    // Progress ring
    animateProgressRing(data);

    // Render categories
    renderCategories(data.audit_results);
}

function animateProgressRing(data) {
    const C = 2 * Math.PI * 65; // circumference for r=65
    const total = data.complete + data.partial + data.incomplete;
    if (total === 0) return;

    const completeLen   = (data.complete   / total) * C;
    const partialLen    = (data.partial    / total) * C;
    const incompleteLen = (data.incomplete / total) * C;

    // Rotation offsets so each arc starts where the previous one ends
    const partialStartDeg    = (data.complete / total) * 360;
    const incompleteStartDeg = ((data.complete + data.partial) / total) * 360;

    ringComplete.setAttribute('transform',   `rotate(0, 75, 75)`);
    ringPartial.setAttribute('transform',    `rotate(${partialStartDeg}, 75, 75)`);
    ringIncomplete.setAttribute('transform', `rotate(${incompleteStartDeg}, 75, 75)`);

    // Trigger CSS transition by setting dasharray in next frame
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            ringComplete.style.strokeDasharray   = `${completeLen}, ${C}`;
            ringPartial.style.strokeDasharray    = `${partialLen}, ${C}`;
            ringIncomplete.style.strokeDasharray = `${incompleteLen}, ${C}`;
        });
    });

    // Animate percentage number
    animateValue(progressText, 0, data.overall_percentage, 1500);
}

function animateValue(el, start, end, duration) {
    const startTime = performance.now();
    const rounded = Math.round(end * 10) / 10;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = start + (rounded - start) * ease;

        el.innerHTML = `${current.toFixed(1)}<span>%</span>`;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

function animateNumber(el, target) {
    const duration = 1000;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(target * ease);
        el.textContent = current;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function renderCategories(results) {
    categoriesContainer.innerHTML = '';

    // Group by category
    const grouped = {};
    results.forEach(r => {
        if (!grouped[r.category]) grouped[r.category] = [];
        grouped[r.category].push(r);
    });

    // Sort categories: most incomplete first
    const sortedCategories = Object.entries(grouped).sort((a, b) => {
        const scoreA = a[1].reduce((s, r) => s + (r.status === 'Incomplete' ? 2 : r.status === 'Partial' ? 1 : 0), 0);
        const scoreB = b[1].reduce((s, r) => s + (r.status === 'Incomplete' ? 2 : r.status === 'Partial' ? 1 : 0), 0);
        return scoreB - scoreA;
    });

    sortedCategories.forEach(([category, items], idx) => {
        const section = document.createElement('div');
        section.className = 'category-section';
        section.style.animation = `fadeInUp 0.5s ease-out ${idx * 0.08}s both`;

        const catComplete = items.filter(r => r.status === 'Complete').length;
        const catPartial = items.filter(r => r.status === 'Partial').length;
        const catIncomplete = items.filter(r => r.status === 'Incomplete').length;
        const iconName = CATEGORY_ICONS[category] || 'assignment';

        section.innerHTML = `
            <div class="category-header">
                <div class="category-icon">
                    <span class="material-symbols-outlined">${iconName}</span>
                </div>
                <h2>${escapeHtml(category)}</h2>
                <div class="category-stats">
                    ${catComplete > 0 ? `<span class="mini-badge complete-badge">${catComplete} ✓</span>` : ''}
                    ${catPartial > 0 ? `<span class="mini-badge partial-badge">${catPartial} ~</span>` : ''}
                    ${catIncomplete > 0 ? `<span class="mini-badge incomplete-badge">${catIncomplete} ✗</span>` : ''}
                </div>
            </div>
            <div class="requirements-list">
                ${items.map(r => renderRequirementCard(r)).join('')}
            </div>
        `;
        categoriesContainer.appendChild(section);
    });

    // Apply any active filter
    applyFilter(activeFilter);
}

function renderRequirementCard(r) {
    const statusClass = r.status.toLowerCase();
    const pctFilled = r.status === 'Complete' ? 100 : (r.percentage_filled || 0);
    const confidencePct = Math.round(r.confidence_score * 100);

    const evidenceHtml = r.proposal_evidence && r.proposal_evidence !== 'N/A'
        ? `<div class="detail-block">
               <h4>
                   <span class="material-symbols-outlined">description</span>
                   Evidence from Proposal
               </h4>
               <p class="evidence-quote">${escapeHtml(r.proposal_evidence)}</p>
               ${r.page_reference ? `<div class="page-ref"><span class="material-symbols-outlined" style="font-size:14px">insert_drive_file</span> Page ${r.page_reference}</div>` : ''}
           </div>`
        : `<div class="detail-block">
               <h4>
                   <span class="material-symbols-outlined">description</span>
                   Evidence
               </h4>
               <p style="color: var(--outline); font-style: italic;">No matching evidence found in the proposal.</p>
           </div>`;

    const missingHtml = r.missing_elements && r.missing_elements.length > 0
        ? `<div class="detail-block">
               <h4>
                   <span class="material-symbols-outlined">error</span>
                   Missing Elements
               </h4>
               <ul class="missing-list">
                   ${r.missing_elements.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
               </ul>
           </div>`
        : `<div class="detail-block">
               <h4>
                   <span class="material-symbols-outlined">check_circle</span>
                   Missing Elements
               </h4>
               <p style="color: var(--complete);">All elements satisfied</p>
           </div>`;

    return `
        <div class="requirement-card" data-status="${r.status}" onclick="toggleCard(this)">
            <div class="requirement-card-header">
                <div class="status-indicator ${statusClass}"></div>
                <div class="requirement-text">${escapeHtml(r.requirement)}</div>
                <span class="status-badge ${statusClass}">${r.status}</span>
                <span class="confidence-mini">${confidencePct}%</span>
                <span class="expand-icon">
                    <span class="material-symbols-outlined">expand_more</span>
                </span>
            </div>
            <div class="requirement-detail">
                <div class="detail-content">
                    ${evidenceHtml}
                    ${missingHtml}
                </div>
                <div class="percentage-bar-wrapper">
                    <div class="percentage-bar-label">
                        <span>Completion</span>
                        <span>${pctFilled.toFixed(0)}%</span>
                    </div>
                    <div class="percentage-bar">
                        <div class="percentage-bar-fill ${statusClass}" style="width: ${pctFilled}%;"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ─── Card Expand/Collapse ───
function toggleCard(card) {
    card.classList.toggle('expanded');
}

// ─── Filtering ───
filterBar.addEventListener('click', e => {
    if (e.target.classList.contains('filter-chip')) {
        const filter = e.target.dataset.filter;
        activeFilter = filter;
        document.querySelectorAll('.filter-chip').forEach(c =>
            c.classList.remove('active', 'active-complete', 'active-partial', 'active-incomplete')
        );
        if      (filter === 'Complete')   e.target.classList.add('active-complete');
        else if (filter === 'Partial')    e.target.classList.add('active-partial');
        else if (filter === 'Incomplete') e.target.classList.add('active-incomplete');
        else                              e.target.classList.add('active');
        applyFilter(filter);
    }
});

function applyFilter(filter) {
    document.querySelectorAll('.requirement-card').forEach(card => {
        if (filter === 'all' || card.dataset.status === filter) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Hide empty category sections
    document.querySelectorAll('.category-section').forEach(section => {
        const visibleCards = section.querySelectorAll('.requirement-card:not([style*="display: none"])');
        section.style.display = visibleCards.length > 0 ? '' : 'none';
    });
}

// ─── Event Listeners ───
analyzeBtn.addEventListener('click', runFullAudit);
demoBtn.addEventListener('click', runDemoAudit);
newAuditBtn.addEventListener('click', resetToUpload);
exportCsvBtn.addEventListener('click', () => {
    if (auditData && auditData.proposal_id) {
        window.location.href = `/api/export-csv/${auditData.proposal_id}`;
    }
});

// ─── Utility ───
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
