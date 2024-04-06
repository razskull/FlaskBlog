import os
import json
from urllib.parse import quote_plus, urlencode
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, render_template, url_for, session, redirect, abort
from flask import jsonify, request
from sqlalchemy.orm import joinedload

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f51c12faac358e25a495e3d7f7581227'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
db = SQLAlchemy(app)

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

oauth = OAuth(app)

oauth.register(
	"auth0",
	client_id=os.environ.get("AUTH0_CLIENT_ID"),
	client_secret=os.environ.get("AUTH0_CLIENT_SECRET"),
	client_kwargs={
		"scope": "openid profile email",
	},
	server_metadata_url=f'https://{os.environ.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    by = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    time = db.Column(db.String(255), nullable=False)
    likes = db.relationship('LikesDislikes', backref = 'news', lazy = True)

    def delete_news(self):
        """
        Allows for the deletion of news articles from the database
        """
        LikesDislikes.query.filter_by(news_id=self.id).delete()
        db.session.delete(self)
        db.session.commit()

    def get_likes_count(self):
        """
        Return a count of the likes
        """
        return LikesDislikes.query.filter_by(news_id=self.id, likes=True).count()

    def get_dislikes_count(self):
        """
        Return a count of the dislikes
        """
        return LikesDislikes.query.filter_by(news_id=self.id, likes=False).count()

    def __repr__(self):
        """
        Return a string representation of the News object.
        """
        return f"News('{self.id}','{self.title}','{self.by}','{self.time}')"

class LikesDislikes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False)
    likes = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        """
        Return a string representation of the LikesDislikes object.
        """
        return f"Likes('{self.id}','{self.news_id}','{self.likes}')"

@app.route("/")
@app.route("/news")
def news():
    """
	Display a paginated list of news items.
    """
    page = request.args.get('page', 1, type=int)
    with app.app_context():
	       news_items = News.query.options(joinedload(News.likes)
	       	).order_by(News.time.desc()
	       	).group_by(News.id).paginate(page=page, per_page=5)
    return render_template('news.html', title='News', news_items=news_items, session=session.get('user'), pretty=json.dumps(session.get('user')))

@app.route("/like_news/<int:news_id>", methods=["GET","POST"])
def like_news(news_id):
    """
    Handle the liking of a news item.
    """
    news_item = News.query.get(news_id)
    like=LikesDislikes(news_id=news_item.id, likes=True)
    db.session.add(like)
    db.session.commit()
    return redirect('/news')

@app.route("/dislike_news/<int:news_id>", methods=["GET","POST"])
def dislike_news(news_id):
    """
    Handle the disliking of a news item.
    """
    news_item = News.query.get(news_id)
    dislike=LikesDislikes(news_id=news_item.id, likes=False)
    db.session.add(dislike)
    db.session.commit()
    return redirect('/news')

@app.route("/newsfeed", methods=["GET"])
def newsfeed():
    """
	Provide a JSON representation of the latest news items.
	"""
    k = int(request.args.get("k", 30))

    latest_news = News.query.order_by(News.time.desc()).limit(k).all()

    news_list = []
    for news_item in latest_news:
        news_dict={
            "title": news_item.title,
            "url": news_item.url,
            "by": news_item.by,
            "score": news_item.score,
            "time": news_item.time
        }
        news_list.append(news_dict)

    return jsonify(news_list)

@app.route("/about")
def about():
    """
	Display information about the application.
	"""
    return render_template(
        'about.html',
        title='About',
        session=session.get('user'),
        pretty=json.dumps(session.get('user'))
    )

@app.route("/login")
def login():
    """
    Redirect to the Auth0 login page.
    """
    return oauth.auth0.authorize_redirect(
		redirect_uri=url_for("callback", _external=True)
	)

@app.route("/register")
def register():
    """
    Redirect to the Auth0 registration page.
    """
    return oauth.auth0.authorize_redirect(
		redirect_uri=url_for("callback", _external=True),
		screen_hint="signup"
	)

@app.route("/callback", methods=["GET", "POST"])
def callback():
    """
	Handle the callback from the Auth0 authentication.
	"""
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

@app.route("/logout")
def logout():
    """
	Handle the logout of the user
	"""
    session.clear()
    return redirect(
		"https://" + os.environ.get("AUTH0_DOMAIN")
		+ "/v2/logout?"
		+ urlencode(
			{
				"returnTo": url_for("home", _external=True),
				"client_id": os.environ.get("AUTH0_CLIENT_ID"),
			},
			quote_via=quote_plus,
		)
	)

@app.route("/account")
def account():
    """
    Handle the displaying of current user's account info
    """
    userinfo = session.get("user")
    if not userinfo:
        return redirect("/login")

    return render_template(
		"account.html",
		title='Account',
		session=session.get('user'),
		pretty=json.dumps(session.get('user'))
		)

@app.route("/admin")
def admin():
    """
    Handle the admin view
    """
    userinfo = session.get("user")
    if not userinfo:
        abort(403)
    page = request.args.get('page', 1, type=int)
    with app.app_context():
        news_items = News.query.options(joinedload(News.likes)
        	).order_by(News.time.desc()
        	).group_by(News.id).paginate(page=page, per_page=5)
    return render_template(
		'admin.html',
		title='Admin View',
		news_items=news_items,
		session=session.get('user'),
		pretty=json.dumps(session.get('user'))
		)

@app.route("/admin/delete_news/<int:news_id>", methods=["GET", "POST"])
def delete_news(news_id):
	"""
    Handle the deletion of news articles in the admin view
    """
	userinfo = session.get("user")
	if not userinfo:
		abort(403)

	news_item = News.query.get(news_id)
	if news_item:
		news_item.delete_news()
		return redirect(url_for("admin"))

	abort(404)

if __name__ == '__main__':
	with app.app_context():
		db.create_all()
	app.run(host='0.0.0.0',debug=True)