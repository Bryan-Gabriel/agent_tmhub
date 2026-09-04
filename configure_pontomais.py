from getpass import getpass
from pathlib import Path

from dotenv import set_key

def main():
    login = input("Login/CPF Ponto Mais: ").strip()
    password = getpass("Senha Ponto Mais: ")
    if not login or not password:
        raise SystemExit("Login e senha são obrigatórios.")
    env_file = Path(__file__).with_name(".env")
    set_key(env_file, "PONTOMAIS_LOGIN", login, quote_mode="auto")
    set_key(env_file, "PONTOMAIS_PASSWORD", password, quote_mode="auto")
    print("Credenciais gravadas no .env local, que é ignorado pelo Git.")


if __name__ == "__main__":
    main()
