/**
 * АИС УДЗ - JavaScript приложение
 * Веб-интерфейс для системы управления документами закупок
 */

// API Base URL
const API_BASE = '/api/v1';

// State
let currentPage = 'analysis';
let analysisResult = null;

// ===================== Initialization =====================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initUploadArea();
    initAnalyzeButton();
    initRegistryFilters();
    loadControlStages();
    loadAnalytics();
});

// ===================== Navigation =====================

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[data-page]');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            showPage(page);
        });
    });
}

function showPage(pageName) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === pageName);
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });

    // Update title
    const titles = {
        'analysis': 'Анализ закупочной документации',
        'registry': 'Реестр документов',
        'packages': 'Формирование пакетов',
        'control': 'Многоэтапный контроль',
        'reports': 'Отчеты и аналитика'
    };
    document.getElementById('page-title').textContent = titles[pageName] || pageName;

    currentPage = pageName;

    // Load page data
    if (pageName === 'registry') {
        loadRegistryDocuments();
    } else if (pageName === 'control') {
        loadControlStages();
    } else if (pageName === 'reports') {
        loadAnalytics();
    }
}

// ===================== File Upload =====================

function initUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    const allowedTypes = ['.pdf', '.docx', '.doc', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowedTypes.includes(ext)) {
        showToast('error', 'Неподдерживаемый формат файла');
        return;
    }

    showLoading(true);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/analyze/file`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        analysisResult = result;
        displayAnalysisResult(result);
        showToast('success', 'Анализ успешно завершен');

    } catch (error) {
        console.error('Error uploading file:', error);
        showToast('error', 'Ошибка при анализе файла');
    } finally {
        showLoading(false);
    }
}

// ===================== Text Analysis =====================

function initAnalyzeButton() {
    const analyzeBtn = document.getElementById('analyze-btn');

    analyzeBtn.addEventListener('click', async () => {
        const textInput = document.getElementById('text-input');
        const text = textInput.value.trim();

        if (!text) {
            showToast('warning', 'Введите текст документации или загрузите файл');
            return;
        }

        showLoading(true);

        try {
            const response = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            analysisResult = result;
            displayAnalysisResult(result);
            showToast('success', 'Анализ успешно завершен');

        } catch (error) {
            console.error('Error analyzing text:', error);
            showToast('error', 'Ошибка при анализе текста');
        } finally {
            showLoading(false);
        }
    });
}

function displayAnalysisResult(result) {
    const resultsCard = document.getElementById('results-card');
    resultsCard.style.display = 'block';

    // Procurement Info
    const procInfo = result.procurement_info || {};
    const infoSection = document.getElementById('procurement-info');
    infoSection.innerHTML = `
        <h4>Информация о закупке</h4>
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">Номер закупки</span>
                <span class="info-value">${procInfo.number || 'Не указан'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Правовая основа</span>
                <span class="info-value">${procInfo.legal_basis || 'Не определена'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Тип процедуры</span>
                <span class="info-value">${procInfo.procedure_type || 'Не определен'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Заказчик</span>
                <span class="info-value">${procInfo.customer || 'Не указан'}</span>
            </div>
        </div>
    `;

    // Statistics
    const docs = result.required_documents || [];
    const mandatory = docs.filter(d => d.mandatory).length;
    const optional = docs.length - mandatory;

    const statsGrid = document.getElementById('stats-grid');
    statsGrid.innerHTML = `
        <div class="stat-item">
            <div class="stat-value">${docs.length}</div>
            <div class="stat-label">Всего документов</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${mandatory}</div>
            <div class="stat-label">Обязательных</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${optional}</div>
            <div class="stat-label">Опциональных</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${result.model_size || 'N/A'}</div>
            <div class="stat-label">Модель</div>
        </div>
    `;

    // Documents Table
    const tbody = document.querySelector('#documents-table tbody');
    tbody.innerHTML = docs.map((doc, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>${doc.name || 'Без названия'}</td>
            <td>${doc.category || '-'}</td>
            <td>
                <span class="badge ${doc.mandatory ? 'badge-danger' : 'badge-info'}">
                    ${doc.mandatory ? 'Да' : 'Нет'}
                </span>
            </td>
            <td>${doc.format || '-'}</td>
            <td>${doc.validity_requirements || '-'}</td>
        </tr>
    `).join('');

    // Scroll to results
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

// ===================== Registry =====================

function initRegistryFilters() {
    const searchInput = document.getElementById('registry-search');
    const categorySelect = document.getElementById('registry-category');
    const statusSelect = document.getElementById('registry-status');

    const filterHandler = debounce(() => loadRegistryDocuments(), 300);

    searchInput?.addEventListener('input', filterHandler);
    categorySelect?.addEventListener('change', filterHandler);
    statusSelect?.addEventListener('change', filterHandler);
}

async function loadRegistryDocuments() {
    const search = document.getElementById('registry-search')?.value || '';
    const category = document.getElementById('registry-category')?.value || '';
    const status = document.getElementById('registry-status')?.value || '';

    try {
        const params = new URLSearchParams();
        if (search) params.append('query', search);
        if (category) params.append('category', category);
        if (status) params.append('status', status);

        const response = await fetch(`${API_BASE}/documents?${params}`);
        const data = await response.json();

        const tbody = document.querySelector('#registry-table tbody');
        if (!tbody) return;

        if (data.documents && data.documents.length > 0) {
            tbody.innerHTML = data.documents.map(doc => `
                <tr>
                    <td>${doc.id}</td>
                    <td>${doc.name}</td>
                    <td>${doc.category || '-'}</td>
                    <td>
                        <span class="badge badge-${getStatusBadge(doc.status)}">
                            ${getStatusText(doc.status)}
                        </span>
                    </td>
                    <td>${doc.expiry_date || '-'}</td>
                    <td>
                        <button class="btn btn-outline" onclick="viewDocument('${doc.id}')">
                            Просмотр
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--gray-500);">Документы не найдены</td></tr>';
        }

    } catch (error) {
        console.error('Error loading registry:', error);
    }
}

function getStatusBadge(status) {
    const badges = {
        'valid': 'success',
        'expiring_soon_30d': 'warning',
        'expiring_soon_7d': 'warning',
        'expired': 'danger',
        'unknown': 'info'
    };
    return badges[status] || 'info';
}

function getStatusText(status) {
    const texts = {
        'valid': 'Действующий',
        'expiring_soon_30d': 'Истекает',
        'expiring_soon_7d': 'Срочно',
        'expired': 'Истек',
        'unknown': 'Неизвестно'
    };
    return texts[status] || status;
}

// ===================== Control Stages =====================

async function loadControlStages() {
    const container = document.getElementById('control-stages');
    if (!container) return;

    try {
        const response = await fetch(`${API_BASE}/control/checklists`);
        const checklists = await response.json();

        container.innerHTML = Object.entries(checklists).map(([stageName, checklist], index) => {
            const checked = checklist.filter(item => item.checked).length;
            const total = checklist.length;
            const progress = total > 0 ? Math.round(checked / total * 100) : 0;

            let statusClass = 'pending';
            if (progress === 100) statusClass = 'passed';
            else if (progress > 0) statusClass = 'warning';

            return `
                <div class="control-stage">
                    <div class="stage-header" onclick="toggleStage(this)">
                        <div class="stage-info">
                            <div class="stage-icon ${statusClass}">${index + 1}</div>
                            <div>
                                <div class="stage-name">${stageName}</div>
                                <div class="stage-status">${checked}/${total} пунктов выполнено</div>
                            </div>
                        </div>
                        <span>${progress}%</span>
                    </div>
                    <div class="stage-content">
                        <ul class="checklist">
                            ${checklist.map(item => `
                                <li class="checklist-item">
                                    <input type="checkbox" class="checklist-checkbox"
                                           ${item.checked ? 'checked' : ''}
                                           ${item.is_automatic ? 'disabled' : ''}
                                           onchange="updateChecklistItem(${index}, '${item.id}', this.checked)">
                                    <span class="checklist-text ${item.severity === 'critical' ? 'critical' : ''}">
                                        ${item.description}
                                        ${item.severity === 'critical' ? ' <span class="badge badge-danger">Критично</span>' : ''}
                                    </span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading control stages:', error);
        container.innerHTML = '<p class="text-muted">Ошибка загрузки чек-листов</p>';
    }
}

function toggleStage(header) {
    const content = header.nextElementSibling;
    content.classList.toggle('expanded');
}

async function updateChecklistItem(stageIndex, itemId, checked) {
    try {
        await fetch(`${API_BASE}/control/checklists/${stageIndex}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                item_id: itemId,
                checked: checked,
                user_id: 'web_user',
                user_name: 'Веб-пользователь'
            })
        });

        showToast('success', checked ? 'Пункт отмечен' : 'Отметка снята');

    } catch (error) {
        console.error('Error updating checklist:', error);
        showToast('error', 'Ошибка обновления чек-листа');
    }
}

// ===================== Reports & Analytics =====================

async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/reports/analytics`);
        const data = await response.json();

        document.getElementById('stat-total').textContent = data.total_procurements || 0;
        document.getElementById('stat-success').textContent = `${data.success_rate || 0}%`;
        document.getElementById('stat-time').textContent = `${data.average_preparation_time || 0}ч`;

    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function generateReport(type) {
    showToast('info', `Генерация отчета: ${type}`);
    // TODO: Implement report generation
}

// ===================== Utilities =====================

function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.toggle('active', show);
}

function showToast(type, message) {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${getToastIcon(type)}
        </svg>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getToastIcon(type) {
    const icons = {
        'success': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        'error': '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        'warning': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        'info': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
    };
    return icons[type] || icons.info;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export button handler
document.getElementById('export-btn')?.addEventListener('click', () => {
    if (analysisResult) {
        const dataStr = JSON.stringify(analysisResult, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'analysis_result.json';
        a.click();
        URL.revokeObjectURL(url);
        showToast('success', 'Результаты экспортированы');
    }
});

// Add document button handler
document.getElementById('add-doc-btn')?.addEventListener('click', () => {
    showToast('info', 'Функция в разработке');
});

// Make functions globally available
window.showPage = showPage;
window.toggleStage = toggleStage;
window.updateChecklistItem = updateChecklistItem;
window.generateReport = generateReport;
window.viewDocument = (id) => showToast('info', `Просмотр документа: ${id}`);
