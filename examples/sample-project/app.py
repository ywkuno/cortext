from helpers import greet


class App:
    def run(self):
        return greet("Tabi")


def main():
    app = App()
    print(app.run())


if __name__ == "__main__":
    main()
