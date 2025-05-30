import { initializeApp } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-app.js";
import { getDatabase, ref, onValue, set, get } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-database.js";

export class FirebaseService {
    static db;
    
    static initialize() {
        const app = initializeApp({
            apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
            authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
            databaseURL: import.meta.env.VITE_FIREBASE_DATABASE_URL,
            projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
            storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
            messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
            appId: import.meta.env.VITE_FIREBASE_APP_ID
        });
        
        this.db = getDatabase(app);
        return this.db;
    }

    static getRef(path) {
        return ref(this.db, path);
    }

    static async getValue(path) {
        const snapshot = await get(this.getRef(path));
        return snapshot.exists() ? snapshot.val() : null;
    }

    static setValue(path, value) {
        return set(this.getRef(path), value);
    }

    static listen(path, callback) {
        return onValue(this.getRef(path), callback);
    }
}