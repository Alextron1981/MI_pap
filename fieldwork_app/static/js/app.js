// app.js - Главный файл приложения

class FieldworkApp {
    constructor() {
        this.apiBase = '/api/fieldwork';
        this.token = null;
        this.currentUser = null;
        this.isOnline = navigator.onLine;
        this.syncInterval = null;
        
        this.init();
    }

    async init() {
        // Проверка наличия токена
        this.token = localStorage.getItem('access_token');
        
        if (!this.token) {
            this.showLoginForm();
        } else {
            await this.loadCurrentUser();
            this.setupEventListeners();
            this.setupOnlineOfflineListeners();
            this.startAutoSync();
            this.showSection('dashboard');
            this.loadDashboard();
        }
    }

    // Аутентификация
    showLoginForm() {
        document.body.innerHTML = `
            <div class="login-container">
                <div class="login-box">
                    <h1>📋 Система управления полевыми работами</h1>
                    <form id="login-form">
                        <div class="form-group">
                            <label>Логин</label>
                            <input type="text" id="login-username" required>
                        </div>
                        <div class="form-group">
                            <label>Пароль</label>
                            <input type="password" id="login-password" required>
                        </div>
                        <button type="submit" class="btn-primary">Вход</button>
                    </form>
                    <div id="login-error"></div>
                </div>
                <style>
                    body { background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
                    .login-container { width: 100%; height: 100vh; display: flex; align-items: center; justify-content: center; }
                    .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); width: 90%; max-width: 400px; }
                    .login-box h1 { text-align: center; margin-bottom: 30px; color: #2c3e50; font-size: 24px; }
                    .form-group { margin-bottom: 20px; }
                    .form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
                    .form-group input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
                    .form-group input:focus { outline: none; border-color: #3498db; box-shadow: 0 0 5px rgba(52, 152, 219, 0.3); }
                    .btn-primary { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: 500; }
                    .btn-primary:hover { background: #2980b9; }
                    #login-error { color: #e74c3c; margin-top: 15px; text-align: center; }
                </style>
            </div>
        `;

        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorDiv = document.getElementById('login-error');

        try {
            const response = await fetch(`${this.apiBase}/api/token/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                throw new Error('Invalid credentials');
            }

            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);
            
            this.token = data.access;
            this.currentUser = {
                username: data.username,
                email: data.email,
                full_name: data.full_name,
                role: data.role
            };

            // Перезагрузить страницу
            window.location.reload();
        } catch (error) {
            errorDiv.textContent = 'Ошибка входа. Проверьте логин и пароль.';
        }
    }

    async loadCurrentUser() {
        try {
            const response = await fetch(`${this.apiBase}/employees/current_user/`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.currentUser = data;
            }
        } catch (error) {
            console.error('Error loading user:', error);
        }
    }

    // Управление сетевым статусом
    setupOnlineOfflineListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateSyncStatus();
            this.syncOfflineData();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateSyncStatus();
        });

        // Проверка соединения каждые 5 секунд
        setInterval(() => {
            const wasOnline = this.isOnline;
            this.isOnline = navigator.onLine;
            if (wasOnline !== this.isOnline) {
                this.updateSyncStatus();
                if (this.isOnline) {
                    this.syncOfflineData();
                }
            }
        }, 5000);
    }

    updateSyncStatus() {
        const indicator = document.getElementById('sync-indicator');
        const text = document.getElementById('sync-text');
        
        if (this.isOnline) {
            indicator.className = 'sync-indicator online';
            text.textContent = 'Онлайн';
        } else {
            indicator.className = 'sync-indicator offline';
            text.textContent = 'Offline';
        }
    }

    // Установка обработчиков событий
    setupEventListeners() {
        // Навигация
        document.querySelectorAll('.menu-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.menu-item').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.showSection(e.target.dataset.section);
            });
        });

        // Выход
        document.getElementById('logout-btn')?.addEventListener('click', () => {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.reload();
        });

        // Заявки
        document.getElementById('new-request-btn')?.addEventListener('click', () => {
            document.getElementById('request-modal').style.display = 'block';
        });

        document.getElementById('request-form')?.addEventListener('submit', (e) => this.handleCreateRequest(e));

        document.getElementById('refresh-requests-btn')?.addEventListener('click', () => this.loadWorkRequests());
    }

    // Показать раздел
    showSection(sectionId) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        const section = document.getElementById(sectionId);
        if (section) {
            section.classList.add('active');
        }
    }

    // Загрузка панели управления
    async loadDashboard() {
        const content = document.getElementById('dashboard-content');
        
        try {
            const requests = await this.fetchData('work-requests/my_requests/');
            const stats = await offlineStorage.getStorageStats();

            const dashboardHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
                    <div class="card">
                        <div class="card-header">
                            <h3>Мои заявки</h3>
                        </div>
                        <div style="font-size: 32px; font-weight: bold; color: #3498db;">${requests.length}</div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3>Профиль</h3>
                        </div>
                        <div style="font-size: 14px;">
                            <p><strong>${this.currentUser.user?.first_name || 'Пользователь'}</strong></p>
                            <p>Роль: ${this.getRoleDisplay(this.currentUser.role)}</p>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3>Сохранено offline</h3>
                        </div>
                        <div style="font-size: 14px;">
                            <p>Заявок: ${stats.workRequests}</p>
                            <p>Результатов: ${stats.workResults}</p>
                            <p>К синх.: ${stats.syncQueueSize}</p>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <h3>Состояние сети</h3>
                        </div>
                        <div style="font-size: 14px;">
                            <p>${this.isOnline ? '✅ Онлайн' : '⚠️ Offline режим'}</p>
                            <p style="font-size: 12px; color: #999;">Автосинхронизация: включена</p>
                        </div>
                    </div>
                </div>
            `;

            content.innerHTML = dashboardHTML;
        } catch (error) {
            content.innerHTML = `<div class="alert alert-danger">Ошибка загрузки панели: ${error.message}</div>`;
        }
    }

    // Загрузка заявок
    async loadWorkRequests() {
        const list = document.getElementById('requests-list');
        
        try {
            const requests = await this.fetchData('work-requests/my_requests/');
            
            if (requests.length === 0) {
                list.innerHTML = '<div class="alert alert-info">Нет заявок</div>';
                return;
            }

            let html = '';
            requests.forEach(req => {
                html += `
                    <div class="card">
                        <div class="card-header">
                            <div>
                                <h3 class="card-title">${req.object_address}</h3>
                                <p style="color: #666; font-size: 14px; margin-top: 5px;">${req.work_type}</p>
                            </div>
                            <div style="text-align: right;">
                                <span class="badge badge-${this.getStatusClass(req.status)}">${this.getStatusDisplay(req.status)}</span>
                                <span class="badge badge-${this.getPriorityClass(req.priority)}">${this.getPriorityDisplay(req.priority)}</span>
                            </div>
                        </div>
                        <p style="margin: 10px 0;">${req.description}</p>
                        <p style="font-size: 12px; color: #999;">Дата: ${req.planned_date} | Инженер: ${req.assigned_to_name || 'Не назначен'}</p>
                        <div class="button-group" style="margin-top: 10px;">
                            ${req.status === 'planned' ? `<button class="btn-primary" onclick="app.assignRequest('${req.id}')">Взять заявку</button>` : ''}
                            ${req.status === 'assigned' ? `<button class="btn-success" onclick="app.startWork('${req.id}')">Начать работу</button>` : ''}
                            ${req.status === 'in_progress' ? `<button class="btn-warning" onclick="app.completeWork('${req.id}')">Завершить</button>` : ''}
                            <button class="btn-secondary" onclick="app.viewRequest('${req.id}')">Подробнее</button>
                        </div>
                    </div>
                `;
            });

            list.innerHTML = html;
        } catch (error) {
            list.innerHTML = `<div class="alert alert-danger">Ошибка загрузки заявок: ${error.message}</div>`;
        }
    }

    // Создание новой заявки
    async handleCreateRequest(e) {
        e.preventDefault();

        const formData = {
            work_type: document.getElementById('work_type').value,
            object_address: document.getElementById('object_address').value,
            object_name: document.getElementById('object_name').value,
            planned_date: document.getElementById('planned_date').value,
            description: document.getElementById('description').value,
            priority: document.getElementById('priority').value,
            meter_number: document.getElementById('meter_number').value,
            account_number: document.getElementById('account_number').value,
            contact_person: document.getElementById('contact_person').value,
            contact_phone: document.getElementById('contact_phone').value,
            status: 'planned'
        };

        try {
            if (this.isOnline) {
                const response = await fetch(`${this.apiBase}/work-requests/`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) throw new Error('Error creating request');
                
                const result = await response.json();
                this.showNotification('Заявка создана успешно', 'success');
                
                // Кэшировать результат
                await offlineStorage.saveToIndexedDB('workRequests', result);
            } else {
                // Offline режим - сохранить в очередь синхронизации
                const newId = offlineStorage.generateUUID();
                formData.id = newId;
                
                await offlineStorage.saveToIndexedDB('workRequests', formData);
                await offlineStorage.addToSyncQueue('WorkRequest', newId, formData, 'create');
                
                this.showNotification('Заявка сохранена (будет синхронизирована)', 'warning');
            }

            document.getElementById('request-form').reset();
            closeModal('request-modal');
            this.loadWorkRequests();
        } catch (error) {
            this.showNotification(`Ошибка: ${error.message}`, 'danger');
        }
    }

    // Назначить заявку себе
    async assignRequest(requestId) {
        try {
            const response = await fetch(`${this.apiBase}/work-requests/${requestId}/assign_to_me/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Error assigning request');

            this.showNotification('Заявка назначена вам', 'success');
            this.loadWorkRequests();
        } catch (error) {
            this.showNotification(`Ошибка: ${error.message}`, 'danger');
        }
    }

    // Начать работу
    async startWork(requestId) {
        try {
            const response = await fetch(`${this.apiBase}/work-requests/${requestId}/start_work/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Error starting work');

            this.showNotification('Работа начата', 'success');
            this.loadWorkRequests();
        } catch (error) {
            this.showNotification(`Ошибка: ${error.message}`, 'danger');
        }
    }

    // Завершить работу
    async completeWork(requestId) {
        try {
            const response = await fetch(`${this.apiBase}/work-requests/${requestId}/complete_work/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Error completing work');

            this.showNotification('Работа завершена', 'success');
            this.loadWorkRequests();
        } catch (error) {
            this.showNotification(`Ошибка: ${error.message}`, 'danger');
        }
    }

    // Синхронизация offline данных
    async syncOfflineData() {
        try {
            const queue = await offlineStorage.getSyncQueue();
            
            if (queue.length === 0) return;

            for (const item of queue) {
                try {
                    const response = await fetch(`${this.apiBase}/work-results/sync_offline_data/`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${this.token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            offline_data: [item]
                        })
                    });

                    if (response.ok) {
                        // Отметить как синхронизированное
                        item.synced = true;
                        await offlineStorage.saveToIndexedDB('syncQueue', item);
                    }
                } catch (error) {
                    console.error('Sync error:', error);
                }
            }
        } catch (error) {
            console.error('Sync offline data error:', error);
        }
    }

    // Автоматическая синхронизация
    startAutoSync() {
        this.syncInterval = setInterval(() => {
            if (this.isOnline) {
                this.syncOfflineData();
            }
        }, 30000); // Каждые 30 секунд
    }

    // Загрузка данных через API
    async fetchData(endpoint) {
        const cached = offlineStorage.getCachedAPIResponse(endpoint);
        if (cached && !this.isOnline) {
            return cached;
        }

        const response = await fetch(`${this.apiBase}/${endpoint}`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        offlineStorage.cacheAPIResponse(endpoint, data);
        return data;
    }

    // Вспомогательные функции
    getRoleDisplay(role) {
        const roles = {
            'admin': 'Администратор',
            'coordinator': 'Координатор',
            'engineer': 'Инженер',
            'viewer': 'Просмотрщик'
        };
        return roles[role] || role;
    }

    getStatusDisplay(status) {
        const statuses = {
            'draft': 'Черновик',
            'planned': 'Запланирована',
            'assigned': 'Назначена',
            'in_progress': 'В работе',
            'completed': 'Завершена',
            'cancelled': 'Отменена'
        };
        return statuses[status] || status;
    }

    getStatusClass(status) {
        const classes = {
            'draft': 'primary',
            'planned': 'primary',
            'assigned': 'info',
            'in_progress': 'warning',
            'completed': 'success',
            'cancelled': 'danger'
        };
        return classes[status] || 'primary';
    }

    getPriorityDisplay(priority) {
        const priorities = {
            'low': 'Низкий',
            'normal': 'Обычный',
            'high': 'Высокий',
            'critical': 'Критический'
        };
        return priorities[priority] || priority;
    }

    getPriorityClass(priority) {
        const classes = {
            'low': 'primary',
            'normal': 'primary',
            'high': 'warning',
            'critical': 'danger'
        };
        return classes[priority] || 'primary';
    }

    showNotification(message, type = 'info') {
        const alerts = document.querySelector('.content');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; cursor: pointer; font-size: 20px; color: inherit;">&times;</button>
        `;
        
        if (alerts) {
            alerts.insertBefore(alert, alerts.firstChild);
            setTimeout(() => alert.remove(), 5000);
        }
    }

    viewRequest(requestId) {
        // Реализовать подробный просмотр заявки
        console.log('View request:', requestId);
    }
}

// Глобальные функции
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

window.closeModal = closeModal;

// Инициализация приложения
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new FieldworkApp();
});
