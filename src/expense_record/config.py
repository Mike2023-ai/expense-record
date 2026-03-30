"""Application configuration."""


class Config:
    SECRET_KEY = "dev"


class TestConfig(Config):
    TESTING = True

