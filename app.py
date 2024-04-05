from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)
    wrong_answer1 = db.Column(db.String(100), nullable=False)
    wrong_answer2 = db.Column(db.String(100), nullable=False)
    wrong_answer3 = db.Column(db.String(100), nullable=False)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user:
            if check_password_hash(user.password, password):
                flash('Login successful!')
                return redirect(url_for('quiz_selection'))
            else:
                flash('Incorrect username or password. Please try again.', 'error')
        else:
            flash('Incorrect username or password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/quiz_selection')
def quiz_selection():
    return render_template('quiz_selection.html')


@app.route('/start_quiz/<quiz_id>', methods=['GET', 'POST'])
def start_quiz(quiz_id):
    return f"Starting quiz {quiz_id}"


@app.route('/start_quiz/breaking_bad', methods=['GET'])
def start_breaking_bad_quiz():
    questions = [
        {
            "question": "What is the name of the main character in the TV series 'Breaking Bad'?",
            "answers": ["Walter White", "Jesse Pinkman", "Saul Goodman", "Mike Ehrmantraut"],
            "correct_answer": "Walter White"
        },
        {
            "question": "In which city do the main events of the series take place?",
            "answers": ["Chicago", "Los Angeles", "Albuquerque", "Miami"],
            "correct_answer": "Albuquerque"
        },
        {
            "question": "Which character is a lawyer and private investigator?",
            "answers": ["Skyler White", "Saul Goodman", "Mike Ehrmantraut", "Gus Fring"],
            "correct_answer": "Saul Goodman"
        },
        {
            "question": "Who is the partner of Walter White in the methamphetamine business?",
            "answers": ["Jesse Pinkman", "Hank Schrader", "Walter Jr.", "Skyler White"],
            "correct_answer": "Jesse Pinkman"
        },
        {
            "question": "What is the nickname of Walter White's methamphetamine?",
            "answers": ["Blue Crystal", "Green Lantern", "Pink Panther", "White Lightning"],
            "correct_answer": "Blue Crystal"
        },
        {
            "question": "Who is the owner of the Los Pollos Hermanos restaurant chain?",
            "answers": ["Walter White", "Jesse Pinkman", "Saul Goodman", "Gustavo Fring"],
            "correct_answer": "Gustavo Fring"
        },
        {
            "question": "What is the profession of Walter White before he starts cooking meth?",
            "answers": ["High school chemistry teacher", "Lawyer", "Car mechanic", "Police officer"],
            "correct_answer": "High school chemistry teacher"
        },
        {
            "question": "What is the name of Walter White's brother-in-law who works for the DEA?",
            "answers": ["Hank Schrader", "Ted Beneke", "Tuco Salamanca", "Mike Ehrmantraut"],
            "correct_answer": "Hank Schrader"
        },
        {
            "question": "Who is the distributor of the blue meth in the later seasons?",
            "answers": ["Gus Fring", "Tuco Salamanca", "Hector Salamanca", "Jack Welker"],
            "correct_answer": "Gus Fring"
        },
        {
            "question": "What is the name of the spin-off prequel series to 'Breaking Bad' featuring Saul Goodman?",
            "answers": ["Better Call Saul", "The Saul Show", "Legal Eagle", "Goodman's Gambit"],
            "correct_answer": "Better Call Saul"
        }
    ]
    return render_template('quiz.html', questions=questions, quiz_title='Breaking Bad')


@app.route('/start_quiz/House', methods=['GET'])
def start_House_quiz():
    questions = [
        {
            "question": "What is the name of the main character in the TV series 'House'?",
            "answers": ["Gregory House", "James Wilson", "Lisa Cuddy", "Robert Chase"],
            "correct_answer": "Gregory House"
        },
        {
            "question": "What is Dr. House's specialty in medicine?",
            "answers": ["Oncology", "Diagnostic Medicine", "Neurology", "Cardiology"],
            "correct_answer": "Diagnostic Medicine"
        },
        {
            "question": "Who is Dr. House's best friend and colleague?",
            "answers": ["Lisa Cuddy", "James Wilson", "Allison Cameron", "Eric Foreman"],
            "correct_answer": "James Wilson"
        },
        {
            "question": "What is the name of Dr. House's team of diagnosticians?",
            "answers": ["Surgical Team", "Diagnostic Team", "Emergency Team", "Therapy Team"],
            "correct_answer": "Diagnostic Team"
        },
        {
            "question": "What is Dr. House's favorite catchphrase?",
            "answers": ["Everybody lies", "Life is pain", "No pain, no gain", "Pain is temporary"],
            "correct_answer": "Everybody lies"
        },
        {
            "question": "What is the name of the hospital where Dr. House works?",
            "answers": ["Mayfield Psychiatric Hospital", "Seattle Grace Hospital",
                        "Princeton-Plainsboro Teaching Hospital", "New Jersey General Hospital"],
            "correct_answer": "Princeton-Plainsboro Teaching Hospital"
        },
        {
            "question": "What is Dr. House's addiction?",
            "answers": ["Cocaine", "Morphine", "Vicodin", "Heroin"],
            "correct_answer": "Vicodin"
        },
        {
            "question": "Who is Dr. House's boss at the hospital?",
            "answers": ["James Wilson", "Allison Cameron", "Eric Foreman", "Lisa Cuddy"],
            "correct_answer": "Lisa Cuddy"
        },
        {
            "question": "What is the nickname given to Dr. House by his team?",
            "answers": ["House", "Boss", "Doc", "Greg"],
            "correct_answer": "House"
        },
        {
            "question": "What is Dr. House's first name?",
            "answers": ["John", "Robert", "Gregory", "David"],
            "correct_answer": "Gregory"
        }
    ]
    return render_template('quiz.html', questions=questions, quiz_title='House')


@app.route('/submit_quiz_answers', methods=['POST'])
def submit_quiz_answers():
    # Получаем ответы пользователя из запроса
    user_answers = request.form

    # Получаем название викторины из параметра запроса
    quiz_name = request.args.get('quiz_name')

    # Проверяем, что параметр quiz_name не None и валидный
    if quiz_name is None or quiz_name not in ['Breaking Bad', 'House']:
        return "Invalid quiz name"

    # В зависимости от выбранной викторины вызываем соответствующую функцию для проверки ответов
    if quiz_name == 'Breaking Bad':
        num_correct_answers, total_questions = submit_quiz_answers_breaking_bad(user_answers)
    elif quiz_name == 'House':
        num_correct_answers, total_questions = submit_quiz_answers_house(user_answers)
    else:
        return "Invalid quiz name"

    # Возвращаем результаты на отдельную страницу
    return render_template('quiz_results.html', num_correct=num_correct_answers, total_questions=total_questions)

def submit_quiz_answers_breaking_bad(user_answers):
    correct_answers_breaking_bad = {
        "What is the name of the main character in the TV series 'Breaking Bad'?": 'Walter White',
        "In which city do the main events of the series take place?": 'Albuquerque',
        "Which character is a lawyer and private investigator?": 'Saul Goodman',
        "Who is the partner of Walter White in the methamphetamine business?": 'Jesse Pinkman',
        "What is the nickname of Walter White's methamphetamine?": 'Blue Crystal',
        "Who is the owner of the Los Pollos Hermanos restaurant chain?": 'Gustavo Fring',
        "What is the profession of Walter White before he starts cooking meth?": 'High school chemistry teacher',
        "What is the name of Walter White's brother-in-law who works for the DEA?": 'Hank Schrader',
        "Who is the distributor of the blue meth in the later seasons?": 'Gus Fring',
        "What is the name of the spin-off prequel series to 'Breaking Bad' featuring Saul Goodman?": 'Better Call Saul'
    }

    num_correct_answers = 0
    for question, user_answer in user_answers.items():
        if user_answer == correct_answers_breaking_bad.get(question):
            num_correct_answers += 1

    total_questions = len(correct_answers_breaking_bad)
    return num_correct_answers, total_questions


def submit_quiz_answers_house(user_answers):
    correct_answers_house = {
        "What is the name of the main character in the TV series 'House'?": 'Gregory House',
        "What is Dr. House's specialty in medicine?": 'Diagnostic Medicine',
        "Who is Dr. House's best friend and colleague?": 'James Wilson',
        "What is the name of Dr. House's team of diagnosticians?": 'Diagnostic Team',
        "What is Dr. House's favorite catchphrase?": 'Everybody lies',
        "What is the name of the hospital where Dr. House works?": 'Princeton-Plainsboro Teaching Hospital',
        "What is Dr. House's addiction?": 'Vicodin',
        "Who is Dr. House's boss at the hospital?": 'Lisa Cuddy',
        "What is the nickname given to Dr. House by his team?": 'House',
        "What is Dr. House's first name?": 'Gregory'
    }

    num_correct_answers = 0
    for question, user_answer in user_answers.items():
        if user_answer == correct_answers_house.get(question):
            num_correct_answers += 1

    total_questions = len(correct_answers_house)
    return num_correct_answers, total_questions


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
