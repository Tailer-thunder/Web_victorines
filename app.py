from flask import Flask, render_template, request, redirect, url_for, flash, session
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

from flask import jsonify, request

@app.route('/get_time_left', methods=['GET'])
def get_time_left():
    time_left = "10:00"
    return jsonify({'time_left': time_left})
def get_questions_for_quiz(quiz_id):
    if quiz_id.lower() == 'breaking_bad':
        return [
            {"question": "What is the name of the main character in the TV series 'Breaking Bad'?", "answers": ["Walter White", "Jesse Pinkman", "Saul Goodman", "Mike Ehrmantraut"], "correct_answer": "Walter White", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "In which city do the main events of the series take place?", "answers": ["Chicago", "Los Angeles", "Albuquerque", "Miami"], "correct_answer": "Albuquerque", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "Which character is a lawyer and private investigator?", "answers": ["Skyler White", "Saul Goodman", "Mike Ehrmantraut", "Gus Fring"], "correct_answer": "Saul Goodman", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "Who is the partner of Walter White in the methamphetamine business?", "answers": ["Jesse Pinkman", "Hank Schrader", "Walter Jr.", "Skyler White"], "correct_answer": "Jesse Pinkman", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "What is the nickname of Walter White's methamphetamine?", "answers": ["Blue Crystal", "Green Lantern", "Pink Panther", "White Lightning"], "correct_answer": "Blue Crystal", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "Who is the owner of the Los Pollos Hermanos restaurant chain?", "answers": ["Walter White", "Jesse Pinkman", "Saul Goodman", "Gustavo Fring"], "correct_answer": "Gustavo Fring", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "What is the profession of Walter White before he starts cooking meth?", "answers": ["High school chemistry teacher", "Lawyer", "Car mechanic", "Police officer"], "correct_answer": "High school chemistry teacher", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "What is the name of Walter White's brother-in-law who works for the DEA?", "answers": ["Hank Schrader", "Ted Beneke", "Tuco Salamanca", "Mike Ehrmantraut"], "correct_answer": "Hank Schrader", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "Who is the distributor of the blue meth in the later seasons?", "answers": ["Gus Fring", "Tuco Salamanca", "Hector Salamanca", "Jack Welker"], "correct_answer": "Gus Fring", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"},
            {"question": "What is the name of the spin-off prequel series to 'Breaking Bad' featuring Saul Goodman?", "answers": ["Better Call Saul", "The Saul Show", "Legal Eagle", "Goodman's Gambit"], "correct_answer": "Better Call Saul", "image": "https://i.postimg.cc/gcyNmNmh/brba.jpg"}
        ]
    elif quiz_id.lower() == 'house':
        return [
            {"question": "What is the name of the main character in the TV series 'House'?", "answers": ["Gregory House", "James Wilson", "Lisa Cuddy", "Robert Chase"], "correct_answer": "Gregory House", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is Dr. House's specialty in medicine?", "answers": ["Oncology", "Diagnostic Medicine", "Neurology", "Cardiology"], "correct_answer": "Diagnostic Medicine", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "Who is Dr. House's best friend and colleague?", "answers": ["Lisa Cuddy", "James Wilson", "Allison Cameron", "Eric Foreman"], "correct_answer": "James Wilson", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is the name of Dr. House's team of diagnosticians?", "answers": ["Surgical Team", "Diagnostic Team", "Emergency Team", "Therapy Team"], "correct_answer": "Diagnostic Team", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is Dr. House's favorite catchphrase?", "answers": ["Everybody lies", "Life is pain", "No pain, no gain", "Pain is temporary"], "correct_answer": "Everybody lies", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is the name of the hospital where Dr. House works?", "answers": ["Mayfield Psychiatric Hospital", "Seattle Grace Hospital", "Princeton-Plainsboro Teaching Hospital", "New Jersey General Hospital"], "correct_answer": "Princeton-Plainsboro Teaching Hospital", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is Dr. House's addiction?", "answers": ["Cocaine", "Morphine", "Vicodin", "Heroin"], "correct_answer": "Vicodin", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "Who is Dr. House's boss at the hospital?", "answers": ["James Wilson", "Allison Cameron", "Eric Foreman", "Lisa Cuddy"], "correct_answer": "Lisa Cuddy", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is the nickname given to Dr. House by his team?", "answers": ["House", "Boss", "Doc", "Greg"], "correct_answer": "House", "image": "https://i.postimg.cc/P56dcWCs/House.png"},
            {"question": "What is Dr. House's first name?", "answers": ["John", "Robert", "Gregory", "David"], "correct_answer": "Gregory", "image": "https://i.postimg.cc/P56dcWCs/House.png"}
        ]
    elif quiz_id.lower() == 'history and culture of japan':
        return [
            {"question": "What is the name of Japanese traditional clothing?", "answers": ["Hanbok", "Kimono", "Sari", "Cheongsam"], "correct_answer": "Kimono", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is sakura in Japanese culture?", "answers": ["Japanese holiday", "Geographic name", "Japanese military equipment", "Cherry blossoms"], "correct_answer": "Cherry blossoms", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is the name of the Japanese art of decorating objects with gold or silver?", "answers": ["Origami", "Ikebana", "Ukiyo-e", "Maki-e"], "correct_answer": "Maki-e", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is a samurai?", "answers": ["Japanese dance", "Japanese tea", "Japanese warrior", "Japanese dish"], "correct_answer": "Japanese warrior", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is the name of the Japanese traditional theater genre in which actors perform folk tales and legends?", "answers": ["Noh", "Kabuki", "Bunraku", "Enka"], "correct_answer": "Kabuki", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is the name of the Japanese tea ceremony?", "answers": ["Sushi", "Izakaya", "Sake", "Chado"], "correct_answer": "Chado", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "Which day is celebrated as the National Emperor's Birthday Holiday in Japan?", "answers": ["May 1st", "November 11", "February 23", "April 29"], "correct_answer": "April 29", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is the name of the classic Japanese folding knife?", "answers": ["Katana", "Wakizashi", "Tanto", "Higonokami"], "correct_answer": "Katana", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is a geisha in Japanese culture?", "answers": ["Female profession", "Japanese trampoline", "Japanese Beatles", "Japanese instrument"], "correct_answer": "Female profession", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"},
            {"question": "What is the name of the Japanese art of arranging bouquets of fresh flowers?", "answers": ["Sumi-e", "Mizuhiki", "Ikebana", "Kintsugi"], "correct_answer": "Ikebana", "image": "https://i.postimg.cc/Kj99F8Bz/japan.jpg"}
        ]
    elif quiz_id.lower() == 'history of cinema':
        return [
            {"question": "Who directed the movie 'Breakfast at Tiffany's'?", "answers": ["Stanley Kubrick", "Alfred Hitchcock", "Billy Wilder", "Blake Edwards"], "correct_answer": "Blake Edwards", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "Which film was the first color film to win the Academy Award for Best Picture?", "answers": ["The Wizard of Oz", "The Sound of Music", "Ben-Hur", "The Citadel"], "correct_answer": "The Wizard of Oz", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "Who played the main role in the movie 'The Godfather'?", "answers": ["Robert De Niro", "Al Pacino", "Marlon Brando", "Johnny Depp"], "correct_answer": "Marlon Brando", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "What is the name of the first film made by the Lumiere brothers?", "answers": ["Train arrival at La Ciotat station", "Cleaning the floor", "Breakfast", "Lumiere family"], "correct_answer": "Train arrival at La Ciotat station", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "Which film is the highest-grossing film in the history of cinema?", "answers": ["Avengers: Endgame", "Avatar", "Star Wars: The Force Awakens", "Titanic"], "correct_answer": "Titanic", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "In what year was Disney's first animated feature film released?", "answers": ["1937", "1950", "1963", "1989"], "correct_answer": "1937", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "Who made the movie 'Some Like It Hot'?", "answers": ["Francis Ford Coppola", "Stanley Donen", "Damien Chazelle", "Billy Wilder"], "correct_answer": "Stanley Donen", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "What movie starred Charlize Theron as a painfully lonely astronaut?", "answers": ["Alien", "March", "Gravity", "Oblivion"], "correct_answer": "March", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "Who played the main male role in the film 'Insomnia' (2002)?", "answers": ["Colin Farrell", "Al Pacino", "Leonardo DiCaprio", "Billy Wilder"], "correct_answer": "Al Pacino", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"},
            {"question": "Which film brought actor Tom Hanks his first Academy Award for Best Actor?", "answers": ["Saving Private Ryan", "Forrest Gump", "The Green Mile", "Ghost"], "correct_answer": "Forrest Gump", "image": "https://i.postimg.cc/ncgk1516/cinema.jpg"}
        ]
    elif quiz_id.lower() == 'geography of france':
        return [
            {"question": "Which river flows through Paris?", "answers": ["Seine", "Rhine", "Loire", "Garonne"], "correct_answer": "Seine", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "What is the name of the highest peak in France?", "answers": ["Mont Blanc", "Elbrus", "Matterhorn", "Eiger"], "correct_answer": "Mont Blanc", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "Which city is the capital of France?", "answers": ["Marseille", "Lyon", "Toulouse", "Paris"], "correct_answer": "Paris", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "Which lake is located on the border of France and Switzerland?", "answers": ["Geneva", "Constance", "Como", "Garda"], "correct_answer": "Geneva", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "Which region of France is famous for its wineries?", "answers": ["Loire", "Alsace", "Bordeaux", "Normandy"], "correct_answer": "Bordeaux", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "Which sea washes the southern coast of France?", "answers": ["Mediterranean", "Black", "Caspian", "Azure"], "correct_answer": "Mediterranean", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "Which mountain range lies in the southeast of France?", "answers": ["Pyrenees", "Alps", "Carpathians", "Apennines"], "correct_answer": "Alps", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "What is the name of the archipelago in the Mediterranean Sea that belongs to France?", "answers": ["Corsica", "Sardinia", "Sicily", "Balearics"], "correct_answer": "Corsica", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "What is the name of the river that flows through Lyon?", "answers": ["Loire", "Seine", "Rhone", "Garonne"], "correct_answer": "Rhone", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"},
            {"question": "What is the name of the city located on the Cote d'Azur of France?", "answers": ["Nice", "Marseille", "Cannes", "Monaco"], "correct_answer": "Nice", "image": "https://i.postimg.cc/4yr9zCTP/franch.jpg"}
        ]
    elif quiz_id.lower() == 'world literature':
        return [
            {"question": "Who wrote the novel 'Crime and Punishment'?", "answers": ["Fyodor Dostoevsky", "Leo Tolstoy", "Ivan Turgenev", "Alexander Pushkin"], "correct_answer": "Fyodor Dostoevsky", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "What year was Leo Tolstoy's War and Peace published?", "answers": ["1869", "1872", "1867", "1878"], "correct_answer": "1869", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "What is the name of the chronicle novel by Gabriel García Márquez?", "answers": ["Odyssey", "War and Peace", "One Hundred Years of Solitude", "The Brothers Karamazov"], "correct_answer": "One Hundred Years of Solitude", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "Who is the main character of the novel 'The Master and Margarita' by Mikhail Bulgakov?", "answers": ["Professor", "Artist", "Writer", "Devil"], "correct_answer": "Devil", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "Who wrote the story 'Alice in Wonderland'?", "answers": ["Jonathan Swift", "Lewis Carroll", "Oscar Wilde", "Charles Dickens"], "correct_answer": "Lewis Carroll", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "What is the name of George Orwell's dystopian novel?", "answers": ["1984", "Roasted Orange", "Gone with the Wind", "The One Who Runs the Maze"], "correct_answer": "1984", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "Who is the author of the novel 'Harry Potter and the Philosopher's Stone'?", "answers": ["John R. R. Tolkien", "JK Rowling", "George R. R. Martin", "Suzanne Collins"], "correct_answer": "JK Rowling", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "Which work of Jules Verne was the first in the 'Mysterious Island' cycle?", "answers": ["Twenty Thousand Leagues Under the Sea", "Earth on the Moon", "Robinson Crusoe", "Five Weeks in a Balloon"], "correct_answer": "Twenty Thousand Leagues Under the Sea", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "What was the name of the count in the novel 'Monte Cristo' by Alexandre Dumas?", "answers": ["Count Rochefort", "Count de Leon", "Count Argon", "Count Edmond"], "correct_answer": "Count Edmond", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"},
            {"question": "What is the name of Nellie Bly's autobiographical book about life in Dark Matter?", "answers": ["Caught Moon", "Ships in the Desert", "Early Mornings", "Hands of Sand"], "correct_answer": "Ships in the Desert", "image": "https://i.postimg.cc/fLytpWz5/Literatyra.jpg"}
        ]
    else:
        return None

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
                session['user_id'] = user.id
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

@app.route('/start_quiz/<quiz_id>')
def start_quiz(quiz_id):
    if quiz_id.lower() == 'breaking_bad' or quiz_id.lower() == 'house' or quiz_id.lower() == 'history and culture of japan' or quiz_id.lower() == 'history of cinema' or quiz_id.lower() == 'geography of france' or quiz_id.lower() == 'world literature':
        session['quiz_id'] = quiz_id
        return redirect(url_for('quiz_question', quiz_id=quiz_id, question_number=1))
    else:
        return "Invalid quiz"

@app.route('/quiz/<quiz_id>/<int:question_number>', methods=['GET', 'POST'])
def quiz_question(quiz_id, question_number):
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('Please log in to access the quiz.', 'error')
        return redirect(url_for('login'))

    questions = get_questions_for_quiz(quiz_id)
    if questions is None:
        return "Invalid quiz"

    if request.method == 'POST':
        selected_answer = request.form['answer']
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
    return render_template('question.html', quiz_id=quiz_id, question_number=question_number, question=question['question'], answers=question['answers'], image=question['image'])


@app.route('/quiz_results')
def quiz_results():
    num_correct = session.get('num_correct', 0)

    total_questions = 0
    if 'quiz_id' in session:
        quiz_id = session['quiz_id']
        questions = get_questions_for_quiz(quiz_id)
        if questions is not None:
            total_questions = len(questions)

    session.pop('num_correct', None)
    return render_template('quiz_results.html', num_correct=num_correct, total_questions=total_questions)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
