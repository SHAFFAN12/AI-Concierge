export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    timestamp: number;
}

const DB_NAME = "AIConciergeDB";
const STORE_NAME = "chat_history";
const DB_VERSION = 1;

export const initDB = (): Promise<IDBDatabase> => {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = (event) => {
            console.error("IndexedDB error:", event);
            reject("Error opening database");
        };

        request.onsuccess = (event) => {
            resolve((event.target as IDBOpenDBRequest).result);
        };

        request.onupgradeneeded = (event) => {
            const db = (event.target as IDBOpenDBRequest).result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: "timestamp" });
            }
        };
    });
};

export const saveMessage = async (message: ChatMessage) => {
    try {
        const db = await initDB();
        return new Promise<void>((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readwrite");
            const store = tx.objectStore(STORE_NAME);
            const request = store.put(message);

            request.onsuccess = () => resolve();
            request.onerror = () => reject("Error saving message");

            tx.oncomplete = () => resolve();
            tx.onerror = () => reject("Transaction error");
        });
    } catch (error) {
        console.error("Error saving message:", error);
    }
};

export const getHistory = async (): Promise<ChatMessage[]> => {
    try {
        const db = await initDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readonly");
            const store = tx.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onsuccess = () => {
                // Sort by timestamp just in case
                const results = request.result as ChatMessage[];
                results.sort((a, b) => a.timestamp - b.timestamp);
                resolve(results);
            };

            request.onerror = () => {
                reject("Error fetching history");
            };
        });
    } catch (error) {
        console.error("Error getting history:", error);
        return [];
    }
};

export const clearHistory = async () => {
    try {
        const db = await initDB();
        const tx = db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        store.clear();
    } catch (error) {
        console.error("Error clearing history:", error);
    }
};
