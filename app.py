from os import environ, urandom

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort, make_response
from flask_mail import Mail, Message
from smtplib import SMTPRecipientsRefused, SMTPDataError
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from wtforms import Form, StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, Email, EqualTo, Optional, ValidationError

from datetime import datetime
from config import mail as mail_configuration  # Импортируем файл конфигурации

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.secret_key = 'your_secret_key'

# Устанавливаем параметры приложения для отправки писем по SMTP
app.config['MAIL_SERVER'] = mail_configuration.server
app.config['MAIL_PORT'] = mail_configuration.port
app.config['MAIL_USE_TLS'] = mail_configuration.TLS
app.config['MAIL_USE_SSL'] = mail_configuration.SSL
app.config['MAIL_USERNAME'] = mail_configuration.address
app.config['MAIL_PASSWORD'] = mail_configuration.password
app.config['MAIL_DEFAULT_SENDER'] = mail_configuration.address
app.config['MAIL_ASCII_ATTACHMENTS'] = mail_configuration.ASCII
# Создаем экземпляр менеджера для работы с письмами
mail = Mail(app)

db = SQLAlchemy(app)


def send_confirmation_code(email: str) -> str:
    """
    Функция для отправки письма с кодом подтверждения,
    принимает параметр email: str c адресом электронной почты,
    если отправка успешна,
    то возвращает код подтверждения, который отправила на почту,
    если отправка невозможна (т.е адрес не существует или неверный),
    то выбрасывает исключение CantSendEmail.
    """
    if not isinstance(email, str):
        raise TypeError('email must be a string')

    # С помощью криптографически надежной функции, создаем псевдослучайный код подтверждения
    # и приводим его к удобному формату
    confirmation_code = hex(int.from_bytes(urandom(2), "big"))[2:].upper().zfill(4)

    # Создаем письмо с кодом подтверждения
    msg = Message(
        "WebVictorines: your confirmation code", recipients=[email], )
    msg.body = (f'To confirm your email, enter this code: {confirmation_code}\n'
                f'If you have not requested confirmation by email, just ignore this letter.')

    try:  # Пытаемся отправить письмо
        mail.send(msg)
    except SMTPRecipientsRefused:  # Невозможно отправить письмо, так как адрес неверный
        raise CantSendEmail
    except SMTPDataError:  # Невозможно отправить письмо, так как адрес не существует
        raise CantSendEmail
    else:  # Если отправка успешна, то возвращаем код подтверждения
        return confirmation_code


def save_result_of_quiz(*, user_id: int | str, quiz_id: int | str, total_questions: int = None,
                        number_of_correct: int) -> None:
    """
    Функция сохраняет результат выполнения викторины в базу данных, самостоятельно вычисляя баллы и время выполнения.
    Параметры:
        <user_id> - ID пользователя, который выполнил викторину (int или str).
        <quiz_id> - ID викторины, которая была выполнена (int или str).
        <total_questions> - необязательный параметр, общее количество вопросов в викторине (int).
        <number_of_correct> - количество правильных ответов (int).
    Все параметры необходимо передавать как именованные.
    """
    # Если параметры user_id и quiz_id не являются числами или строками, то выбрасываем исключение TypeError
    if any(map(lambda x: not (isinstance(x, int) or isinstance(x, str)), (user_id, quiz_id))):
        raise TypeError("user_id and quiz_id must be int or str")
    # Если общее количество вопросов не указано, то получаем его от менеджера викторин
    if total_questions is None:
        total_questions = len(quizzes_manager.get_quiz_questions(quiz_id))
    # Если параметры total_questions и number_of_correct не являются числами, то выбрасываем исключение TypeError
    if any(map(lambda x: not isinstance(x, int), (total_questions, number_of_correct))):
        raise TypeError("total_question and num_correct must be int")

    if total_questions <= 0:
        raise ValueError("total_question must be greater than 0")

    user_id, quiz_id = int(user_id), int(quiz_id)
    scores = int(round(number_of_correct / total_questions, 4) * 10_000)  # Высчитываем баллы за викторину

    # Сохраняем результат в базу данных
    new_result = ResultOfQuiz(user_id=user_id, quiz_id=quiz_id, scores=scores, time=datetime.now())
    db.session.add(new_result)
    db.session.commit()


def update_rating(user_id: int | str) -> None:
    """
    Функция обновляет рейтинг пользователя.
    Принимает единственный параметр <user_id>: (int или str).
    """
    # Если параметр user_id не является числом или строкой, то выбрасываем исключение TypeError
    if not (isinstance(user_id, int) or isinstance(user_id, str)):
        raise TypeError("user_id must be int or str")

    # Получаем пользователя из базы данных
    user_id = int(user_id)
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise ValueError(f"user with ID={user_id} does not exist")

    # Получаем список результатов из базы данных
    log_of_results = ResultOfQuiz.query.filter_by(user_id=user_id).order_by(ResultOfQuiz.scores.desc()).all()
    # Вычисляем рейтинг пользователя
    quizzes_already_taken_into = []
    total_scores = 0
    for result in log_of_results:
        if result.quiz_id not in quizzes_already_taken_into:
            total_scores += result.scores
            quizzes_already_taken_into.append(result.quiz_id)
    total_scores = total_scores // 100

    # Записываем рейтинг пользователя в базу данных
    user.rating = total_scores
    db.session.commit()


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


def generate_strong_password() -> str:
    """
    Функция генерирует надежный пароль из 16 знаков.
    Не принимает параметров, возвращает пароль в виде строки.
    """
    password = ''
    flag = True
    while flag or new_password_validator(password):  # Проверяем пароль на надежность, в первый раз проверку пропускаем
        password = []
        flag = False
        i = 0
        while i < 16:
            # Каждая итерация цикла генерирует один или ноль знаков
            char_code = int.from_bytes(urandom(1), 'big') & 0b0111_1111
            # Так как один байт - это слишком много для ASCII, применили битовую маску

            # Если код знака в интервале [33, 126], то добавляем его в пароль
            if 33 <= char_code <= 126:
                password.append(chr(char_code))
                i += 1
        password = ''.join(password)  # Превращаем пароль в строку
    return password


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True, index=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(100), nullable=False)  # Статус пользователя
    rating = db.Column(db.Integer, default=0)  # Рейтинг пользователя (<number> points)


class OneTimeCode(db.Model):
    # ID кода
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True, index=True)
    # ID пользователя, для которого этот код предназначается
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True, index=True)
    # Хэшированный код
    code = db.Column(db.String(100), nullable=False)


class ResultOfQuiz(db.Model):
    # ID результата
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True, index=True)
    # ID пользователя, который выполнил викторину
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=False, index=True)
    # ID выполненной викторины
    quiz_id = db.Column(db.Integer, nullable=False, unique=False, index=False)
    # Баллы (<процент выполнения> / 1% * 100), например: 66.67% это 6667
    scores = db.Column(db.Integer, nullable=False, unique=False, index=False)
    # Время выполнения викторины, т.е. когда она была выполнена
    time = db.Column(db.DateTime, nullable=False)


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


def get_email_confirmation_form(user: User):
    """Возвращает экземпляр класса EmailConfirmationForm"""

    if not isinstance(user, User):
        raise TypeError('user must be an instance of User')

    class EmailConfirmationForm(Form):
        """Форма для подтверждения почты"""
        # Поле для почты:
        #   быстрая предварительная проверка на корректность,
        #   проверка на незанятость,
        #   значение по умолчанию берется из user.
        email = StringField('Email', [Optional(),
                                      Email(message='Incorrect email.', check_deliverability=False),
                                      IsEmailFree(validation_exception=user.email)], default=user.email)

        confirmation_code = StringField('Confirmation code', [Optional()])  # Поле для кода подтверждения
        send_code = SubmitField('Send code')  # Кнопка для отправки кода подтверждения
        check_code = SubmitField('Check code')  # Кнопка для проверки кода подтверждения

    return EmailConfirmationForm(request.form)


def get_remove_account_form():
    """Возвращает экземпляр класса DeleteAccountForm"""

    class RemoveAccountForm(Form):
        """Форма для удаления аккаунта"""
        password = PasswordField('Password', [InputRequired(message='Enter password')])
        confirm = BooleanField('Confirm', [InputRequired(message='Please check')])
        submit = SubmitField()

    return RemoveAccountForm(request.form)


class CantSendEmail(Exception):  # Исключение, возникающее из-за невозможности отправки письма
    pass


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


@app.route('/get_strong_password')
def get_strong_password():
    response = make_response(generate_strong_password(), 200)  # Создаем ответ
    response.mimetype = "text/plain"  # Устанавливаем тип ответа
    return response  # Возвращаем ответ


@app.route('/')
def index():
    param = {
        'title': 'Home',
        # Установили заголовок страницы
        'is_authorized': 'user_id' in session
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
    }
    return render_template('index.html', **param)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    param = {
        'title': 'Sign up',
        # Установили заголовок страницы
        'is_authorized': False,
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
        'recommended_password': generate_strong_password()
        # Передали рекомендуемый пароль, чтобы пользователю не пришлось придумывать его самостоятельно
    }
    if request.method == 'POST':
        # Проверка на корректность поученной формы
        if 'name' not in request.form or 'login' not in request.form or 'password' not in request.form:
            param['alert_message'] = 'Fill in all the fields.'
            return render_template('register.html', **param)

        username = request.form['name']
        email = request.form['login']
        password = request.form['password']
        param['inputted_username'] = username
        param['inputted_email'] = email

        if not (username and email and password):  # Проверка на заполнение всех полей формы
            param['alert_message'] = 'Fill in all the fields.'
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
        new_user = User(username=username, email=email, password=hashed_password, status='requires_confirmation')
        db.session.add(new_user)
        db.session.commit()
        session['restricted_user_id'] = new_user.id
        flash('Registration successful! Please confirm your email address.')
        return redirect(url_for('email_confirmation'))
    if 'user_id' in session:
        return redirect(url_for('quiz_selection'))
    if 'restricted_user_id' in session:
        return redirect(url_for('email_confirmation'))
    return render_template('register.html', **param)


@app.route('/email_confirmation', methods=['GET', 'POST'])
def email_confirmation():
    """Страница подтверждения почтового адреса"""
    # При входе на эту страницу ожидается,
    # что пользователь авторизован как ограниченный (status: 'requires_confirmation') пользователь,
    # если же пользователь авторизован как обычный пользователь,
    # то переадресовываем на страницу редактирования аккаунта,
    # если пользователь НЕ авторизован как ограниченный пользователь (т.е. если пользователь НЕ авторизован),
    # то переадресовываем на страницу входа.
    if 'user_id' in session:
        return redirect(url_for('my_account'))
    if 'restricted_user_id' not in session:
        return redirect(url_for('signin'))

    # Получаем пользователя из базы данных
    user = db.session.query(User).filter(User.id == session['restricted_user_id']).first()
    if not user:  # Если пользователь не найден в базе данных, то переадресовываем на страницу входа
        return redirect(url_for('signin'))
    form = get_email_confirmation_form(user)  # Получаем форму для подтверждения почтового адреса
    param = {  # Устанавливаем параметры страницы
        'title': 'Email confirmation',
        # Установили заголовок страницы
        'is_authorized': False,
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
        'email': user.email,
        # Указали email пользователя для отображения в форме
        'code_has_been_sent': False
        # Установили параметру code_has_been_sent значение по умолчанию: False,
        # то есть указали, что код подтверждения не был отправлен.
    }

    # Если получили POST-запрос и форма прошла валидацию
    if request.method == 'POST' and form.validate():
        # При получении этого POST-запроса ожидается,
        # что пользователь авторизован как ограниченный (status: 'requires_confirmation') пользователь,
        # если же пользователь авторизован как обычный пользователь,
        # то переадресовываем на страницу редактирования аккаунта,
        # если пользователь НЕ авторизован как ограниченный пользователь (т.е. если пользователь НЕ авторизован),
        # то переадресовываем на страницу входа.
        if 'user_id' in session:
            return redirect(url_for('my_account'))
        if 'restricted_user_id' not in session:
            return redirect(url_for('signin'))

        # Если в POST-запросе есть поле send_code и значение в нем True (т.е. кнопка отправки кода нажата)
        if 'send_code' in request.form and form.send_code.data:
            # Если в POST-запросе НЕТ поля email или поле email НЕ заполнено,
            # то выводим сообщение: 'Enter the email address.'
            if not ('email' in request.form and form.email.data):
                param['alert_message'] = 'Enter the email address.'
                return render_template('email_confirmation.html', form=form, **param)

            # Пытаемся отправить код на email адрес, который был введен пользователем,
            # если этот email адрес НЕ существует или вовсе НЕ является валидным email адресом,
            # то получаем ошибку CantSendEmail, отлавливаем ее
            # и выводим сообщение: 'Invalid or non-existent email address.'.
            try:
                confirmation_code = send_confirmation_code(form.email.data)
            except CantSendEmail:
                param['alert_message'] = 'Invalid or non-existent email address.'
                return render_template('email_confirmation.html', form=form, **param)

            # Если код подтверждения получилось отправить
            else:
                user.email = form.email.data  # Получаем email из формы
                hashed_code = generate_password_hash(confirmation_code)  # Хэшируем код подтверждения

                # Ищем в базе данных неактуальный код подтверждения,
                # если находим, то удаляем.
                old_code = OneTimeCode.query.filter_by(user_id=user.id).first()
                if old_code:
                    OneTimeCode.query.filter_by(user_id=user.id).delete()
                # Записываем в базу данных актуальный код подтверждения
                new_code = OneTimeCode(user_id=user.id, code=hashed_code)
                db.session.add(new_code)
                db.session.commit()

                param['code_has_been_sent'] = True  # Передаем в шаблон то, что код подтверждения был отправлен
                param['email'] = user.email  # Передаем в шаблон email, для отображения в форме
                return render_template('email_confirmation.html', form=form, **param)

        # Если в POST-запросе есть поле check_code и значение в нем True (т.е. кнопка проверки кода нажата)
        elif 'check_code' in request.form and form.check_code.data:
            # Если в POST-запросе НЕТ поля confirmation_code или поле confirmation_code НЕ заполнено,
            # то выводим сообщение: 'Enter the confirmation code.'.
            if not ('confirmation_code' in form and form.confirmation_code.data):
                param['alert_message'] = 'Enter the confirmation code.'
                param['code_has_been_sent'] = True  # Передаем в шаблон то, что код подтверждения был отправлен
                return render_template('email_confirmation.html', form=form, **param)

            # Получаем актуальный код подтверждения из базы данных,
            # если код подтверждения не найден в базе данных,
            # то переадресовываем на страницу подтверждения почтового адреса.
            one_time_code = OneTimeCode.query.filter_by(user_id=user.id).first()
            if not one_time_code:
                return redirect(url_for('email_confirmation'))

            # Проверяем код подтверждения
            if check_password_hash(one_time_code.code, form.confirmation_code.data.upper()):
                # Если код верный, то:
                # 1) удаляем код подтверждения из базы данных;
                # 2) устанавливаем пользователю статус обычного пользователя (status: 'active');
                # 3) отзываем авторизацию пользователя как ограниченного пользователя;
                # 4) авторизуем пользователя как обычного пользователя;
                # 5) переадресовываем на страницу выбора викторины.
                OneTimeCode.query.filter_by(user_id=user.id).delete()
                user.status = 'active'
                db.session.commit()
                del session['restricted_user_id']
                session['user_id'] = user.id
                return redirect(url_for('quiz_selection'))
            else:
                # Если код неверный, то выводим сообщение: 'Incorrect confirmation code.'.
                param['alert_message'] = 'Incorrect confirmation code.'
                param['code_has_been_sent'] = True  # Передаем в шаблон то, что код подтверждения был отправлен
                # Отображаем страниц с формой и даем возможность заново попытаться ввести код подтверждения.
                return render_template('email_confirmation.html', form=form, **param)

        # Если получен некорректный POST-запрос
        else:
            return redirect(url_for('email_confirmation'))

    # Отображаем страницу с формой подтверждения почтового адреса.
    # Если параметр code_has_been_sent == False (т.е. код подтверждения не был отправлен),
    #   то в форме будет отображаться поле с ранее введенным email, полученным из базы данных,
    #   пользователь может его изменить, если ошибся или передумал,
    #   также будет отображаться кнопка 'Send the code'.
    # Иначе (т.е. код подтверждения был отправлен),
    #   то в форме будет отображаться поле, с ранее введенным email,
    #   доступное только для чтения (т.е. пользователь не может сейчас изменить email);
    #   ещё в форме будет отображено поле для ввода кода подтверждения и кнопка 'Check the code';
    #   также будет отображаться кнопка 'Reset code', переадресовывающая на страницу подтверждения почтового адреса,
    #   важно, что при этом значение параметра code_has_been_sent будет сброшено на значение по умолчанию (false),
    #   (это необходимо для того, чтобы пользователь мог заново отправить код подтверждения, возможно, с другим email).
    return render_template('email_confirmation.html', form=form, **param)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    param = {'title': 'Sign in'}
    if request.method == 'POST':
        # Проверка на корректность поученной формы
        if 'login' not in request.form or 'password' not in request.form:
            param['alert_message'] = 'Fill in all the fields.'
            return render_template('login.html', **param)

        email = request.form['login']
        password = request.form['password']
        if not (email and password):  # Проверка на заполнение всех полей формы
            param['alert_message'] = 'Fill in all the fields.'
            return render_template('login.html', **param)
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                if user.status == 'active':  # Проверяем статус аккаунта
                    session['user_id'] = user.id
                    flash('Login successful!')
                    return redirect(url_for('quiz_selection'))
                elif user.status == 'requires_confirmation':
                    session['restricted_user_id'] = user.id
                    return redirect(url_for('email_confirmation'))
                # Любой другой статус, возможно, заблокирован (не реализовано) или 'не навсегда' удален (не реализовано)
                else:
                    abort(403)
        param['alert_message'] = 'Incorrect username or password. Please try again.'
        return render_template('login.html', **param)

    if 'user_id' in session:  # Если пользователь авторизован как обычный пользователь
        user = User.query.filter_by(id=session['user_id']).first()  # Получаем пользователя из базы данных
        if not user:  # Если пользователь не найден, то отзываем авторизацию и переадресовываем на страницу авторизации
            del session['user_id']
            return redirect(url_for('signin'))
        return redirect(url_for('quiz_selection'))

    if 'restricted_user_id' in session:  # Если пользователь авторизован как ограниченный пользователь
        user = User.query.filter_by(id=session['restricted_user_id']).first()  # Получаем пользователя из базы данных
        if not user:  # Если пользователь не найден, то отзываем авторизацию и переадресовываем на страницу авторизации
            del session['restricted_user_id']
            return redirect(url_for('signin'))
        return redirect(url_for('email_confirmation'))

    return render_template('login.html', **param)


@app.route('/logout')
def logout():
    if 'user_id' in session:
        del session['user_id']
    return redirect('/')


@app.route('/my_account', methods=['GET', 'POST'])
def my_account():
    # Если пользователь не авторизован, то переадресовываем на страницу авторизации
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    changes_successfully_applied = False  # Сообщение об успешном применении изменений
    email_confirmation_required = False  # Сообщение о необходимости подтверждения почты
    validation_errors = []  # Список ошибок валидации
    user = db.session.query(User).filter(User.id == session['user_id']).first()  # Получаем пользователя из базы данных
    if not user:  # Если пользователь не найден, то переадресовываем на страницу авторизации
        return redirect(url_for('signin'))
    form = get_edit_profile_form(user)  # Получаем форму для редактирования профиля пользователя из базы данных
    # Получаем список результатов пользователя из базы данных
    log_of_results = ResultOfQuiz.query.filter_by(user_id=user.id).order_by(ResultOfQuiz.time.desc()).all()

    # Создаем таблицу с результатами
    results_table = []
    for result in log_of_results:
        results_table.append({'name': quizzes_manager.get_quiz_name(result.quiz_id), 'scores': result.scores // 100,
                              'data': f"{result.time:%d %b %Y}", 'time': f"{result.time:%H:%M}"})

    param = {
        'title': 'My account',
        # Указали заголовок страницы
        'user': user,  # Передаем пользователя из базы данных в шаблон
        'user_id': session['user_id'],  # Передаем ID пользователя из базы данных в шаблон, чтобы его отобразить в форме
        'is_authorized': True,
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
        'quizzes_history': results_table,
    }

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
                user.status = 'requires_confirmation'
                user.email = form.email.data  # Сохраняем новый email пользователя, если он был указан в форме
                del session['user_id']
                session['restricted_user_id'] = user.id
                email_confirmation_required = True  # Сообщение о необходимости подтверждения почты
                changes_successfully_applied = True
            if form.new_password.data:
                # Сохраняем новый пароль, если он был указан в форме
                user.password = generate_password_hash(form.new_password.data)
                changes_successfully_applied = True
            db.session.commit()

    param['errors'] = validation_errors
    param['changes_successfully_applied'] = changes_successfully_applied
    param['email_confirmation_required'] = email_confirmation_required
    # Возвращаем шаблон с формой для редактирования профиля пользователя
    return render_template('my_account.html', form=form, **param)


@app.route('/remove_account', methods=['GET', 'POST'])
def remove_account():
    if 'user_id' not in session:  # Если пользователь не авторизован, то переадресовываем на страницу авторизации
        return redirect(url_for('signin'))
    user = User.query.filter_by(id=session['user_id']).first()  # Получаем пользователя из базы данных
    if not user:  # Если пользователь не найден, то переадресовываем на страницу авторизации
        return redirect(url_for('signin'))

    validation_errors = []  # Создаем список ошибок валидации
    form = get_remove_account_form()  # Получаем форму для удаления аккаунта
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            return redirect(url_for('signin'))
        if not check_password_hash(user.password, form.password.data):
            validation_errors.append((ValidationError('Invalid password'), 'wrong_password'))
        if not validation_errors:
            del session['user_id']
            ResultOfQuiz.query.filter_by(user_id=user.id).delete()
            db.session.query(User).filter(User.id == user.id).delete()
            db.session.commit()
            return redirect(url_for('index'))
    param = {
        'title': 'Удаление аккаунта',
        # Указали заголовок страницы
        'is_authorized': True,
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
        'errors': validation_errors
    }
    # Возвращаем шаблон с формой для удаления профиля пользователя
    return render_template('remove_account.html', form=form, **param)


@app.route('/rating_table')
def rating_table():
    # Если пользователь не авторизован, то переадресовываем на страницу авторизации
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    user = User.query.filter_by(id=session['user_id']).first()  # Получаем пользователя из базы данных
    # Если пользователь не найден, то переадресовываем на страницу авторизации
    if not user:
        return redirect(url_for('signin'))

    # Получаем список пользователей, отсортированный по рейтингу
    rating_list = User.query.order_by(User.rating.desc()).all()

    param = {
        'title': 'Rating table',
        # Указали заголовок страницы
        'is_authorized': True,
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
        'rating_list': rating_list,
        'current_user_id': user.id
    }
    return render_template('rating_table.html', **param)


@app.route('/quiz_selection')
def quiz_selection():
    if 'user_id' not in session:  # Если пользователь не авторизован, то переадресовываем на страницу авторизации
        return redirect(url_for('signin'))
    user = User.query.filter_by(id=session['user_id']).first()  # Получаем пользователя из базы данных
    if not user:  # Если пользователь не найден, то переадресовываем на страницу авторизации
        return redirect(url_for('signin'))

    param = {
        'title': 'Quiz selection',
        # Указали заголовок страницы
        'is_authorized': True,
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
        'quizzes_manager': quizzes_manager
        # Передали менеджер викторин в шаблон
    }
    return render_template('quiz_selection.html', **param)


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

    user = User.query.filter_by(id=session['user_id']).first()  # Получаем пользователя из базы данных
    if not user:  # Если пользователь не найден, то переадресовываем на страницу авторизации
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

    # Если пользователь авторизован, то сохраняем результат выполнения викторины
    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        if user:
            # Сохраняем результат выполнения викторины
            save_result_of_quiz(user_id=user.id, quiz_id=session['quiz_id'], total_questions=total_questions,
                                number_of_correct=num_correct)
            # Обновляем рейтинг пользователя
            update_rating(user_id=user.id)

    return render_template('quiz_results.html', num_correct=num_correct, total_questions=total_questions)


@app.route('/new_quiz')
def new_quiz():
    params = {
        'title': 'New quiz',
        # Указали заголовок страницы
        'is_authorized': 'user_id' in session
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
    }
    return render_template('new_quiz.html', **params)  # Отображаем заглушку


@app.errorhandler(404)
def page_not_found(e):
    param = {
        'title': 'Page not found',
        # Указали заголовок страницы
        'is_authorized': 'user_id' in session
        # Указали, что пользователь не авторизован как обычный пользователь
        # (нужно для правильного отображения шапки сайта)
    }
    return render_template('404.html', **param), 404  # Отображение ошибки: страница не найдена


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    quizzes_manager = QuizzesManager('./quizzes')  # Подлюкам менеджер викторин
    port = int(environ.get("PORT", 5000))  # Получение порта
    app.run(host='0.0.0.0', port=port, debug=True)  # Запуск приложения
