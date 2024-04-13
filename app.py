from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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


class QuizzesManager:
    """
    Менеджер для работы с викторинами
    Методы:
        Инициализация: QuizzesManager('<path_to_directory>')
            (Инициализирует менеджер,
            кэширует множество ID всех викторин и словарь названий викторин,
            создает файл с именами викторин, если его не существует)
        Получение множества ID всех викторин: get_quizzes_set() -> frozenset
        Проверка существования викторины: check_for_existence(<quiz_id>: int) -> bool
        Получение названия викторины: get_quiz_name(<quiz_id>: int)
            (Возвращает название викторины если викторина существует,
            иначе вызывает исключение ValueError)
        Получение вопросов из викторины: get_quiz_questions(<quiz_id>: int)
            (Возвращает список вопросов если викторина существует,
            иначе вызывает исключение ValueError)
        Добавление викторины: add_quiz('<quiz_name>', <questions_list>)
            (<questions_list> должен быть списком, пригодным для записи в json файл)
        Удаление викторины: remove_quiz(<quiz_id>: int)
            (Удаляет викторину если викторина существует,
            иначе вызывает исключение ValueError)
    """

    def __id_to_path(self, quiz_id):
        return self.directory + "/" + str(quiz_id) + ".json"

    def __find_free_id(self):
        id_candidate = 1
        while id_candidate in self.quizzes_set:
            id_candidate += 1
        return id_candidate

    def __init__(self, path_to_directory: str):
        from os import remove, listdir, path
        from json import load, dump
        self.__remove = remove
        self.__load, self.__dump = load, dump
        self.directory = path_to_directory
        quizzes_names_file_path = self.directory + "/names.json"

        # Кэширование множества ID всех викторин
        self.quizzes_set = frozenset(
            int(j) for j in (i.split(".json")[0] for i in listdir(self.directory) if ".json" in i) if j.isdigit())

        # Проверка наличия файла с именами викторин
        if not path.exists(quizzes_names_file_path):
            # Инициализация пустого кэша
            self.quizzes_names = dict()
            # Создание файла с именами викторин
            with open(quizzes_names_file_path, encoding="utf-8", mode="w") as quizzes_names_file:
                self.__dump(self.quizzes_names, quizzes_names_file, ensure_ascii=False, indent=2)
        else:
            # Кэширование словаря названий викторин, с помощью информации из файла с именами
            with open(quizzes_names_file_path, encoding="utf-8", mode="r") as quizzes_names_file:
                self.quizzes_names = self.__load(quizzes_names_file)

    def get_quizzes_set(self) -> frozenset:
        return self.quizzes_set

    def check_for_existence(self, quiz_id: int) -> bool:
        return quiz_id in self.quizzes_set

    def get_quiz_name(self, quiz_id: int):
        if quiz_id in self.quizzes_set:
            if str(quiz_id) in self.quizzes_names:
                return self.quizzes_names[str(quiz_id)]
            raise RuntimeError(f"cannot find the name of the quiz with id=={quiz_id}")
        raise ValueError(f"the quiz with id=={quiz_id} does not exist")

    def get_quiz_questions(self, quiz_id: int):
        if quiz_id in self.quizzes_set:
            with open(self.__id_to_path(quiz_id), encoding="utf-8", mode="r") as questions_file:
                quiz = self.__load(questions_file)
            return quiz
        raise ValueError(f"the quiz with id=={quiz_id} does not exist")

    def add_quiz(self, quiz_name, questions_list):
        quiz_id = self.__find_free_id()  # Поиск свободного ID для новой викторины
        self.quizzes_names[str(quiz_name)] = quiz_id  # Добавление нового имени в словарь имен викторин

        # Добавление нового ID в множество ID всех викторин
        new_quizzes_set = set(self.quizzes_set)
        new_quizzes_set.add(quiz_id)
        self.quizzes_set = frozenset(new_quizzes_set)

        # Добавление нового имени в файл с именами викторин
        with open(self.directory + "/names.json", encoding="utf-8", mode="r") as quizzes_names_file:
            new_quizzes_names = self.__load(quizzes_names_file)
        new_quizzes_names[str(quiz_id)] = quiz_name
        with open(self.directory + "/names.json", encoding="utf-8", mode="w") as quizzes_names_file:
            self.__dump(new_quizzes_names, quizzes_names_file, ensure_ascii=False, indent=2)
        # Добавление нового файла с вопросами новой викторины
        with open(self.__id_to_path(quiz_id), encoding="utf-8", mode="w") as questions_file:
            self.__dump(questions_list, questions_file, ensure_ascii=False, indent=2)

    def remove_quiz(self, quiz_id: int):
        # Проверка существования викторины
        if quiz_id in self.quizzes_set:

            # Удаление ID из множества ID всех викторин
            new_quizzes_set = set(self.quizzes_set)
            new_quizzes_set.remove(quiz_id)
            self.quizzes_set = frozenset(new_quizzes_set)

            del self.quizzes_names[str(quiz_id)]  # Удаление имени из словаря с именами викторин
            self.__remove(self.__id_to_path(quiz_id))  # Удаление файла с вопросами викторины

            # Удаление имени из файла с именами викторин
            with open(self.directory + "/names.json", encoding="utf-8", mode="r") as quizzes_names_file:
                new_quizzes_names = self.__load(quizzes_names_file)
            del new_quizzes_names[str(quiz_id)]
            with open(self.directory + "/names.json", encoding="utf-8", mode="w") as quizzes_names_file:
                self.__dump(new_quizzes_names, quizzes_names_file, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"the quiz with id=={quiz_id} does not exist")


@app.route('/get_time_left', methods=['GET'])
def get_time_left():
    time_left = "01:00"  # Оставляем 1 минуту на каждый вопрос
    return jsonify({'time_left': time_left})


@app.route('/')
def index():
    param = {
        'is_authorized': 'user_id' in session
    }
    return render_template('index.html', **param)


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
                session['user_id'] = user.id
                flash('Login successful!')
                return redirect(url_for('quiz_selection'))
            else:
                flash('Incorrect username or password. Please try again.', 'error')
        else:
            flash('Incorrect username or password. Please try again.', 'error')
    if 'user_id' in session:
        return redirect('/quiz_selection')
    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        del session['user_id']
    return redirect('/')


@app.route('/quiz_selection')
def quiz_selection():
    if 'user_id' not in session:
        return redirect('/')
    param = {
        'quizzes_manager': quizzes_manager
    }
    return render_template('quiz_selection.html', **param)


@app.route('/start_quiz/<quiz_id>')
def start_quiz(quiz_id):
    if quiz_id.lower() == 'breaking_bad' or quiz_id.lower() == 'house':
        session['quiz_id'] = quiz_id
        return redirect(url_for('quiz_question', quiz_id=quiz_id, question_number=1))
    else:
        return "Invalid quiz"


@app.route('/quiz', methods=['GET', 'POST'])
def quiz_question():
    # Get params
    quiz_id = int(request.args.get("quiz_id"))
    question_number = int(request.args.get("question_number"))

    session['quiz_id'] = quiz_id

    # Check if the user is logged in
    if 'user_id' not in session:
        flash('Please log in to access the quiz.', 'error')
        return redirect(url_for('login'))

    if not quizzes_manager.check_for_existence(quiz_id):
        return "Invalid quiz"
    questions = quizzes_manager.get_quiz_questions(quiz_id)

    if request.method == 'POST':
        selected_answer = request.form.get(
            'answer')  # Используем get() для получения параметра, чтобы избежать KeyError
        if not selected_answer:  # Если ответ не выбран, переходим к следующему вопросу
            next_question_number = question_number + 1
            if next_question_number <= len(questions):
                return redirect(url_for('quiz_question', quiz_id=quiz_id, question_number=next_question_number))
            else:
                return redirect(url_for('quiz_results'))

        question = questions[question_number - 1]
        if selected_answer == question['correct_answer']:
            session.setdefault('num_correct', 0)
            session['num_correct'] += 1
            flash('Correct!')
        else:
            flash('Incorrect!')

        next_question_number = question_number + 1
        if next_question_number <= len(questions):
            return redirect(url_for('quiz_question', quiz_id=quiz_id, question_number=next_question_number))
        else:
            return redirect(url_for('quiz_results'))

    question = questions[question_number - 1]
    return render_template('question.html', quiz_id=quiz_id, question_number=question_number,
                           question=question['question'], answers=question['answers'])


@app.route('/quiz_results')
def quiz_results():
    num_correct = session.get('num_correct', 0)

    total_questions = 0
    if 'quiz_id' in session:
        quiz_id = session['quiz_id']
        questions = quizzes_manager.get_quiz_questions(int(quiz_id))
        if questions is not None:
            total_questions = len(questions)

    session.pop('num_correct', None)
    if num_correct > total_questions:
        num_correct = total_questions
    return render_template('quiz_results.html', num_correct=num_correct, total_questions=total_questions)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    quizzes_manager = QuizzesManager('./quizzes')
    app.run(debug=True)