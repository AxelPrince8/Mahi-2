from flask import Flask, render_template, request, jsonify
import threading, time, requests, os, uuid, json, datetime
import sys

app = Flask(__name__)

MASTER_PASSWORD = "Axel67"
TASKS_FILE = "tasks.json"
tasks = {}
URL = "https://mahi-2-42k5.onrender.com"

def log_event(msg):
    with open("restart_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")
    print(msg)

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for task_id, config in data.items():
                tasks[task_id] = {"running": True, "thread": None, "config": config}
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
    cookies_list = config["cookies"]
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
            for cookie_string in cookies_list:
                try:
                    url = f"https://graph.facebook.com/v15.0/t_{convo_id}"
                    payload = {"message": f"{haters_name} {msg}"}
                    headers = {"Cookie": cookie_string}

                    # 🔹 DEBUG logs
                    log_event(f"[DEBUG {task_id}] Sending message: {msg[:30]}... with cookie: {cookie_string[:20]}...")

                    r = requests.post(url, data=payload, headers=headers)

                    log_event(f"[DEBUG {task_id}] Response code: {r.status_code} | Response text: {r.text[:100]}")

                    count += 1
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
        cookies_list = []
        if token_option == "single":
            single_cookie = request.form.get("singleToken")
            if single_cookie:
                cookies_list = [single_cookie.strip()]
        else:
            cookie_file = request.files.get("tokenFile")
            if cookie_file:
                content = cookie_file.read().decode("utf-8")
                cookies_list = [c.strip() for c in content.splitlines() if c.strip()]

        convo_id = request.form.get("threadId")
        haters_name = request.form.get("kidx")
        delay = request.form.get("time")

        txt_file = request.files.get("txtFile")
        np_path = f"np_{uuid.uuid4().hex}.txt"
        if txt_file:
            txt_file.save(np_path)

        config = {
            "cookies": cookies_list,
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
            np_file = tasks[task_id]["config"].get("np_file")
            if np_file and os.path.exists(np_file):
                os.remove(np_file)
            save_tasks()
            return jsonify({"status": f"Task {task_id} stopped"})
        return jsonify({"status": f"No active task with ID {task_id}"})
    except Exception as e:
        return jsonify({"error": str(e)})

# ✅ Add this route for live logs
@app.route("/logs")
def get_logs():
    if os.path.exists("restart_log.txt"):
        with open("restart_log.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            # return last 200 lines for performance
            return "".join(lines[-200:])
    return ""

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
    os.execv(sys.executable, [sys.executable] + sys.argv)

threading.Thread(target=monitor_server, daemon=True).start()

if __name__ == "__main__":
    log_event("🚀 Server started successfully")
    load_tasks()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
