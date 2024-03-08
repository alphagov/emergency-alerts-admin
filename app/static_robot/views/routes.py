from app.static_robot import static


@static.route("/robots.txt")
def send_robots_txt():
    return "User-agent: *\nDisallow: /"
