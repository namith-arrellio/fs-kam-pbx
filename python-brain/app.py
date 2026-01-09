from flask import Flask, jsonify
import mysql.connector
from greenswitch import InboundESL

app = Flask(__name__)

# --- DB connection ---
db = mysql.connector.connect(
    host="127.0.0.1", user="root", password="root", database="voipdb"
)

# --- FreeSWITCH ESL connection ---
fs_conn = InboundESL(host="127.0.0.1", port=8021, password="ClueCon")


@app.route("/fs-status")
def fs_status():
    try:
        if not fs_conn.connected():
            fs_conn.connect()
        info = fs_conn.api("status")
        return jsonify({"status": "connected", "info": info})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/db-test")
def db_test():
    cur = db.cursor()
    cur.execute("SHOW DATABASES;")
    return jsonify({"databases": [r[0] for r in cur.fetchall()]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
