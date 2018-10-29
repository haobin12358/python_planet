# -*- coding: utf-8 -*-
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import scoped_session, sessionmaker

from planet.common.base_model import mysql_engine, Base

from planet.models import *


def create_table():
    Base.metadata.create_all(mysql_engine)


def drop_table():
    Base.metadata.drop_all(mysql_engine)


if __name__ == '__main__':
    create_table()
