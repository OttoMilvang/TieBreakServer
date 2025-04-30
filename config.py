from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    INSTALLER_USERID: str = ""
    INSTALLER_PWD: str = ""
    MYSQL_HOST: str = ""
    MYSQL_TCP_PORT: int
    MYSQL_DATABASE: str = ""
    MYSQL_PWD: str = ""
    MYSQL_ROOT_PASSWORD: str = ""


def get_settings() -> Settings:
    return Settings()
    # pass
