from flask import Flask, render_template, request, session, redirect, url_for, flash
import sqlite3
from datetime import date, timedelta, datetime
import calendar
import random
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect("study.db")
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        subject TEXT,
        minutes INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        subject TEXT,
        goal_minutes INTEGER,
        UNIQUE(username, subject)
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT,
        subject TEXT NOT NULL,
        minutes INTEGER NOT NULL,
        done INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS friends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT NOT NULL,
        to_user TEXT NOT NULL,
        status TEXT NOT NULL,
        UNIQUE(from_user, to_user)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cheers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT NOT NULL,
        to_user TEXT NOT NULL,
        cheer_date TEXT NOT NULL
    )
    """)
    try:
        cursor.execute("""
        ALTER TABLE users
        ADD COLUMN display_name TEXT
        """)
    except:
        pass

    try:
        cursor.execute("""
        ALTER TABLE users
        ADD COLUMN profile_image TEXT
        """)
    except:
        pass

    try:
        cursor.execute("""
        ALTER TABLE users
        ADD COLUMN bio TEXT
        """)
    except:
        pass
    try:
        cursor.execute("""
        ALTER TABLE users
        ADD COLUMN plan TEXT DEFAULT 'free'
        """)
    except:
        pass

    conn.commit()
    conn.close()
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM users
        WHERE username = ?
        """, (username,))

        user = cursor.fetchone()        

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("ユーザー名またはパスワードが違います")
        


    return render_template("login.html")
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT plan
        FROM users
        WHERE username = ?
    """, (session["username"],))

    user_plan = cursor.fetchone()[0]
    cursor.execute("""
    SELECT subject, minutes, done
    FROM plans
    WHERE username = ?
        AND date = date('now')
    ORDER BY id
    """, (session["username"],))

    today_plans = cursor.fetchall()
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())

    cursor.execute("""
    SELECT id, date, subject, minutes
    FROM study_records
    WHERE username = ?
    ORDER BY date DESC
    """, (session["username"],))

    records = cursor.fetchall()

    cursor.execute("""
        SELECT subject
        FROM plans
        WHERE username = ?
            AND date = date('now')
            AND done = 0
        """, (session["username"],))

    today_plan_subjects = [row[0] for row in cursor.fetchall()]

    study_days = set()

    for record in records:
        study_days.add(date.fromisoformat(record[1]))
    streak = 0
    check_day = date.today()
    while check_day in study_days:
        streak += 1
        check_day -= timedelta(days=1)
    print(records)

    weekly_data = {}

    for record in records:
        record_date = date.fromisoformat(record[1])

        # 今週だけ
        if start_of_week <= record_date <= today:
            subject = record[2]
            minutes = int(record[3] or 0)

            day_index = record_date.weekday()

            if subject not in weekly_data:
                weekly_data[subject] = [0,0,0,0,0,0,0]

            weekly_data[subject][day_index] += minutes

    daily_data = {}
    cal=calendar.monthcalendar(today.year, today.month)
    for record in records:
        day = record[1]
        minutes = int(record[3] or 0)

        if day not in daily_data:
            daily_data[day] = 0

        daily_data[day] += minutes
    print(daily_data)

    subject_totals = {}
    ranking = []

    for record in records:
        subject = record[2]
        minutes = int(record[3] or 0)

        if subject not in subject_totals:
            subject_totals[subject] = 0

        subject_totals[subject] += minutes
        ranking = sorted(
            subject_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )


    total_minutes = 0
    today_minutes = 0
    week_minutes = 0
    month_minutes = 0
    level = 1
    exp = 0

    cursor.execute("""
    SELECT subject, goal_minutes
    FROM goals
    WHERE username = ?
    """, (session["username"],))

    goals = cursor.fetchall()
    goal_progress = []

    for subject, goal in goals:
        studied = subject_totals.get(subject, 0)

        if goal > 0:
            percent = int(studied / goal * 100)
        else:
            percent = 0

        goal_progress.append((subject, studied, goal, percent))

    advice = "今日もがんばろう！"

    if len(goal_progress) > 0:
        #達成率が一番低い科目
        lowest = min(goal_progress, key=lambda x:x[3])
        if lowest[3] < 100:
            advice = f"{lowest[0]}は目標まであと{lowest[2]-lowest[1]}分です！"
        else:
            advice = "すべての目標を達成しています！🎉"


    for record in records:
        total_minutes += int(record[3] or 0)
        exp += int(record[3] or 0)
    
        record_date = date.fromisoformat(record[1])
        

        if record[1] == date.today().isoformat():
            today_minutes += int(record[3] or 0)
        if start_of_week <= record_date <= today:
            week_minutes += int(record[3] or 0)
        if record_date.month == today.month and record_date.year == today.year:
            month_minutes += int(record[3] or 0)
    level = exp // 300 + 1

    next_level = level * 300

    remain = next_level - exp

    progress = (exp % 300) / 300 * 100
    cursor.execute("""
            SELECT COUNT(*)
            FROM plans
            WHERE username = ?
                AND date = date('now')
            """, (session["username"],))
    
    plan_total = cursor.fetchone()[0]
    
    cursor.execute("""
            SELECT COUNT(*)
            FROM plans
            WHERE username = ?
                AND date = date('now')
                AND done = 1
            """, (session["username"],))
    
    plan_done = cursor.fetchone()[0]
    advice = ""
    if today_plans:
        subjects = "、".join(plan[0] for plan in today_plans)

        advice = random.choice([
            f"今日は {subjects} をやる予定だよ！📚",
            f"今日は {subjects} に挑戦しよう！✨",
            f"{subjects} を頑張る日だね！応援してるよ😊"
        ])
        

    elif plan_total > 0 and plan_done == plan_total:
        advice = "🎉 今日の予定は全部達成したね！お疲れさま！"



    elif today_minutes == 0:
        advice = random.choice([
            "今日はまだ勉強してないね！まずは10分だけ始めよう📚",
            "少しだけでも勉強するとストリークが続くよ🔥",
            "10分だけでも大丈夫！一緒に頑張ろう😊"
        ])

    elif remain <= 30:
        advice = random.choice([
            f"あと{remain}分でレベルアップ！✨",
            "もう少しでレベルアップだよ！💪",
            f"ラストスパート！あと{remain}分！"
        ])

    elif streak >= 7:
        advice = random.choice([
            f"{streak}日連続！この調子で続けよう🔥",
            "毎日コツコツ頑張れてるね！😊",
            "継続は力なり！その調子！"
        ])

    elif ranking:
        advice = random.choice([
            f"今日は『{ranking[0][0]}』を一番頑張ってるね！",
            f"『{ranking[0][0]}』がトップだよ！✨",
            "バランスよく他の科目もやってみよう！"
        ])

    else:
        advice = random.choice([
            "今日も一緒に頑張ろう！",
            "焦らずコツコツ続けよう📚",
            "君ならできる！💪"
        ])
   
    if level == 1:
        character = "🥚"
    elif level <= 16:
        character = "🐣"
    elif level <= 35:
        character = "🐤"
    elif level <= 50:
        character = "🦉"
    else:
        character = "🐉"
    
    conn.close()
    print(weekly_data)
    
    if plan_total == 0:
        plan_percent = 0
    else:
        plan_percent = int(plan_done / plan_total * 100)
    return render_template(
        "dashboard.html",
        username=session["username"],
        user_plan=user_plan,
        records=records,
        total_minutes=total_minutes,
        today_minutes=today_minutes,
        week_minutes=week_minutes,
        month_minutes=month_minutes,
        ranking=ranking,
        weekly_data=weekly_data,
        daily_data=daily_data,
        calendar_data=cal,
        today=today,
        goals=goals,
        goal_progress=goal_progress,
        advice=advice,
        streak=streak,
        level=level,
        exp=exp,
        remain=remain,
        progress=progress,
        character=character,
        plan_total=plan_total,
        plan_done=plan_done,
        plan_percent=plan_percent,
        today_plans=today_plans
    )
@app.route("/add_record", methods=["GET", "POST"])
@app.route("/add_record/<int:plan_id>", methods=["GET", "POST"])
def add_record(plan_id=None):

    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        subject = request.form["subject"]
        minutes = int(request.form["minutes"])
        username = session["username"]

        if minutes <= 0:
            return "勉強時間を入力してください"
        
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO study_records
        (username, date, subject, minutes)
        VALUES (?, date('now'), ?, ?)
        """, (username, subject, minutes))

        cursor.execute("""
        UPDATE plans
        SET done = 1
        WHERE id = ?
        AND username = ?
        """, (plan_id, username))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))
    subject = ""
    minutes = ""

    conn = get_db()
    cursor = conn.cursor()

    

    cursor.execute("""
    SELECT subject, minutes
    FROM plans
    WHERE id = ? AND username = ?
    """, (plan_id, session["username"]))

    plan = cursor.fetchone()

    conn.close()

    if plan:
        subject = plan[0]
        minutes = plan[1]
           
    return render_template(
        "add_record.html",
        subject=subject,
        minutes=minutes
    )
@app.route("/records")
def records():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, date, subject, minutes
    FROM study_records
    WHERE username = ?
    ORDER BY date DESC
    """, (session["username"],))

    records = cursor.fetchall()

    conn.close()

    return render_template(
        "records.html",
        records=records
    )
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()       
# ユーザー名は3～20文字
        if len(username) < 3 or len(username) > 20:
            flash("ユーザー名は3〜20文字で入力してください")
            return redirect(url_for("register"))

# ユーザー名は英数字と_のみ
        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            flash("ユーザー名は英数字と_のみ使用できます")
            return redirect(url_for("register"))

# ユーザー名とパスワードは同じにできない
        if username == password:
            flash("ユーザー名とパスワードは同じにできません")
            return redirect(url_for("register"))

# パスワードは8文字以上
        if len(password) < 8:
            flash("パスワードは8文字以上にしてください")
            return redirect(url_for("register"))

# 英字を含む
        if not re.search(r"[A-Za-z]", password):
            flash("パスワードには英字を含めてください")
            return redirect(url_for("register"))

# 数字を含む
        if not re.search(r"\d", password):
            flash("パスワードには数字を含めてください")
            return redirect(url_for("register"))

        cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )

        if cursor.fetchone():
            flash("そのユーザー名は既に使われています")
            conn.close()
            return redirect(url_for("register"))
        
        hashed_password = generate_password_hash(password)

        cursor.execute("""
                       INSERT INTO users (username, password)
                       VALUES (?, ?)
                       """, (username, hashed_password))

        conn.commit()
        conn.close()
        flash("登録が完了しました！ログインしてください")
        return redirect(url_for("login"))
        

    return render_template("register.html")
@app.route("/mypage")
def mypage():

    if "username" in session:
        return f"{session['username']}さん、ログイン中です！"

    return "ログインしてください"
@app.route("/delete_record/<int:record_id>")
def delete_record(record_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM study_records
    WHERE id = ? AND username = ?
    """, (record_id, session["username"]))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))
@app.route("/edit_record/<int:record_id>", methods=["GET", "POST"])
def edit_record(record_id):

    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        subject = request.form["subject"]
        minutes = request.form["minutes"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE study_records
        SET subject = ?, minutes = ?
        WHERE id = ? AND username = ?
        """, (subject, minutes, record_id, session["username"]))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))


    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT subject, minutes
    FROM study_records
    WHERE id = ? AND username = ?
    """, (record_id, session["username"]))

    record = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_record.html",
        record=record
    )
@app.route("/goal", methods=["GET", "POST"])
def goal():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        subject = request.form["subject"]
        goal_minutes = int(request.form["goal_minutes"])

        cursor.execute("""
        INSERT INTO goals (username, subject, goal_minutes)
        VALUES (?, ?, ?)
        ON CONFLICT(username, subject)
        DO UPDATE SET goal_minutes = excluded.goal_minutes
        """, (
            session["username"],
            subject,
            goal_minutes
        ))

        conn.commit()

    cursor.execute("""
    SELECT subject, goal_minutes
    FROM goals
    WHERE username = ?
    """, (session["username"],))

    goals = cursor.fetchall()

    conn.close()

    return render_template(
        "goal.html",
        goals=goals
    )
@app.route("/plans", methods=["GET", "POST"])
def plans():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        plan_date = request.form["date"]
        subject = request.form["subject"]
        minutes = int(request.form["minutes"])

        cursor.execute("""
        INSERT INTO plans
        (username, date, subject, minutes)
        VALUES (?, ?, ?, ?)
        """, (session["username"], plan_date, subject, minutes))

        conn.commit()

    cursor.execute("""
    SELECT id, date, subject, minutes, done
    FROM plans
    WHERE username = ?
    ORDER BY date
    """, (session["username"],))

    plans = cursor.fetchall()
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    new_plans = []

    for plan in plans:
        d = datetime.strptime(plan[1], "%Y-%m-%d")
        date_str = f"{d.month}/{d.day}({weekdays[d.weekday()]})"

        new_plans.append((
            plan[0],      # id
            date_str,     # 7/27(月)
            plan[2],      # 科目
            plan[3],      # 時間
            plan[4]       # 状態
        ))
    conn.close()

    return render_template("plans.html", plans=plans)
@app.route("/complete_plan/<int:plan_id>")
def complete_plan(plan_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE plans
    SET done = 1
    WHERE id = ? AND username = ?
    """, (plan_id, session["username"]))

    conn.commit()
    conn.close()

    return redirect(url_for("plans"))
@app.route("/delete_plan/<int:plan_id>")
def delete_plan(plan_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM plans
    WHERE id = ? AND username = ?
    """, (plan_id, session["username"]))

    conn.commit()
    conn.close()

    return redirect(url_for("plans"))
@app.route("/edit_plan/<int:plan_id>", methods=["GET", "POST"])
def edit_plan(plan_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        plan_date = request.form["date"]
        subject = request.form["subject"]
        minutes = int(request.form["minutes"])

        cursor.execute("""
        UPDATE plans
        SET date = ?, subject = ?, minutes = ?
        WHERE id = ? AND username = ?
        """, (plan_date, subject, minutes, plan_id, session["username"]))

        conn.commit()
        conn.close()
        return redirect(url_for("plans"))

    cursor.execute("""
    SELECT date, subject, minutes
    FROM plans
    WHERE id = ? AND username = ?
    """, (plan_id, session["username"]))

    plan = cursor.fetchone()

    conn.close()

    return render_template("edit_plan.html", plan=plan)
@app.route("/friends", methods=["GET", "POST"])
def friends():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    message = "友達申請を送りました！"
    cursor = conn.cursor()

    if request.method == "POST":

        friend_username = request.form["friend_username"].strip()

    # 自分自身は追加できない
        if friend_username == session["username"]:
            return "自分は友達に追加できません"

    # ユーザーが存在するか確認
        cursor.execute("""
        SELECT id
        FROM users
        WHERE username = ?
        """, (friend_username,))

        user = cursor.fetchone()

        if user is None:
            message = "❌ そのユーザーは存在しません"

            cursor.execute("""
            SELECT
                f.to_user,
                COALESCE(SUM(CASE
                    WHEN s.date = date('now') THEN s.minutes
                    ELSE 0
                END), 0),
                COALESCE(SUM(CASE
                    WHEN s.date >= date('now', '-6 days') THEN s.minutes
                    ELSE 0
                END), 0)
            FROM friends f
            LEFT JOIN study_records s
                ON f.to_user = s.username
            WHERE f.from_user = ?
                AND f.status = 'accepted'
            GROUP BY f.to_user
            """, (session["username"],))

            friends = cursor.fetchall()

            conn.close()

            return render_template(
                "friends.html",
                friends=friends,
                message=message
            )



           

    # 友達登録
        cursor.execute("""
        INSERT OR IGNORE INTO friends
        (from_user, to_user, status)
        VALUES (?, ?, ?)
        """, (
            session["username"], 
            friend_username,
            "pending"
            ))

        conn.commit()

        

    cursor.execute("""
    SELECT
        f.to_user,
        COALESCE(SUM(CASE
            WHEN s.date = date('now') THEN s.minutes
            ELSE 0
        END), 0) AS today_minutes,
        COALESCE(SUM(CASE
            WHEN s.date >= date('now', '-6 days') THEN s.minutes
            ELSE 0
        END), 0) AS week_minutes
    FROM friends f
    LEFT JOIN study_records s
    ON f.to_user = s.username
    WHERE f.from_user = ?
        AND f.status = 'accepted'
    GROUP BY f.to_user
    ORDER BY f.to_user
    """, (session["username"],))

    friends = cursor.fetchall()

    from datetime import date, timedelta

    friend_data = []

    for friend in friends:
        username = friend[0]

        cursor.execute("""
        SELECT date
        FROM study_records
        WHERE username = ?
        ORDER BY date DESC
        """, (username,))

        records = cursor.fetchall()

        study_days = set()

        for record in records:
            study_days.add(date.fromisoformat(record[0]))

        streak = 0
        check_day = date.today()

        while check_day in study_days:
            streak += 1
            check_day -= timedelta(days=1)

        friend_data.append((
            friend[0],   # ユーザー名
            friend[1],   # 今日
            friend[2],   # 今週
            streak        # ストリーク
        ))

    conn.close()

    return render_template(
        "friends.html", 
        friends=friend_data,
        message=message)
@app.route("/ranking")
def ranking():
    mode = request.args.get("mode", "today")

    today = date.today()

    if mode == "today":
        date_condition = "s.date = date('now')"

    elif mode == "week":
        start = today - timedelta(days=today.weekday())
        date_condition = f"s.date >= '{start.isoformat()}'"

    elif mode == "month":
        date_condition = (
            f"strftime('%Y-%m', s.date) = '{today.strftime('%Y-%m')}'"
        )

    else:
        date_condition = "1=1"

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(f"""
    SELECT
        s.username,
        SUM(s.minutes) AS total,
        COUNT(DISTINCT c.id) AS cheers
    FROM study_records s

    LEFT JOIN cheers c
    ON s.username = c.to_user

    WHERE
        {date_condition}
        AND (
            s.username = ?
            OR s.username IN (
                SELECT to_user
                FROM friends
                WHERE from_user = ?
                    AND status = 'accepted'
            )
        )
    GROUP BY s.username
    ORDER BY total DESC
    """, (session["username"], session["username"]))

    ranking = cursor.fetchall()

    conn.close()

    return render_template(
        "ranking.html", 
        ranking=ranking,
        username=session["username"],
        mode=mode
    )
@app.route("/cheer", methods=["POST"])
def cheer():

    if "username" not in session:
        return redirect(url_for("login"))

    to_user = request.form["to_user"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM cheers
    WHERE from_user = ?
        AND to_user = ?
        AND cheer_date = date('now')
    """, (session["username"], to_user))

    already = cursor.fetchone()

    if already is None: 
        cursor.execute("""
        INSERT INTO cheers
        (from_user, to_user, cheer_date)
        VALUES (?, ?, date('now'))
        """, (session["username"], to_user))

    conn.commit()
    conn.close()

    return redirect(url_for("ranking"))
@app.route("/friend_requests")
def friend_requests():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, from_user
    FROM friends
    WHERE to_user = ?
      AND status = 'pending'
    ORDER BY id DESC
    """, (session["username"],))

    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "friend_requests.html",
        requests=requests
    )
@app.route("/accept_friend/<int:request_id>")
def accept_friend(request_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT from_user, to_user
    FROM friends
    WHERE id = ?
    """, (request_id,))

    request = cursor.fetchone()

    if request:
        from_user, to_user = request

        cursor.execute("""
        UPDATE friends
        SET status = 'accepted'
        WHERE id = ?
        """, (request_id,))

        cursor.execute("""
        INSERT OR IGNORE INTO friends
        (from_user, to_user, status)
        VALUES (?, ?, 'accepted')
        """, (to_user, from_user))

    conn.commit()
    conn.close()

    return redirect(url_for("friend_requests"))
@app.route("/reject_friend/<int:request_id>")
def reject_friend(request_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM friends
    WHERE id = ?
      AND to_user = ?
    """, (request_id, session["username"]))

    conn.commit()
    conn.close()

    return redirect(url_for("friend_requests"))
@app.route("/remove_friend/<friend_username>")
def remove_friend(friend_username):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # 自分 → 相手
    cursor.execute("""
    DELETE FROM friends
    WHERE from_user = ?
      AND to_user = ?
    """, (session["username"], friend_username))

    # 相手 → 自分
    cursor.execute("""
    DELETE FROM friends
    WHERE from_user = ?
      AND to_user = ?
    """, (friend_username, session["username"]))

    conn.commit()
    conn.close()

    return redirect(url_for("friends"))
@app.route("/profile")
def profile():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username,
           bio,
           profile_image
    FROM users
    WHERE username=?
    """, (session["username"],))

    user = cursor.fetchone()

    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=6)).isoformat()

    # 今日の勉強時間
    cursor.execute("""
    SELECT COALESCE(SUM(minutes), 0)
    FROM study_records
    WHERE username = ? AND date = ?
    """, (session["username"], today))

    today_minutes = cursor.fetchone()[0]

    # 今週の勉強時間
    cursor.execute("""
    SELECT COALESCE(SUM(minutes), 0)
    FROM study_records
    WHERE username = ?
    AND date >= ?
    """, (session["username"], week_ago))

    week_minutes = cursor.fetchone()[0]

    # 合計勉強時間
    cursor.execute("""
    SELECT COALESCE(SUM(minutes), 0)
    FROM study_records
    WHERE username = ?
    """, (session["username"],))

    total_minutes = cursor.fetchone()[0]

    cursor.execute("""
    SELECT DISTINCT date
    FROM study_records
    WHERE username = ?
    ORDER BY date
    """, (session["username"],))

    study_days = [row[0] for row in cursor.fetchall()]

    streak = 0

    if study_days:
        study_dates = sorted(
            datetime.strptime(d, "%Y-%m-%d").date()
            for d in study_days
        )

        current = study_dates[-1]

        for d in reversed(study_dates):
            if d == current:
                streak += 1
                current -= timedelta(days=1)
            else:
                break

    return render_template(
        "profile.html",
        user=user,
        today_minutes=today_minutes,
        week_minutes=week_minutes,
        total_minutes=total_minutes,
        streak=streak

    )
@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        bio = request.form["bio"]

        image = request.files["profile_image"]

        filename = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )


        if filename:
            cursor.execute("""
            UPDATE users
            SET bio = ?, profile_image = ?
            WHERE username = ?
            """, (bio, filename, session["username"]))
        else:
            cursor.execute("""
            UPDATE users
            SET bio = ?
            WHERE username = ?
            """, (bio, session["username"]))

        conn.commit()
        conn.close()

        return redirect(url_for("profile"))

    cursor.execute("""
    SELECT bio
    FROM users
    WHERE username = ?
    """, (session["username"],))

    user = cursor.fetchone()

    conn.close()

    return render_template("edit_profile.html", user=user)
@app.route("/user/<username>")
def user_profile(username):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT username,
           bio,
           profile_image
    FROM users
    WHERE username = ?
    """, (username,))

    user = cursor.fetchone()

    if user is None:
        conn.close()
        return "ユーザーが見つかりません", 404

    conn.close()

    return render_template("user_profile.html", user=user)
@app.route("/timer")
def timer():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("timer.html")
@app.route("/timer_record")
def timer_record():

    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    subject = request.args.get("subject")
    minutes = request.args.get("minutes")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO study_records
    (username, date, subject, minutes)
    VALUES (?, date('now'), ?, ?)
    """,
    (username, subject, int(minutes)))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))
init_db()

if __name__ == "__main__":
    app.run(debug=True)