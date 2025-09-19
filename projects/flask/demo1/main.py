from flask import Flask
from flask import render_template
from flask import request

app=Flask(__name__)

@app.route("/")
def hello():
    return "Hello,Flask!"

@app.route("/user/<username>")
def user(username):
    return render_template("hello.html", name=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        return f"Welcome, {username}!"
    return '''
        <form method="post">
            <input name="username">
            <input type="submit">
        </form>
    '''

if __name__=="__main__":
    app.run(debug=True)


