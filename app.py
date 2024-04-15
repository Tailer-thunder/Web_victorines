from os import environ

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from wtforms import Form, StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, Email, EqualTo, Optional, ValidationError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)


def new_password_validator(password) -> str:
    """
    Проверяет корректность и надежность пароля:
    если пароль слишком простой или некорректный,
    то возвращает сообщение,
    иначе возвращает пустую строку
    """
    password = str(password)
    if not password.isascii():
        return "The password must contain only ASCII chars"
    if len(password) < 16:
        return 'The password must contain at least 16 chars'
    if password.isalpha():
        return 'The password should not consist only of letters'
    if password.isdigit():
        return 'The password should not consist only of numbers'
    if password.islower():
        return 'All letters of the password must not be in lowercase'
    if password.isupper():
        return 'All letters of the password must not be uppercase'
    if len(set(password)) * 2 < len(password):
        return 'The password should not contain too many non-unique chars'
    if ('123' or '321' or 'abc' or 'qwe') in password:
        return 'The password should not contain obvious combinations'
    return ''


def check_data_for_password_changing(old_password, new_password, confirm_new_password):
    """Валидатор формы, проверяет данные для смены пароля"""
    validation_errors = []
    if old_password or new_password or confirm_new_password:
        if not old_password:
            validation_errors.append(
                (ValidationError('To change the password, enter the old password'), 'old_password_not_filled'))
        if not new_password:
            validation_errors.append(
                (ValidationError('To change the password, enter a new password'), 'new_password_not_filled'))
        if not confirm_new_password:
            validation_errors.append((ValidationError('To change the password, confirm the new password'),
                                      'confirm_new_password_not_filled'))
    return validation_errors


class IsEmailFree:
    """
    Этот валидатор формы проверяет, не занята ли указанная электронная почта
    IsEmailFree(validation_exception=None)
    Параметры:
    validation_exception - адрес, который необходимо исключить из проверки
    """

    def __init__(self, validation_exception=None):
        self.validation_exception = validation_exception

    def __call__(self, form, field):
        existing_email = User.query.filter_by(email=field.data).first()
        if existing_email:
            if self.validation_exception:
                if existing_email.email != self.validation_exception:
                    raise ValidationError('This email is already in use')
            else:
                raise ValidationError('This email is already in use')


def get_edit_profile_form(user):
    """Возвращает экземпляр класса EditProfileForm"""

    class EditProfileForm(Form):
        """Форма для редактирования профиля"""
        name = StringField('Full name', [Optional()], default=user.username)
        email = StringField('Email', [Optional(), Email(message='Incorrect email', check_deliverability=False),
                                      IsEmailFree(validation_exception=user.email)], default=user.email)
        old_password = PasswordField('Old password', [Optional()])
        new_password = PasswordField('New password', [Optional()])
        confirm_new_password = PasswordField('Confirm new password',
                                             [Optional(), EqualTo('new_password', message='Passwords must match')])
        submit = SubmitField()

    return EditProfileForm(request.form)


def get_remove_account_form():
    """Возвращает экземпляр класса DeleteAccountForm"""

    class RemoveAccountForm(Form):
        """Форма для удаления аккаунта"""
        password = PasswordField('Password', [InputRequired(message='Enter password')])
        confirm = BooleanField('Confirm', [InputRequired(message='Please check')])
        submit = SubmitField()

    return RemoveAccountForm(request.form)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True, index=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(100), nullable=False)


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
        'title': 'Home',
        'is_authorized': 'user_id' in session
    }
    return render_template('index.html', **param)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    param = {'title': 'Sign up'}
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        param['inputted_username'] = username
        param['inputted_email'] = email

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            param['alert_message'] = 'Username already exists. Please choose a different one.'
            return render_template('register.html', **param)

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            param['alert_message'] = 'Email already exists. Please choose a different one.'
            return render_template('register.html', **param)

        password_check_result = new_password_validator(password)
        if password_check_result:
            param['alert_message'] = password_check_result
            return render_template('register.html', **param)

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('signin'))
    return render_template('register.html', **param)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    param = {'title': 'Sign in'}
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.id
                flash('Login successful!')
                return redirect(url_for('quiz_selection'))
            else:
                param['alert_message'] = 'Incorrect username or password. Please try again.'
        else:
            param['alert_message'] = 'Incorrect username or password. Please try again.'
        return render_template('login.html', **param)
    if 'user_id' in session:
        return redirect(url_for('quiz_selection'))
    return render_template('login.html', **param)


@app.route('/logout')
def logout():
    if 'user_id' in session:
        del session['user_id']
    return redirect('/')


@app.route('/my_account', methods=['GET', 'POST'])
def my_account():
    if 'user_id' not in session:
        return redirect(
            url_for('signin'))  # Если пользователь не авторизован, то переадресовываем на страницу авторизации
    changes_successfully_applied = False  # Сообщение об успешном применении изменений
    validation_errors = []  # Список ошибок валидации
    user = db.session.query(User).filter(User.id == session['user_id']).first()  # Получаем пользователя из базы данных
    form = get_edit_profile_form(user)  # Получаем форму для редактирования профиля пользователя из базы данных
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            return redirect(url_for('signin'))
        if form.old_password.data or form.new_password.data or form.confirm_new_password.data:
            if not form.old_password.data:
                validation_errors.append(
                    (ValidationError('To change the password, enter the old password'), 'old_password_not_filled'))
            if not form.new_password.data:
                validation_errors.append(
                    (ValidationError('To change the password, enter a new password'), 'new_password_not_filled'))
            if not form.confirm_new_password.data:
                validation_errors.append((ValidationError('To change the password, confirm the new password'),
                                          'confirm_new_password_not_filled'))
            if form.old_password.data:
                if not check_password_hash(user.password, form.old_password.data):
                    validation_errors.append((ValidationError('Invalid password'), 'wrong_password'))
            if form.new_password.data:
                password_check_result = new_password_validator(form.new_password.data)
                if password_check_result:
                    validation_errors.append((ValidationError(password_check_result), 'password_is_too_easy'))
        if not validation_errors:
            if form.name.data and form.name.data != user.username:
                user.username = form.name.data  # Сохраняем новое имя пользователя, если оно было указано в форме
                changes_successfully_applied = True
            if form.email.data and form.email.data != user.email:
                user.email = form.email.data  # Сохраняем новый email пользователя, если он был указан в форме
                changes_successfully_applied = True
            if form.new_password.data:
                # Сохраняем новый пароль, если он был указан в форме
                user.password = generate_password_hash(form.new_password.data)
                changes_successfully_applied = True
            db.session.commit()

    param = {
        'title': 'My account',
        'user': user,  # Передаем пользователя из базы данных в шаблон
        'user_id': session['user_id'],  # Передаем ID пользователя из базы данных в шаблон, чтобы его отобразить в форме
        'is_authorized': True,
        'errors': validation_errors,
        'changes_successfully_applied': changes_successfully_applied
    }
    # Возвращаем шаблон с формой для редактирования профиля пользователя
    return render_template('my_account.html', form=form, **param)


@app.route('/remove_account', methods=['GET', 'POST'])
def remove_account():
    if 'user_id' not in session:  # Если пользователь не авторизован, то переадресовываем на страницу авторизации
        return redirect(url_for('signin'))
    validation_errors = []
    form = get_remove_account_form()
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            return redirect(url_for('signin'))
        if not check_password_hash(user.password, form.password.data):
            validation_errors.append((ValidationError('Invalid password'), 'wrong_password'))
        if not validation_errors:
            del session['user_id']
            db.session.query(User).filter(User.id == user.id).delete()
            db.session.commit()
            return redirect(url_for('index'))
    param = {
        'title': 'Удаление аккаунта',
        'session': True,
        'errors': validation_errors
    }
    # Возвращаем шаблон с формой для удаления профиля пользователя
    return render_template('remove_account.html', form=form, **param)


@app.route('/quiz_selection')
def quiz_selection():
    if 'user_id' not in session:
        return redirect(
            url_for('signin'))  # Если пользователь не авторизован, то переадресовываем на страницу авторизации
    param = {
        'title': 'Quiz selection',
        'is_authorized': True,
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
        return redirect(url_for('signin'))

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
                           question=question['question'], answers=question['answers'], image=question['image'])


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


@app.route('/new_quiz')
def new_quiz():
    params = {'title': 'New quiz', 'is_authorized': 'user_id' in session}
    return render_template('new_quiz.html', **params)


@app.errorhandler(404)
def page_not_found(e):
    param = {
        'title': 'Page not found',
        'is_authorized': 'user_id' in session
    }
    return render_template('404.html', **param), 404  # Отображение ошибки: страница не найдена


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    quizzes_manager = QuizzesManager('./quizzes')
    port = int(environ.get("PORT", 5000))  # Получение порта
    app.run(host='0.0.0.0', port=port, debug=True)  # Запуск приложения
