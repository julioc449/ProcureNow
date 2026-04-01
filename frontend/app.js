/**
 * RFP Compliance Auditor — Frontend Application
 * Design System: Nexus Audit Pro / The Obsidian Audit
 */

// ─── State ───
let rfpFile = null;
let proposalFile = null;
let auditData = null;
let activeFilter = 'all';
let currentProposalId = null;

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

const navDashboard      = document.getElementById('navDashboard');
const navLibrary        = document.getElementById('navLibrary');

const pdfViewerPage     = document.getElementById('pdfViewerPage');
const complianceLibrary = document.getElementById('complianceLibrary');

const libraryTableBody  = document.getElementById('libraryTableBody');
const libraryEmptyState = document.getElementById('libraryEmptyState');
const pdfViewerCardsContainer = document.getElementById('pdfViewerCardsContainer');


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
    if (!zone) return;
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
        
        currentProposalId = auditData.proposal_id;

        // Setup PDF viewer url mapped to the current uploaded file
        if (proposalFile) {
            if (window.currentPdfUrl) URL.revokeObjectURL(window.currentPdfUrl);
            window.currentPdfUrl = URL.createObjectURL(proposalFile);
        }

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
        currentProposalId = auditData.proposal_id;
        renderDashboard(auditData);
    } catch (err) {
        hideLoading();
        alert(`Demo audit failed: ${err.message}`);
    }
}

// ─── UI State Management ───
let loadingInterval = null;
const loadingMessages = [
    "Uploading to secure vault...",
    "Extracting RFP requirements...",
    "Mapping proposal table of contents...",
    "Cross-referencing compliance rules...",
    "Evaluating risk factors...",
    "Structuring final audit report..."
];

function showLoading() {
    uploadSection.style.display = 'none';
    loadingOverlay.classList.add('active');
    dashboard.classList.remove('active');
    
    // Manage dynamic loading text
    const statusText = document.getElementById('loadingStatusText');
    if (statusText) {
        let msgIndex = 0;
        statusText.textContent = "Initializing analysis...";
        clearInterval(loadingInterval);
        loadingInterval = setInterval(() => {
            if (msgIndex < loadingMessages.length) {
                statusText.textContent = loadingMessages[msgIndex];
                msgIndex++;
            }
        }, 3500); // update every 3.5 seconds
    }
}

function hideLoading() {
    clearInterval(loadingInterval);
    loadingOverlay.classList.remove('active');
    uploadSection.style.display = 'block';
}

function showDashboard() {
    clearInterval(loadingInterval);
    loadingOverlay.classList.remove('active');
    uploadSection.style.display = 'none';
    complianceLibrary.classList.remove('active');
    pdfViewerPage.classList.remove('active');
    dashboard.classList.add('active');
}

function resetToUpload() {
    dashboard.classList.remove('active');
    complianceLibrary.classList.remove('active');
    pdfViewerPage.classList.remove('active');
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
    currentProposalId = null;
}

// ─── Routing ───
navDashboard.addEventListener('click', () => {
    navDashboard.classList.add('active');
    navLibrary.classList.remove('active');
    complianceLibrary.classList.remove('active');
    pdfViewerPage.classList.remove('active');
    
    if (auditData) {
        dashboard.classList.add('active');
        uploadSection.style.display = 'none';
    } else {
        dashboard.classList.remove('active');
        uploadSection.style.display = 'block';
    }
});

navLibrary.addEventListener('click', () => {
    navLibrary.classList.add('active');
    navDashboard.classList.remove('active');
    
    dashboard.classList.remove('active');
    pdfViewerPage.classList.remove('active');
    uploadSection.style.display = 'none';
    
    complianceLibrary.classList.add('active');
    loadLibrary();
});

// ─── Evidence View Toggle ───
window.openEvidenceView = function() {
    dashboard.classList.remove('active');
    pdfViewerPage.classList.add('active');
    if (auditData) {
        renderPdfViewerPage(auditData);
    }
};

window.closeEvidenceView = function() {
    pdfViewerPage.classList.remove('active');
    dashboard.classList.add('active');
};

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
                             <button class="btn-icon" title="Export PDF" onclick="downloadReport('pdf', '${audit.id}')">
                                <span class="material-symbols-outlined">picture_as_pdf</span>
                            </button>
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
        currentProposalId = auditData.proposal_id;
        
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

let auditToDelete = null;

window.deleteAudit = function(id) {
    auditToDelete = id;
    document.getElementById('deleteModal').style.display = 'flex';
};

window.closeDeleteModal = function() {
    auditToDelete = null;
    document.getElementById('deleteModal').style.display = 'none';
};

window.confirmDelete = async function() {
    if (!auditToDelete) return;
    const id = auditToDelete;
    
    // Optimistic UI updates
    closeDeleteModal();
    const btnIcon = document.querySelector(`button[onclick="deleteAudit('${id}')"]`);
    if(btnIcon) btnIcon.innerHTML = '<span class="spinner-small" style="width:16px;height:16px;border-width:2px;"></span>';
    
    try {
        const res = await fetch(`/api/audits/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete audit');
        
        if (auditData && auditData.proposal_id === id) {
            resetToUpload();
            navLibrary.click();
        } else {
            loadLibrary();
        }
    } catch (err) {
        alert(`Failed to delete: ${err.message}`);
        if(btnIcon) btnIcon.innerHTML = '<span class="material-symbols-outlined">delete</span>';
    }
};

// ─── Dashboard Rendering ───
function renderDashboard(data) {
    showDashboard();

    rfpTitle.textContent = data.rfp_name || 'RFP Document';
    proposalId.textContent = `AUDIT ID: ${data.proposal_id || ''}`;

    animateNumber(completeCount, data.complete);
    animateNumber(partialCount, data.partial);
    animateNumber(incompleteCount, data.incomplete);

    animateProgressRing(data);
    renderCategories(data.audit_results);

    // Update Export buttons (high-specificity selector to avoid skeleton)
    const summaryRow = document.querySelector('#dashboard .summary-row');
    console.log("[Dashboard] summaryRow found:", summaryRow);
    if (!summaryRow) {
        console.warn("[Dashboard] summaryRow NOT found in #dashboard!");
        return;
    }
    
    const existingActions = summaryRow.querySelector('.summary-actions');
    if (existingActions) existingActions.remove();

    const actions = document.createElement('div');
    actions.className = 'summary-actions';
    actions.innerHTML = `
        <button class="btn btn-secondary" onclick="downloadReport('csv')">
            <span class="material-symbols-outlined">download</span> Export CSV
        </button>
        <button class="btn btn-secondary" onclick="downloadReport('pdf')">
            <span class="material-symbols-outlined">picture_as_pdf</span> Export PDF
        </button>
        <button class="btn btn-primary" onclick="openEvidenceView()">
            <span class="material-symbols-outlined">splitscreen</span> View Source Evidence
        </button>
    `;
    summaryRow.appendChild(actions);
    console.log("[Dashboard] Export buttons appended to summaryRow.");

    const priorityItems = data.audit_results.filter(r => 
        (r.status === 'Partial' || r.status === 'Incomplete') && 
        (r.risk_level === 'Critical' || r.risk_level === 'High')
    );
    
    const pmSection = document.getElementById('priorityMatrixSection');
    const pmContainer = document.getElementById('priorityMatrixContainer');
    
    if (priorityItems.length > 0) {
        pmSection.style.display = 'block';
        pmContainer.innerHTML = priorityItems.map(r => renderRequirementCard(r, true)).join('');
    } else {
        pmSection.style.display = 'none';
        pmContainer.innerHTML = '';
    }
}

window.renderPdfViewerPage = function(data) {
    if (!data || !data.audit_results) return;
    
    // Clear previous cards
    pdfViewerCardsContainer.innerHTML = '';
    
    // Re-render categories layout (reusing logic from dashboard)
    renderCategories(data.audit_results, pdfViewerCardsContainer);
    
    const pdfFrame = document.getElementById('proposalPdfFrame');
    const emptyState = document.getElementById('pdfEmptyState');
    
    if (window.currentPdfUrl) {
        if (emptyState) emptyState.style.display = 'none';
        if (pdfFrame) {
            pdfFrame.style.display = 'block';
            if (!pdfFrame.src.includes(window.currentPdfUrl)) {
                pdfFrame.src = window.currentPdfUrl;
            }
        }
    } else {
        // Fallback for historical audits or lost state
        if (pdfFrame) pdfFrame.style.display = 'none';
        if (emptyState) emptyState.style.display = 'flex';
    }
};

function animateProgressRing(data) {
    const C = 2 * Math.PI * 65;
    const total = data.complete + data.partial + data.incomplete;
    if (total === 0) return;

    const completeLen   = (data.complete   / total) * C;
    const partialLen    = (data.partial    / total) * C;
    const incompleteLen = (data.incomplete / total) * C;

    const partialStartDeg    = (data.complete / total) * 360;
    const incompleteStartDeg = ((data.complete + data.partial) / total) * 360;

    ringComplete.setAttribute('transform',   `rotate(0, 75, 75)`);
    ringPartial.setAttribute('transform',    `rotate(${partialStartDeg}, 75, 75)`);
    ringIncomplete.setAttribute('transform', `rotate(${incompleteStartDeg}, 75, 75)`);

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            ringComplete.style.strokeDasharray   = `${completeLen}, ${C}`;
            ringPartial.style.strokeDasharray    = `${partialLen}, ${C}`;
            ringIncomplete.style.strokeDasharray = `${incompleteLen}, ${C}`;
        });
    });

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
        if (progress < 1) requestAnimationFrame(update);
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

function renderCategories(results, targetContainer = categoriesContainer) {
    targetContainer.innerHTML = '';
    const grouped = {};
    results.forEach(r => {
        if (!grouped[r.category]) grouped[r.category] = [];
        grouped[r.category].push(r);
    });

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
        targetContainer.appendChild(section);
    });
    applyFilter(activeFilter);
}

function renderRequirementCard(r, isPriorityMatrix = false) {
    const statusClass = r.status.toLowerCase();
    const pctFilled = r.status === 'Complete' ? 100 : (r.percentage_filled || 0);
    const confidencePct = Math.round(r.confidence_score * 100);

    const riskHtml = r.risk_level && r.status !== 'Complete' ? 
        `<span class="risk-badge ${r.risk_level.toLowerCase()}">
            <span class="material-symbols-outlined">
                ${r.risk_level === 'Critical' ? 'gavel' : r.risk_level === 'High' ? 'warning' : r.risk_level === 'Medium' ? 'info' : 'check'}
            </span>
            ${r.risk_level} Risk
         </span>` : '';

    const evidenceHtml = r.proposal_evidence && r.proposal_evidence !== 'N/A'
        ? `<div class="detail-block">
               <h4>
                   <span class="material-symbols-outlined">description</span>
                   Evidence from Proposal
               </h4>
               <p class="evidence-quote">${escapeHtml(r.proposal_evidence)}</p>
               ${r.page_reference ? `<div class="page-ref" onclick="scrollToPdfPage(${r.page_reference}, event)"><span class="material-symbols-outlined" style="font-size:14px">insert_drive_file</span> Page ${r.page_reference}</div>` : ''}
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

    const reasoningHtml = r.risk_reasoning && r.status !== 'Complete' ? 
        `<div class="detail-block">
             <h4>
                 <span class="material-symbols-outlined">policy</span>
                 Risk Analysis
             </h4>
             <p style="color: var(--text-main); font-weight: 500;">${escapeHtml(r.risk_reasoning)}</p>
         </div>` : '';

    return `
        <div class="requirement-card" data-status="${r.status}" data-req="${escapeHtml(r.requirement).replace(/"/g, '&quot;')}" onclick="toggleCard(this)">
            <div class="requirement-card-header">
                <div class="status-indicator ${statusClass}"></div>
                <div class="requirement-text">
                    ${isPriorityMatrix ? `<span style="color: var(--text-muted); font-size: 0.85em; font-weight: 500; display: block; margin-bottom: 2px;">${escapeHtml(r.category)}</span>` : ''}
                    ${escapeHtml(r.requirement)}
                </div>
                ${riskHtml}
                <span class="status-badge ${statusClass}">${r.status}</span>
                <span class="confidence-mini">AI Confidence: ${confidencePct}%</span>
                <span class="expand-icon">
                    <span class="material-symbols-outlined">expand_more</span>
                </span>
            </div>
            <div class="requirement-detail">
                <div class="detail-content">
                    ${reasoningHtml}
                    ${evidenceHtml}
                    ${missingHtml}
                </div>
                <div class="percentage-bar-wrapper">
                    <div class="percentage-bar-label">
                        <span>Audit Match Accuracy</span>
                        <span>${pctFilled.toFixed(0)}%</span>
                    </div>
                    <div class="percentage-bar">
                        <div class="percentage-bar-fill ${statusClass}" style="width: ${pctFilled}%;"></div>
                    </div>
                </div>
                <div class="override-actions" onclick="event.stopPropagation()">
                    <h4><span class="material-symbols-outlined">edit</span> Manual Override</h4>
                    <button class="override-btn ${r.status === 'Complete' ? 'active-complete' : ''}" onclick="overrideStatus(this, 'Complete')">
                        <span class="material-symbols-outlined" style="font-size:16px;">check_circle</span> Complete
                    </button>
                    <button class="override-btn ${r.status === 'Partial' ? 'active-partial' : ''}" onclick="overrideStatus(this, 'Partial')">
                        <span class="material-symbols-outlined" style="font-size:16px;">warning</span> Partial
                    </button>
                    <button class="override-btn ${r.status === 'Incomplete' ? 'active-incomplete' : ''}" onclick="overrideStatus(this, 'Incomplete')">
                        <span class="material-symbols-outlined" style="font-size:16px;">cancel</span> Incomplete
                    </button>
                </div>
            </div>
        </div>
    `;
}

// ─── Card Expand/Collapse & Overrides ───
window.toggleCard = function(card) {
    card.classList.toggle('expanded');
};

window.overrideStatus = async function(btnEl, newStatus) {
    if (!currentProposalId) return;
    
    const card = btnEl.closest('.requirement-card');
    const requirement = card.getAttribute('data-req');
    
    // Prevent redundant clicks
    if (card.dataset.status === newStatus) return;
    
    // Visual optimistic update (optional, but helps UX)
    btnEl.innerHTML = '<span class="spinner-small" style="width:14px;height:14px;border-width:2px;"></span> Saving...';
    
    try {
        const res = await fetch(`/api/audits/${currentProposalId}/override`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ requirement, status: newStatus })
        });
        
        if (!res.ok) {
            const errDetails = await res.json();
            throw new Error(errDetails.detail || `Server returned ${res.status}`);
        }
        
        // Success: Re-fetch the audit data and fully re-render the dashboard to update all progress rings and numbers seamlessly.
        const auditRes = await fetch(`/api/audits/${currentProposalId}`);
        if (!auditRes.ok) throw new Error('Failed to refresh audit data');
        
        auditData = await auditRes.json();
        
        // Re-render
        renderDashboard(auditData);
        
        // Because re-rendering closes everything, we could intentionally keep the card open by finding it again:
        setTimeout(() => {
            const newCards = document.querySelectorAll('.requirement-card');
            for(let c of newCards) {
                if(c.getAttribute('data-req') === requirement) {
                    c.classList.add('expanded');
                    break;
                }
            }
        }, 50);
        
    } catch (err) {
        alert(`Failed to override status: ${err.message}`);
        // Reset button
        btnEl.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px;">${newStatus === 'Complete' ? 'check_circle' : newStatus === 'Partial' ? 'warning' : 'cancel'}</span> ${newStatus}`;
    }
};

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

    document.querySelectorAll('.category-section').forEach(section => {
        const visibleCards = section.querySelectorAll('.requirement-card:not([style*="display: none"])');
        section.style.display = visibleCards.length > 0 ? '' : 'none';
    });
}

// ─── Event Listeners ───
analyzeBtn.addEventListener('click', runFullAudit);
demoBtn.addEventListener('click', runDemoAudit);
newAuditBtn.addEventListener('click', resetToUpload);
exportCsvBtn.addEventListener('click', () => downloadReport('csv'));

// ─── Utility ───
window.downloadReport = async function(type, overrideId = null) {
    const id = overrideId || currentProposalId;
    if (!id) return;
    
    const endpoint = type === 'pdf' ? 'export-pdf' : 'export-csv';
    const extension = type === 'pdf' ? 'pdf' : 'csv';
    
    console.log(`[Export] Requesting ${type} for ID: ${id}`);
    try {
        const response = await fetch(`/api/${endpoint}/${id}`);
        console.log(`[Export] Response status: ${response.status}`);
        if (!response.ok) throw new Error(`Server returned ${response.status}`);
        
        const blob = await response.blob();
        console.log(`[Export] Blob received, size: ${blob.size}`);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `ProcureNow_Audit_${id}.${extension}`;
        document.body.appendChild(a);
        a.click();
        
        // Use a small timeout before cleanup to ensure the click is handled
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 200);
    } catch (err) {
        console.error('Export Error:', err);
        alert(`Failed to export report: ${err.message}`);
    }
};

function escapeHtml(text) {
    const div = document.createElement('div');
    if (text === null || text === undefined) return '';
    div.textContent = text;
    return div.innerHTML;
}

// ─── PDF Viewer Scroll Logic ───
window.scrollToPdfPage = function(pageNum, evt) {
    if (evt) evt.stopPropagation();
    
    if (!window.currentPdfUrl) {
        alert("PDF viewer is unavailable for historical or demo audits.");
        return;
    }
    
    const frame = document.getElementById('proposalPdfFrame');
    if (frame) {
        frame.src = `${window.currentPdfUrl}#page=${pageNum}`;
    }
};
