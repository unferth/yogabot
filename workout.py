import datetime, os, re, sys, time, csv, pyttsx3
from multiprocessing import Process

CHOSEN_VOICE = 0
last_trigger, file_mod_time, blocks, active_log = "", 0.0, {}, []
is_workout_active = is_prompt_active = False
h_title, h_duration, h_status = "none", "0m", "n/a"

FOL = sys.argv[1] if len(sys.argv) > 1 else ""
if FOL and not os.path.exists(FOL): os.makedirs(FOL)
LOG = os.path.join(FOL, "habit_log.csv") if FOL else "habit_log.csv"

def _spk_worker(txt, v_idx):
    try:
        eng = pyttsx3.init()
        eng.setProperty('rate', 165)
        voices = eng.getProperty('voices')
        if len(voices) > v_idx: eng.setProperty('voice', voices[v_idx].id)
        eng.say(txt); eng.runAndWait()
    except: pass

def speak(txt, only_v=False, c_down=""):
    if txt and not only_v and is_workout_active:
        active_log.append(txt)
        if len(active_log) > 12: active_log.pop(0)
    show(c_down)
    if txt:
        p = Process(target=_spk_worker, args=(txt, CHOSEN_VOICE))
        p.start(); p.join()

def get_habit_stats():
    if not os.path.exists(LOG): return "0% completion (0 day streak)"
    try:
        with open(LOG, 'r', encoding='utf-8') as f:
            rws = [r for r in csv.reader(f) if len(r) >= 4][1:]
        if not rws: return "0% completion (0 day streak)"
        comp = sum(1 for r in rws if r[3] in ["COMPLETED", "YES", "yes", "AUTO_EXECUTED"])
        streak = 0
        for r in reversed(rws):
            if r[3] in ["COMPLETED", "YES", "yes", "AUTO_EXECUTED"]: streak += 1
            else: break
        return f"{int((comp / len(rws)) * 100)}% completion ({streak} streak)"
    except: return "stats loading..."

def log_h(t_str, title, status):
    ex = os.path.exists(LOG)
    with open(LOG, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if not ex: w.writerow(["Timestamp", "Scheduled Time", "Routine Title", "Status"])
        w.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t_str, title, status])

def format_countdown(sec):
    if sec <= 0: return "0 seconds"
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    p = []
    if h: p.append(f"{h} hour{'s' if h != 1 else ''}")
    if m: p.append(f"{m} minute{'s' if m != 1 else ''}")
    if s or not p: p.append(f"{s} second{'s' if s != 1 else ''}")
    return " ".join(p)

def show(nxt):
    os.system('cls' if os.name == 'nt' else 'clear')
    now = datetime.datetime.now()
    suff = 'th' if 11<=now.day<=13 else {1:'st',2:'nd',3:'rd'}.get(now.day%10, 'th')
    print(now.strftime(f"%A {now.day}{suff} of %B, %Y").lower() + (f" [profile: {FOL}]" if FOL else ""))
    print(now.strftime("%I:%M %p").lower().lstrip('0') + f"\nwatching file: {f_path}\n")
    if is_workout_active:
        for l in active_log: print(l)
    else:
        print(f"previous workout: {h_title} ({h_duration}), completed: {h_status} | stats: {get_habit_stats()}\n{nxt}")
    sys.stdout.flush()

def parse_txt(file):
    global file_mod_time, blocks
    if not file or not os.path.exists(file): blocks.clear(); return
    mtime = os.path.getmtime(file)
    if mtime == file_mod_time: return
    file_mod_time, blocks, cur_t = mtime, {}, None
    with open(file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            nw = "(nowait)" in line.lower()
            line = re.sub(r'\(nowait\)', '', line, flags=re.IGNORECASE).strip()
            m = re.match(r'^(\d+):?(\d*)\s*(am|pm)\s*(.*)$', line, re.IGNORECASE)
            if m:
                h, m_val, p, t = int(m.group(1)), m.group(2), m.group(3).lower(), m.group(4).strip()
                mn = int(m_val) if m_val else 0
                if p == 'pm' and h != 12: h += 12
                if p == 'am' and h == 12: h = 0
                cur_t = f"{h:02d}:{mn:02d}"
                blocks[cur_t] = {"title": t or "workout", "nowait": nw, "disp": f"{h-12 if h>12 else (12 if h==0 else h)}{f':{mn:02d}' if mn else ''} {p}", "steps": []}
            elif cur_t and line.startswith('['):
                sm = re.match(r'^\[(\d+)(s|m)?\]\s*(.*)', line, re.IGNORECASE)
                if sm:
                    v, u = int(sm.group(1)), sm.group(2).lower() if sm.group(2) else 's'
                    blocks[cur_t]["steps"].append((v * 60 if u == 'm' else v, sm.group(3)))

def run_block(bk, t_str):
    global h_title, h_duration, h_status, active_log, is_workout_active
    tot = sum(s[0] for s in bk["steps"])
    active_log, is_workout_active = [], True
    speak(f"{bk['disp']} {bk['title']} starting")
    for sec, inst in bk["steps"]:
        speak(inst)
        half = sec // 2
        for r in range(sec, 0, -1):
            if active_log:
                # FIXED: Extracted the regex clean step to keep backslashes completely outside the f-string loop
                clean_text = re.sub(r'\s*\[[^\]]+\]$', '', active_log[-1])
                time_display = f"{r//60}m {r%60}s" if r >= 60 else f"{r}s"
                active_log[-1] = f"{clean_text} [{time_display}]"
            if sec > 45 and r == half: speak("halfway there", only_v=True)
            elif r == 5 and sec > 6: speak("5 seconds remaining", only_v=True)
            else: show(""); time.sleep(1)
        if active_log: active_log[-1] = re.sub(r'\s*\[[^\]]+\]$', '', active_log[-1])
    speak("workout complete.")
    log_h(t_str, bk["title"], "COMPLETED")
    h_title, h_duration, h_status, is_workout_active = bk["title"], f"{tot//60}m" if tot>=60 else f"{tot}s", "yes", False

def prompt(t_str, bk):
    global h_title, h_duration, h_status, is_prompt_active
    if bk["nowait"]: run_block(bk, t_str); return
    is_prompt_active = True
    ann = f"{bk['disp']} {bk['title']} starting"
    speak(ann, c_down=f"alert: {ann}")
    while True:
        for a in range(3):
            if a > 0: speak(ann, c_down="checking in again...")
            show("pending verification: press y to execute / n to skip")
            start = time.time()
            res = None
            while time.time() - start < 300:
                if importlib.import_module('msvcrt').kbhit(): res = importlib.import_module('msvcrt').getwche().lower(); break
                time.sleep(0.05)
            if res == 'y': run_block(bk, t_str); is_prompt_active = False; return
            elif res == 'n':
                log_h(t_str, bk["title"], "SKIPPED")
                tot = sum(s[0] for s in bk["steps"])
                h_title, h_duration, h_status, is_prompt_active = bk["title"], f"{tot//60}m" if tot>=60 else f"{tot}s", "no", False; return
        log_h(t_str, bk["title"], "MISSED_TIMEOUT")
        tot = sum(s[0] for s in bk["steps"])
        h_title, h_duration, h_status = bk["title"], f"{tot//60}m" if tot>=60 else f"{tot}s", "missed (timeout)"
        while True:
            for _ in range(3600):
                if datetime.datetime.now().strftime("%H:%M") != t_str and datetime.datetime.now().strftime("%H:%M") in blocks: is_prompt_active = False; return
                time.sleep(1)
            speak(f"reminder: {bk['disp']} {bk['title']} is waiting.")
            start = time.time()
            res = None
            while time.time() - start < 5:
                if importlib.import_module('msvcrt').kbhit(): res = importlib.import_module('msvcrt').getwche().lower(); break
                time.sleep(0.05)
            if res == 'y': run_block(bk, t_str); is_prompt_active = False; return
            elif res == 'n': log_h(t_str, bk["title"], "SKIPPED"); h_status, is_prompt_active = "no", False; return

if __name__ == "__main__":
    import importlib
    while True:
        now = datetime.datetime.now()
        c_time, day = now.strftime("%H:%M"), now.strftime('%A').lower()
        opts = [f"{day}.txt", f"{day}workout.txt"]
        f_path = next((os.path.join(FOL, o) if FOL else o for o in opts if os.path.exists(os.path.join(FOL, o) if FOL else o)), "")
        if not f_path: f_path = f"NOT FOUND! Create '{day}.txt' inside: '{FOL if FOL else '.'}'"
        parse_txt(f_path if "NOT FOUND!" not in f_path else "")
        if not is_prompt_active:
            if f_path and blocks:
                up = sorted([t for t in blocks.keys() if t >= c_time])
                if up: nxt_str = f"next workout: {blocks[up[0]]['disp']} {blocks[up[0]]['title']} in {format_countdown(((int(up[0][:2])*60+int(up[0][3:]))-(now.hour*60+now.minute))*60-now.second)}..."
                else: nxt_str = "next workout: tomorrow"
            else: nxt_str = "next workout: no schedule file detected"
            show(nxt_str)
        if blocks and c_time in blocks and c_time != last_trigger: last_trigger = c_time; prompt(c_time, blocks[c_time])
        time.sleep(1)
