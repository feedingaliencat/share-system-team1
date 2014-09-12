#!/usr/bin/env python
#-*- coding: utf-8 -*-

from peewee import CharField, DoubleField, BlobField, ForeignKeyField
import ConfigParser
import peewee

from server import CONFIG


config = ConfigParser.ConfigParser()
config.read(CONFIG)

db = peewee.PostgresqlDatabase(
    config.get("database", "db_name"),
    user=config.get("database", "db_user"),
    password=config.get("database", "db_password"),
    host=config.get("database", "db_host")
)


class DBModel(peewee.Model):
    class Meta:
        database = db


class User(DBModel):
    username = CharField(unique=True)
    psw = CharField()
    timestamp = DoubleField()


class File(DBModel):
    server_path = CharField(unique=True)
    md5 = CharField(null=True)
    timestamp = DoubleField()
    content = BlobField(null=True)


class Path(DBModel):
    user = ForeignKeyField(User, related_name="paths")
    server_path = ForeignKeyField(File, related_name="client_paths")
    client_path = CharField()


def connect_db():
    db.create_tables([User, File, Path], safe=True)
