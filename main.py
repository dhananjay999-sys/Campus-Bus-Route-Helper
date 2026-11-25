import os
import sys

from busapp.logic import RouteBook
from busapp.storage import load_routes
from busapp.ui import App, yellow

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 or newer is required.")
    data_path = os.environ.get("BUS_DATA", os.path.join(HERE, "data", "routes.json"))
    routes, notes = load_routes(data_path)
    for n in notes:
        print(yellow("! " + n))
    app = App(RouteBook(routes), data_path,
              os.path.join(HERE, "exports"), os.path.join(HERE, "logs"))
    app.run()


if __name__ == "__main__":
    main()
