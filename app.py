from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3
import csv
from datetime import datetime
from flask import Response

app = Flask(__name__)
app.secret_key = "replace_with_a_random_secret"  # change for deployment
GLOBAL_PASSWORD = "exam2025"  # change if you want another global password
DB = "questions.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")
        if not student_id:
            return render_template("login.html", error="Student ID required")
        if password != GLOBAL_PASSWORD:
            return render_template("login.html", error="Invalid password")
        session['student_id'] = student_id
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('student_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html", student_id=session['student_id'])

@app.route('/section_a')
def section_a():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    qs = conn.execute("SELECT * FROM section_a ORDER BY id").fetchall()
    # load saved answers for this student
    saved = {}
    rows = conn.execute("SELECT question_id, answer FROM answers WHERE student_id=? AND section='A'", (session['student_id'],)).fetchall()
    for r in rows:
        saved[r['question_id']] = r['answer']
    conn.close()
    return render_template("section_a.html", questions=qs, saved=saved, student_id=session['student_id'])

@app.route('/section_b')
def section_b():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    qs = conn.execute("SELECT * FROM section_b ORDER BY id").fetchall()
    saved = {}
    rows = conn.execute("SELECT question_id, answer FROM answers WHERE student_id=? AND section='B'", (session['student_id'],)).fetchall()
    for r in rows:
        saved[r['question_id']] = r['answer']
    conn.close()
    # If no section B questions exist yet, you'll see an empty list
    return render_template("section_b.html", questions=qs, saved=saved, student_id=session['student_id'])

@app.route('/save_answer', methods=['POST'])
def save_answer():
    if 'student_id' not in session:
        return jsonify(status="error", message="Not authenticated"), 403
    data = request.get_json() or {}
    section = data.get('section')
    question_id = data.get('question_id')
    answer = data.get('answer')
    if section not in ('A', 'B') or question_id is None:
        return jsonify(status="error", message="Invalid payload"), 400
    now = datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute('''
        INSERT INTO answers (student_id, section, question_id, answer, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(student_id, section, question_id)
        DO UPDATE SET answer=excluded.answer, updated_at=excluded.updated_at
    ''', (session['student_id'], section, question_id, answer, now))
    conn.commit()
    conn.close()
    return jsonify(status="ok", saved_at=now)

@app.route('/submit', methods=['POST'])
def submit():
    # For simplicity: just mark as submitted or return current answers
    if 'student_id' not in session:
        return redirect(url_for('login'))
    # Additional validation for Section B:
    # Q1 compulsory, plus exactly up to 3 other answers (total 4 including Q1)
    conn = get_db()
    student = session['student_id']
    # get section B questions
    q_rows = conn.execute("SELECT id FROM section_b ORDER BY id").fetchall()
    q_ids = [r['id'] for r in q_rows]
    # gather saved answers
    rows = conn.execute("SELECT question_id, answer FROM answers WHERE student_id=? AND section='B'", (student,)).fetchall()
    answered = {r['question_id']: r['answer'] for r in rows if r['answer'] and r['answer'].strip() != ""}
    # if no section B questions exist, skip B validation
    if q_ids:
        if 1 not in q_ids:
            # If Q1 is not id=1, assume first question is compulsory. Adapt as needed.
            compulsory_qid = q_ids[0]
        else:
            compulsory_qid = 1
        if compulsory_qid not in answered:
            return render_template("submit_result.html", error="You must answer Question 1 in Section B (compulsory).")
        # count other answered (excluding compulsory)
        other_answered = [qid for qid in answered.keys() if qid != compulsory_qid]
        if len(other_answered) < 3:
            return render_template("submit_result.html", error="You must answer Question 1 and any other 3 questions in Section B (total 4).")
    conn.close()
    # If passed validation:
    return render_template("submit_result.html", success="Exam submitted. Good luck!")

@app.route('/download_submissions')
def download_submissions():
    output = []
    output.append(['Student ID', 'Section A Score', 'Section B Answers', 'Section B Score'])
    for sub in get_all_submissions():
        output.append([sub.student_id, sub.section_a_score, sub.section_b_answers, sub.section_b_score])
    def generate():
        writer = csv.writer(Echo())
        for row in output:
            yield writer.writerow(row)
    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=submissions.csv"})

if __name__ == "__main__":
    app.run(debug=True)
