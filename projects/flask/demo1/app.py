from flask import Flask
from flask import render_template
from flask import request

app=Flask(__name__)

@app.route("/user/<username>")
def user(username):
    return render_template("hello.html", name=username)

if __name__=="__main__":
    app.run(debug=True)


