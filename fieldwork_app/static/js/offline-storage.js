// offline-storage.js - Локальное хранилище для offline режима

class OfflineStorage {
    constructor() {
        this.db = null;
        this.initDB();
    }

    initDB() {
        // IndexedDB инициализация для надежного хранилища больших объемов
        const request = indexedDB.open('FieldworkDB', 1);

        request.onerror = () => {
            console.error('Failed to open IndexedDB');
            this.useLocalStorage = true;
        };

        request.onsuccess = (event) => {
            this.db = event.target.result;
        };

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains('workRequests')) {
                db.createObjectStore('workRequests', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('workResults')) {
                db.createObjectStore('workResults', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('workPhotos')) {
                db.createObjectStore('workPhotos', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('workDocuments')) {
                db.createObjectStore('workDocuments', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('syncQueue')) {
                db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
            }
        };
    }

    // Сохранение данных в IndexedDB
    async saveToIndexedDB(storeName, data) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                reject('Database not initialized');
                return;
            }

            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(data);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(data);
        });
    }

    // Получение данных из IndexedDB
    async getFromIndexedDB(storeName, id) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                reject('Database not initialized');
                return;
            }

            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(id);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    // Получение всех данных из хранилища
    async getAllFromIndexedDB(storeName) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                reject('Database not initialized');
                return;
            }

            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    // Добавление в очередь синхронизации
    async addToSyncQueue(entityType, entityId, data, action = 'create') {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                reject('Database not initialized');
                return;
            }

            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            
            const queueItem = {
                entityType,
                entityId,
                data,
                action,
                timestamp: new Date().toISOString(),
                synced: false
            };

            const request = store.add(queueItem);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(queueItem);
        });
    }

    // Получение очереди синхронизации
    async getSyncQueue() {
        const queue = await this.getAllFromIndexedDB('syncQueue');
        return queue.filter(item => !item.synced);
    }

    // Удаление элемента из очереди
    async removeFromSyncQueue(id) {
        return new Promise((resolve, reject) => {
            if (!this.db) {
                reject('Database not initialized');
                return;
            }

            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            const request = store.delete(id);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    // Сохранение файла локально (для мобильных устройств)
    async saveFileLocally(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const fileData = {
                    id: this.generateUUID(),
                    name: file.name,
                    type: file.type,
                    size: file.size,
                    data: e.target.result,
                    timestamp: new Date().toISOString()
                };

                localStorage.setItem(`file_${fileData.id}`, JSON.stringify(fileData));
                resolve(fileData.id);
            };

            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    }

    // Получение сохраненного файла
    getFileLocally(fileId) {
        const fileData = localStorage.getItem(`file_${fileId}`);
        return fileData ? JSON.parse(fileData) : null;
    }

    // Кэширование API ответов
    cacheAPIResponse(key, data, ttl = 3600000) { // 1 час по умолчанию
        const cacheData = {
            data,
            timestamp: Date.now(),
            ttl
        };
        localStorage.setItem(`cache_${key}`, JSON.stringify(cacheData));
    }

    // Получение кэшированного ответа
    getCachedAPIResponse(key) {
        const cached = localStorage.getItem(`cache_${key}`);
        if (!cached) return null;

        const { data, timestamp, ttl } = JSON.parse(cached);
        if (Date.now() - timestamp > ttl) {
            localStorage.removeItem(`cache_${key}`);
            return null;
        }

        return data;
    }

    // Очистка кэша
    clearCache() {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith('cache_')) {
                localStorage.removeItem(key);
            }
        });
    }

    // Генерация UUID
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Получение статистики хранилища
    async getStorageStats() {
        const stats = {
            workRequests: (await this.getAllFromIndexedDB('workRequests')).length,
            workResults: (await this.getAllFromIndexedDB('workResults')).length,
            workPhotos: (await this.getAllFromIndexedDB('workPhotos')).length,
            workDocuments: (await this.getAllFromIndexedDB('workDocuments')).length,
            syncQueueSize: (await this.getSyncQueue()).length
        };
        return stats;
    }

    // Очистка всех данных
    async clearAllData() {
        const stores = ['workRequests', 'workResults', 'workPhotos', 'workDocuments', 'syncQueue'];
        
        for (const store of stores) {
            await new Promise((resolve, reject) => {
                if (!this.db) {
                    reject('Database not initialized');
                    return;
                }

                const transaction = this.db.transaction([store], 'readwrite');
                const objectStore = transaction.objectStore(store);
                const request = objectStore.clear();

                request.onerror = () => reject(request.error);
                request.onsuccess = () => resolve();
            });
        }
    }
}

// Инициализация глобального объекта
const offlineStorage = new OfflineStorage();
