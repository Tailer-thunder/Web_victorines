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
                return redirect(
                    url_for('quiz_selection'))  # Перенаправление на страницу выбора викторины после успешного входа
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
            'question': 'What is the main character\'s name in Breaking Bad?',
            'answers': ['Walter White', 'Jesse Pinkman', 'Saul Goodman', 'Gus Fring'],
            'correct_answer': 'Walter White'
        },
        {
            'question': 'Who is Jesse Pinkman\'s former chemistry teacher?',
            'answers': ['Walter White', 'Gus Fring', 'Saul Goodman', 'Mike Ehrmantraut'],
            'correct_answer': 'Walter White'
        }
        # можно ещё вопросов, наподобие этого ещё викторин сделать черезе ссылочку по кнопочке из quiz_selection
    ]
    return render_template('quiz.html', questions=questions)


@app.route('/submit_quiz_answers', methods=['POST'])
def submit_quiz_answers():
    # Получаем ответы пользователя из запроса
    user_answers = request.form

    # Правильные ответы только на эту викторину к сожалению ((((
    correct_answers = {
        "What is the main character's name in Breaking Bad?": 'Walter White',
        "Who is Jesse Pinkman's former chemistry teacher?": 'Walter White'
    }

    # Подсчитываем количество правильных ответов
    num_correct_answers = 0
    for question, user_answer in user_answers.items():
        if user_answer == correct_answers.get(question):
            num_correct_answers += 1

    # Возвращаем результаты на отдельную страницу
    return render_template('quiz_results.html', num_correct=num_correct_answers, total_questions=len(correct_answers))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
