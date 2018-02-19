#coding: utf8

import logging
import time

import pymysql
import pymysql.cursors
import requests
import telebot

import config
import utils

bot = telebot.TeleBot(token = config.token)

class DB:
    def __init__(self, host, user, db, password):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.charset = 'utf8mb4'
        self.cursorclass = pymysql.cursors.DictCursor

class DataConn:
    def __init__(self, db_obj):
        self.host = db_obj.host
        self.user = db_obj.user
        self.password = db_obj.password
        self.db = db_obj.db
        self.charset = db_obj.charset
        self.cursorclass = db_obj.cursorclass

    def __enter__(self):
        self.conn = pymysql.connect(
            host = self.host,
            user = self.user,
            password = self.password,
            db = self.db,
            charset = self.charset,
            cursorclass = self.cursorclass
        )
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        if exc_val:
            raise
db = DB(
    host = config.host,
    user = config.user,
    password = config.password,
    db = config.db
)

log_name = 'logs.txt'
f = open(log_name,'w')
f.close()
print('Файл логов создан')

telebot_logger = logging.getLogger('telebot')
mysql_info = logging.getLogger('mysql')
main_info = logging.getLogger('main_info')
report_info = logging.getLogger('reports')
print('Список логгеров создан')

logging.basicConfig(
                    format='%(filename)s [LINE:%(lineno)-3d]# %(levelname)-8s - %(name)-9s [%(asctime)s] - %(message)-50s ',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level = logging.INFO
                    )

def ban_sticker(msg, sticker_id):
    """
    Банит стикер\n
    :param msg:\n
    :param sticker_id:\n
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM `banned_stickers` WHERE `chat_id` = {id} AND `sticker_id` = {sticker_id}'.format(
            id = msg.chat.id,
            sticker_id = sticker_id
        )
        cursor.execute(sql)
        res = cursor.fetchone()
        if res is None:
            sql = 'INSERT INTO `banned_stickers` (`chat_id`, `chat_name`, `sticker_id`, `ban_time`) VALUES ("{chat_id}", "{chat_name}", "{sticker_id}", "{ban_time}"'.format(
                chat_id = msg.chat.id,
                chat_name = msg.chat.title,
                sticker_id = sticker_id,
                ban_time = int(time.time())
            )
            sql = sql
            cursor.execute(sql)
            conn.commit()
        else:
            if res != msg.chat.title:
                sql = 'SELECT * FROM `banned_stickers` WHERE `chat_id` = {id}'.format(
                    id = msg.chat.id
                )
                sql = sql
                cursor.execute(sql)
                res = cursor.fetchall()
                for i in res:
                    sql = 'UPDATE `banned_stickers` SET `chat_name` = {chat_name} WHERE `chat_id` = {id}'.format(
                        chat_name = msg.chat.title,
                        id = msg.chat.id
                    )
                    sql = sql
                    cursor.execute(sql)
                    conn.commit()

def unban_sticker(msg, sticker_id):
    """
    Разбанивает стикер\n
    :param msg:\n
    :param sticker_id:\n
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM `banned_stickers` WHERE `chat_id` = {id} and `sticker_id` = {sticker_id}'.format(
            id = msg.chat.id,
            sticker_id = sticker_id
        )
        cursor.execute(sql)
        res = cursor.fetchone()
        if res is not None:
            sql = 'DELETE FROM `banned_stickers` WHERE `chat_id` = {id} AND `sticker_id` = {sticker_id}'.format(
                id = msg.chat.id,
                sticker_id = sticker_id
            )
            sql = sql
            cursor.execute(sql)
            conn.commit()
            return True
        else:
            return False

def get_creator(msg):
    """
    Возвращает объект создателя чата\n
    :param msg:\n
    """
    creator = bot.get_chat_administrators(msg.chat.id)[0].user
    for i in bot.get_chat_administrators(msg.chat.id):
        if i.status == 'creator':
            creator = i.user
    return creator

def register_new_user(call, lang):
    """
    Регистрирует нового пользователя\n
    :param call:\n
    :param lang:\n
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM users WHERE `user_id` = {id}'.format(
            id = call.from_user.id
        )
        cursor.execute(sql)
        res = cursor.fetchone()
        sec_name = 'None'
        try:
            sec_name = call.from_user.second_name
        except Exception as e:
            sec_name = 'None'
            logging.error(e)
        if res is None:
            sql = 'INSERT INTO `users` (`user_id`, `registration_time`, `first_name`, `second_name`, `language`) VALUES ("{id}", "{curr_time}", "{first_name}", "{second_name}", "{lang}")'.format(
                id = call.from_user.id,
                curr_time = int(time.time()),
                first_name = call.from_user.first_name,
                second_name = sec_name,
                lang = lang
            )
            cursor.execute(sql)
            conn.commit()
            sql = 'INSERT INTO `user_settings` (`user_id`, `registration_time`, `language`) VALUES ("{id}", "{curr_time}", "{language}")'.format(
                id = call.from_user.id,
                curr_time = int(time.time()),
                language = lang
            )
            cursor.execute(sql)
            conn.commit()
            utils.notify_new_user(call)
        else:
            sql = 'UPDATE `user_settings` SET `language` = "{lang}" WHERE `user_id` = "{id}"'.format(
                lang = lang,
                id = call.from_user.id
            )
            cursor.execute(sql)
            conn.commit()

def register_new_chat(msg):
    """
    Регистрирует новый чат\n
    :param msg:\n
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM chats WHERE `chat_id` = {id}'.format(
            id = msg.chat.id
        )
        cursor.execute(sql)
        res = cursor.fetchone()
        if res is None:
            creator = get_creator(msg)
            sql = 'INSERT INTO `chats` (`chat_id`, `chat_name`, `creator_name`, `creator_id`, `chat_members_count`, `registration_time`) VALUES ("{chat_id}", "{chat_name}", "{creator_name}", "{creator_id}", "{count}", "{curr_time}")'.format(
                chat_id = msg.chat.id,
                chat_name = msg.chat.title,
                creator_name = creator.first_name,
                creator_id = creator.id,
                count = bot.get_chat_members_count(msg.chat.id),
                curr_time = int(time.time())
            )
            sql = sql
            try:
                print(sql)
                cursor.execute(sql)
                conn.commit()
                print(sql)
            except Exception as e:
                logging.error('error')
                logging.error(sql)
            sql = 'INSERT INTO `group_settings` (`chat_id`, `language`, `get_notifications`, `greeting`, `delete_url`, `delete_system`) VALUES ("{chat_id}", "{language}", "{get_notifications}", "{greeting}", "{delete_url}", "{delete_system}")'.format(
                chat_id = msg.chat.id,
                language = 'ru',
                get_notifications = 1,
                greeting = r'ТЕСТОВОЕ ОПОВЕЩЕНИЕ',
                delete_url = 0,
                delete_system = 1
            )
            sql = sql
            try:
                print(sql)
                cursor.execute(sql)
                conn.commit()
                print(sql)
            except Exception as e:
                logging.error('error')
                logging.error(sql)
            utils.notify_new_chat(msg)

def get_users_count():
    """
    Возвращает количество пользователей в базе\n
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM users'
        cursor.execute(sql)
        res = cursor.fetchall()
        return len(res)

def get_chats_count():
    """
    Возвращает количество чатов в базе\n
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM chats'
        cursor.execute(sql)
        res = cursor.fetchall()
        return len(res)

def get_user_param(msg, column):
    """
    Возвращает определенный параметр пользовательских настроек
    :param msg:
    :param column:
    """
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT `{column}` FROM user_settings WHERE `user_id` = "{id}"'.format(
            column = column,
            id = msg.chat.id
        )
        sql = sql
        print()
        print(sql)
        print()
        cursor.execute(sql)
        res = cursor.fetchone()
        return res[column]

def set_user_param(msg, column, state):
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'UPDATE `user_settings` SET `{column}` = "{state}" WHERE `user_id` = "{id}"'.format(
            column = column,
            state = state,
            id = msg.chat.id
        )
        sql = sql
        cursor.execute(sql)
        conn.commit()

def get_group_param(msg, column):
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT `{column}` FROM group_settings WHERE `chat_id` = {id}'.format(
            column = column,
            id = msg.chat.id
        )
        sql = sql
        cursor.execute(sql)
        res = cursor.fetchone()
        return res[column]

def set_group_param(msg, column, state):
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'UPDATE `group_settings` SET `{column}` = "{state}" WHERE `chat_id` = {id}'.format(
            column = column,
            state = state,
            id = msg.chat.id
        )
        cursor.execute(sql)
        conn.commit()

def is_user_new(msg):
    with DataConn(db) as conn:
        cursor = conn.cursor()
        sql = 'SELECT * FROM users WHERE `user_id` = {id}'.format(
            id = msg.from_user.id
        )
        sql = sql
        cursor.execute(sql)
        r = cursor.fetchone()
        if r is None:
            res = True
        else:
            res = False
        return res