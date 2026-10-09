const state = {
    isDataLoaded: false,
    filters: { logic: 'AND' },
    page: 1,
    perPage: 25,
    sortCol: 'Date',
    sortDesc: true,
    totalPages: 1,
    transactions: []
};

const app = {
    init() {
        this.cacheDOM();
        this.bindEvents();
        this.checkDataStatus();
        this.loadSavedSearches();
    },

    cacheDOM() {
        // Navigation
        this.navItems = document.querySelectorAll('.nav-item');
        this.views = document.querySelectorAll('.view');
        this.viewTitle = document.getElementById('current-view-title');
        this.menuToggle = document.getElementById('menu-toggle');
        this.sidebar = document.getElementById('sidebar');
        
        // Upload
        this.dropZone = document.getElementById('drop-zone');
        this.fileInput = document.getElementById('file-input');
        this.uploadProgress = document.getElementById('upload-progress');
        this.statusIndicator = document.getElementById('upload-status');
        
        // Filter
        this.searchForm = document.getElementById('search-form');
        this.filterToggle = document.getElementById('filter-toggle');
        this.filterBody = document.getElementById('filter-body');
        this.logicToggle = document.getElementById('logic-toggle');
        this.logicLabel = document.getElementById('logic-label');
        
        // Tables
        this.txTableBody = document.getElementById('transactions-body');
        this.custTableBody = document.getElementById('customers-body');
        this.pagination = document.getElementById('pagination-controls');
        this.resultsInfo = document.getElementById('results-info');
        
        // Modals
        this.txModal = document.getElementById('tx-modal');
        this.saveModal = document.getElementById('save-search-modal');
        this.txModalBody = document.getElementById('tx-modal-body');
    },

    bindEvents() {
        // Navigation
        this.navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                if (!item.style.display || item.style.display !== 'none') {
                    const target = item.getAttribute('data-target');
                    this.navigateTo(target.split('-')[0]);
                }
            });
        });

        this.menuToggle.addEventListener('click', () => {
            this.sidebar.classList.toggle('open');
        });

        // Upload
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });
        this.dropZone.addEventListener('dragleave', () => {
            this.dropZone.classList.remove('dragover');
        });
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this.handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        // Filter Form
        this.filterToggle.addEventListener('click', () => {
            this.filterToggle.classList.toggle('collapsed');
            this.filterBody.classList.toggle('collapsed');
        });

        this.logicToggle.addEventListener('change', (e) => {
            this.logicLabel.textContent = e.target.checked ? 'AND' : 'OR';
            state.filters.logic = e.target.checked ? 'AND' : 'OR';
        });

        this.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.applyFilters();
        });

        document.getElementById('btn-clear').addEventListener('click', () => {
            this.searchForm.reset();
            this.logicToggle.checked = true;
            this.logicLabel.textContent = 'AND';
            state.filters = { logic: 'AND' };
            this.fetchTransactions();
        });

        document.getElementById('btn-save-search').addEventListener('click', () => {
            this.saveModal.classList.add('active');
        });

        document.getElementById('btn-confirm-save').addEventListener('click', () => {
            this.saveSearch();
        });

        // Sorting
        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.getAttribute('data-sort');
                if (state.sortCol === col) {
                    state.sortDesc = !state.sortDesc;
                } else {
                    state.sortCol = col;
                    state.sortDesc = true;
                }
                
                document.querySelectorAll('th i.fa-sort, th i.fa-sort-up, th i.fa-sort-down').forEach(i => {
                    i.className = 'fas fa-sort';
                });
                th.querySelector('i').className = state.sortDesc ? 'fas fa-sort-down' : 'fas fa-sort-up';
                
                this.fetchTransactions();
            });
        });

        // Export
        document.getElementById('btn-export-csv').addEventListener('click', () => this.exportData('csv'));
        document.getElementById('btn-export-excel').addEventListener('click', () => this.exportData('excel'));

        // Modals Close
        document.getElementById('close-tx-modal').addEventListener('click', () => this.txModal.classList.remove('active'));
        document.getElementById('close-save-modal').addEventListener('click', () => this.saveModal.classList.remove('active'));
        
        window.addEventListener('click', (e) => {
            if (e.target === this.txModal) this.txModal.classList.remove('active');
            if (e.target === this.saveModal) this.saveModal.classList.remove('active');
        });
    },

    navigateTo(viewName) {
        if (!state.isDataLoaded && viewName !== 'upload') {
            this.showToast('Please upload a file first', 'error');
            return;
        }

        this.navItems.forEach(item => item.classList.remove('active'));
        const activeNav = document.querySelector(`.nav-item[data-target="${viewName}-view"]`);
        if(activeNav) activeNav.classList.add('active');

        this.views.forEach(view => view.classList.remove('active'));
        document.getElementById(`${viewName}-view`).classList.add('active');

        const titles = {
            'upload': 'Upload Data',
            'dashboard': 'Dashboard',
            'transactions': 'Transactions',
            'customers': 'Customer Analytics'
        };
        this.viewTitle.textContent = titles[viewName];

        if (window.innerWidth <= 768) {
            this.sidebar.classList.remove('open');
        }

        if (viewName === 'dashboard') this.fetchDashboardStats();
        if (viewName === 'transactions') this.fetchTransactions();
        if (viewName === 'customers') this.fetchCustomers();
    },

    async checkDataStatus() {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                const data = await res.json();
                if (data.total_transactions > 0) {
                    this.setDataLoadedStatus();
                    this.navigateTo('dashboard');
                } else {
                    this.logicToggle.checked = true;
                }
            }
        } catch (e) {
            console.log("No data loaded yet.");
        }
    },

    setDataLoadedStatus() {
        state.isDataLoaded = true;
        document.getElementById('nav-dashboard').style.display = 'flex';
        document.getElementById('nav-transactions').style.display = 'flex';
        document.getElementById('nav-customers').style.display = 'flex';
        
        this.statusIndicator.innerHTML = '<span class="status-indicator success"></span> Data Loaded';
    },

    async handleFileUpload(file) {
        const allowed = ['.csv', '.xlsx', '.xls', '.tsv', '.txt'];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowed.includes(ext) && file.name.includes('.')) {
            this.showToast('Supported formats: CSV, Excel (.xlsx, .xls), TSV, TXT', 'error');
            return;
        }

        this.dropZone.classList.add('hidden');
        this.uploadProgress.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (res.ok && data.success) {
                this.showToast(`Success! Loaded ${data.row_count} transactions.`, 'success');
                this.setDataLoadedStatus();
                this.navigateTo('dashboard');
            } else {
                this.showToast(data.error || data.details || 'Upload failed', 'error');
                this.dropZone.classList.remove('hidden');
                this.uploadProgress.classList.add('hidden');
            }
        } catch (error) {
            this.showToast('Network error during upload', 'error');
            this.dropZone.classList.remove('hidden');
            this.uploadProgress.classList.add('hidden');
        }
    },

    async fetchDashboardStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            
            document.getElementById('stat-total-tx').textContent = this.formatNumber(data.total_transactions);
            document.getElementById('stat-credit').textContent = this.formatCurrency(data.total_credit);
            document.getElementById('stat-debit').textContent = this.formatCurrency(data.total_debit);
            document.getElementById('stat-fees').textContent = this.formatCurrency(data.total_fees);
            document.getElementById('stat-net').textContent = this.formatCurrency(data.net_balance);
        } catch (error) {
            this.showToast('Failed to load dashboard stats', 'error');
        }
    },

    quickSearch() {
        const keyword = document.getElementById('quick-keyword').value;
        if(keyword) {
            this.searchForm.reset();
            this.searchForm.elements['keyword'].value = keyword;
            state.filters = { keyword, logic: 'AND' };
            this.navigateTo('transactions');
        }
    },

    applyFilters() {
        const formData = new FormData(this.searchForm);
        const filters = {};
        
        for (let [key, value] of formData.entries()) {
            if (value && key !== 'logic_toggle') {
                filters[key] = value;
            }
        }
        
        state.filters = filters;
        state.filters.logic = document.getElementById('logic-toggle').checked ? 'AND' : 'OR';
        state.page = 1;
        
        this.fetchTransactions();
    },

    async fetchTransactions() {
        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filters: state.filters,
                    logic: state.filters.logic,
                    page: state.page,
                    per_page: state.perPage
                })
            });
            const data = await res.json();
            
            state.transactions = data.results;
            state.totalPages = data.pages;
            
            this.renderTransactions(data);
            this.renderPagination(data);
        } catch (error) {
            this.showToast('Failed to fetch transactions', 'error');
        }
    },

    renderTransactions(data) {
        this.txTableBody.innerHTML = '';
        
        if (data.results.length === 0) {
            this.txTableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No transactions found</td></tr>';
            this.resultsInfo.textContent = 'Showing 0 results';
            return;
        }

        const start = ((data.page - 1) * data.per_page) + 1;
        const end = Math.min(start + data.results.length - 1, data.total);
        this.resultsInfo.textContent = `Showing ${start}-${end} of ${data.total} results`;

        data.results.forEach((tx, idx) => {
            const tr = document.createElement('tr');
            
            let debit = tx.Debit ? parseFloat(tx.Debit.toString().replace(/,/g, '')) : 0;
            let credit = tx.Credit ? parseFloat(tx.Credit.toString().replace(/,/g, '')) : 0;

            tr.innerHTML = `
                <td>${this.formatDate(tx.Date)}</td>
                <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">${tx.Description || '-'}</td>
                <td>${tx.Reference || '-'}</td>
                <td class="${debit > 0 ? 'text-danger' : ''}">${debit > 0 ? this.formatCurrency(debit) : '-'}</td>
                <td class="${credit > 0 ? 'text-success' : ''}">${credit > 0 ? this.formatCurrency(credit) : '-'}</td>
                <td>${this.formatCurrency(tx.Balance)}</td>
            `;
            
            tr.addEventListener('click', () => this.showTransactionDetails(tx));
            this.txTableBody.appendChild(tr);
        });
    },

    renderPagination(data) {
        this.pagination.innerHTML = '';
        if (data.pages <= 1) return;

        const maxButtons = 5;
        let startPage = Math.max(1, data.page - Math.floor(maxButtons / 2));
        let endPage = Math.min(data.pages, startPage + maxButtons - 1);

        if (endPage - startPage + 1 < maxButtons) {
            startPage = Math.max(1, endPage - maxButtons + 1);
        }

        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.disabled = data.page === 1;
        prevBtn.onclick = () => { state.page--; this.fetchTransactions(); };
        this.pagination.appendChild(prevBtn);

        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.className = `page-btn ${i === data.page ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => { state.page = i; this.fetchTransactions(); };
            this.pagination.appendChild(btn);
        }

        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-btn';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.disabled = data.page === data.pages;
        nextBtn.onclick = () => { state.page++; this.fetchTransactions(); };
        this.pagination.appendChild(nextBtn);
    },

    showTransactionDetails(tx) {
        this.txModalBody.innerHTML = '';
        const grid = document.createElement('div');
        grid.className = 'tx-detail-grid';

        const fields = ['Date', 'Description', 'Account number', 'Reference', 'Debit', 'Credit', 'Balance', 'Fee'];
        
        fields.forEach(field => {
            if (tx[field]) {
                const item = document.createElement('div');
                item.className = 'tx-detail-item';
                
                let val = tx[field];
                if (['Debit', 'Credit', 'Balance', 'Fee'].includes(field)) {
                    val = this.formatCurrency(val);
                } else if (field === 'Date') {
                    val = this.formatDate(val) + (val.includes(' ') ? ' ' + val.split(' ')[1] : '');
                }

                item.innerHTML = `
                    <span class="tx-detail-label">${field}</span>
                    <span class="tx-detail-value">${val}</span>
                `;
                grid.appendChild(item);
            }
        });

        this.txModalBody.appendChild(grid);
        this.txModal.classList.add('active');
    },

    async fetchCustomers() {
        try {
            const res = await fetch('/api/customers');
            const data = await res.json();
            
            this.custTableBody.innerHTML = '';
            
            const customers = data.customers || data || [];
            if (!customers || customers.length === 0) {
                this.custTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No customers found</td></tr>';
                return;
            }

            customers.forEach(cust => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 500;">${cust.customer_name || 'Unknown'}</td>
                    <td>${this.formatNumber(cust.transaction_count)}</td>
                    <td class="text-success">${this.formatCurrency(cust.total_amount)}</td>
                    <td>${this.formatDate(cust.last_transaction_date)}</td>
                `;
                this.custTableBody.appendChild(tr);
            });
        } catch (error) {
            this.showToast('Failed to load customers', 'error');
        }
    },

    async saveSearch() {
        const nameInput = document.getElementById('save-search-name');
        const name = nameInput.value.trim();
        if (!name) {
            this.showToast('Please enter a name', 'warning');
            return;
        }

        try {
            const res = await fetch('/api/saved-searches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    filters: state.filters,
                    logic: state.filters.logic || 'AND'
                })
            });
            const data = await res.json();
            
            if (data.success) {
                this.showToast('Search saved!', 'success');
                this.saveModal.classList.remove('active');
                nameInput.value = '';
                this.loadSavedSearches();
            }
        } catch (error) {
            this.showToast('Failed to save search', 'error');
        }
    },

    async loadSavedSearches() {
        try {
            const res = await fetch('/api/saved-searches');
            if (!res.ok) return;
            const data = await res.json();
            
            const container = document.getElementById('saved-searches-container');
            container.innerHTML = '';
            
            const searches = data.searches || data || [];
            if (searches && searches.length > 0) {
                searches.forEach(search => {
                    const chip = document.createElement('div');
                    chip.className = 'chip';
                    chip.innerHTML = `
                        <i class="fas fa-search" style="font-size: 0.75rem;"></i>
                        <span class="chip-text">${search.name}</span>
                        <button class="chip-delete"><i class="fas fa-times"></i></button>
                    `;
                    
                    chip.querySelector('.chip-text').addEventListener('click', () => {
                        this.applySavedSearch(search);
                    });
                    
                    chip.querySelector('.chip-delete').addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.deleteSavedSearch(search.id);
                    });
                    
                    container.appendChild(chip);
                });
            }
        } catch (e) {
            console.log("Could not load saved searches");
        }
    },

    applySavedSearch(search) {
        state.filters = search.filters;
        state.filters.logic = search.logic;
        
        this.searchForm.reset();
        for (let key in search.filters) {
            if (this.searchForm.elements[key]) {
                this.searchForm.elements[key].value = search.filters[key];
            }
        }
        
        this.logicToggle.checked = search.logic === 'AND';
        this.logicLabel.textContent = search.logic;
        
        this.fetchTransactions();
    },

    async deleteSavedSearch(id) {
        try {
            const res = await fetch(`/api/saved-searches/${id}`, { method: 'DELETE' });
            if (res.ok) {
                this.loadSavedSearches();
                this.showToast('Saved search deleted', 'success');
            }
        } catch (error) {
            this.showToast('Failed to delete search', 'error');
        }
    },

    exportData(type) {
        const queryParams = new URLSearchParams();
        
        for (let key in state.filters) {
            if (state.filters[key]) {
                queryParams.append(key, state.filters[key]);
            }
        }
        
        if (state.filters.logic) {
            queryParams.append('logic', state.filters.logic);
        }

        window.location.href = `/api/export/${type}?${queryParams.toString()}`;
    },

    formatCurrency(val) {
        if (!val && val !== 0) return 'KSh 0.00';
        let num = typeof val === 'string' ? parseFloat(val.replace(/,/g, '')) : val;
        if (isNaN(num)) return val;
        return 'KSh ' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },

    formatNumber(val) {
        if (!val && val !== 0) return '0';
        return parseInt(val).toLocaleString('en-US');
    },

    formatDate(dateStr) {
        if (!dateStr) return '-';
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            return `${d.getDate().toString().padStart(2, '0')} ${months[d.getMonth()]} ${d.getFullYear()}`;
        } catch(e) {
            return dateStr;
        }
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'exclamation-circle';
        if (type === 'warning') icon = 'exclamation-triangle';
        
        toast.innerHTML = `<i class="fas fa-${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => {
                if(container.contains(toast)) container.removeChild(toast);
            }, 300);
        }, 3000);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
