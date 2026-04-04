/**
 * sql_db.js
 * Comprehensive SQLite integration for mobile browsers using sql.js (WASM).
 * This manages the agent's offline vault for results and incidents.
 */

const SQL_DB_CONFIG = {
    locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`
};

let _db = null;

const SQLiteDB = {
    async init() {
        if (_db) return _db;

        try {
            const SQL = await initSqlJs(SQL_DB_CONFIG);

            // Re-use existing binary from IndexedDB if we want persistence across reloads
            // For first version, we'll create a new DB and focus on sync logic.
            // In a production app, we'd store the .sqlite file binary in IndexedDB.
            _db = new SQL.Database();

            // 1. Create Schema
            _db.run(`
                CREATE TABLE IF NOT EXISTS pending_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, -- 'result' or 'incident'
                    payload TEXT NOT NULL, -- JSON stringified
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                );
            `);

            console.log("SQLite Engine Initialized Successfully (Mobile WASM)");
            return _db;
        } catch (err) {
            console.error("SQLite Initialization Failed:", err);
            throw err;
        }
    },

    async saveRecord(type, payload) {
        const db = await this.init();
        const stmt = db.prepare("INSERT INTO pending_records (type, payload) VALUES (?, ?)");
        stmt.run([type, JSON.stringify(payload)]);
        stmt.free();

        // Export state to console for debugging (since it's in-memory for now)
        console.log(`Saved ${type} to SQLite. Current count:`, this.getCount());
        return true;
    },

    async getAllPending() {
        const db = await this.init();
        const res = db.exec("SELECT * FROM pending_records WHERE status = 'pending'");
        if (res.length === 0) return [];

        // Map rows to objects
        const columns = res[0].columns;
        return res[0].values.map(row => {
            const obj = {};
            columns.forEach((col, i) => obj[col] = row[i]);
            obj.payload = JSON.parse(obj.payload);
            return obj;
        });
    },

    async markSynced(id) {
        const db = await this.init();
        db.run("DELETE FROM pending_records WHERE id = ?", [id]);
    },

    getCount() {
        if (!_db) return 0;
        const res = _db.exec("SELECT COUNT(*) FROM pending_records");
        return res[0].values[0][0];
    }
};

window.SQLiteDB = SQLiteDB;
window.initSQLite = SQLiteDB.init.bind(SQLiteDB);
