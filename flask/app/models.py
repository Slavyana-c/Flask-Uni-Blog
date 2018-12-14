# models.py, implemented by following the tutorials from:
# Flask Web Development by Miguel Grinberg (First Edition) and
# Flask Tutorials by Corey Schafer
# (online) https://www.youtube.com/playlist?list=PL-osiE80TeTs4UjLw5MM6OjgkjFeUxCYH

from app import db, login_manager, app, logger
from datetime import datetime
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'),
    primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'),
    primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# The User database model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)    
    username = db.Column(db.String(20), unique=True, nullable=False)
    profile_image = db.Column(db.String(20), nullable=False, default='default.jpg')
    # Link to the posts
    posts = db.relationship('Post', backref='author', lazy=True)

    followed = db.relationship('Follow',
        foreign_keys=[Follow.follower_id],
        backref=db.backref('follower', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan')

    followers = db.relationship('Follow',
        foreign_keys=[Follow.followed_id],
        backref=db.backref('followed', lazy='joined'),
        lazy='dynamic',
        cascade='all, delete-orphan')

    def get_reset_token(self, exp_sec=900):
        s = Serializer(app.config['SECRET_KEY'], exp_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')
    
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        # Could have expired
        try:
            user_id = s.loads(token)['user_id']
        except:
            logger.error('Cannot use expired/invalid token!')
            return None
        return User.query.get(user_id)

# The Post database model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)    
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Link to the users
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

