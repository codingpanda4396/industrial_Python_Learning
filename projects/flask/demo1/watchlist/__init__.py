from flask import Flask, flash, redirect, url_for
from flask import render_template
from flask import request
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user

from projects.flask.demo1.app import User



app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:439695@192.168.56.10/flask_learning'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'  # 等同于 app.secret_key = 'dev'

login_manager = LoginManager(app)  # 实例化扩展类

@login_manager.user_loader
def load_user(user_id):  # 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id))  # 用 ID 作为 User 模型的主键查询对应的用户
    return user  # 返回用户对象
login_manager.login_view = 'login'

db= SQLAlchemy(app)