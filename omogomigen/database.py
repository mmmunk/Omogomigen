# This file is part of the project "Omogomigen" which is licensed under
# the zlib License (see LICENSE file). Please include every file from
# the project when distributing. Copyright (C) 2019 Thomas Munk.

import sqlite3
import time

SORT_DATEDUE = 1
SORT_DATEDONE = 2
SORT_TASKNAME = 3
SORT_PERSON = 4

connection = None


def connect(filename):
	global connection
	connection = sqlite3.connect(filename)
	#connection.set_trace_callback(print)
	connection.row_factory = sqlite3.Row
	cr = connection.cursor()
	cr.execute(
		'CREATE TABLE IF NOT EXISTS task (' \
		'id INTEGER PRIMARY KEY,' \
		'taskname TEXT NOT NULL,' \
		'description TEXT,' \
		'person TEXT COLLATE NOCASE,' \
		'datedue INTEGER NOT NULL,' \
		'datedone INTEGER,' \
		'repeatcount INTEGER NOT NULL,' \
		'repeatunit INTEGER NOT NULL,' \
		'repeatafter INTEGER NOT NULL,' \
		'neverdays INTEGER NOT NULL,' \
		'neverweeks INTEGER NOT NULL,' \
		'nevermonths INTEGER NOT NULL)'
	)
	cr.execute(
		'CREATE TABLE IF NOT EXISTS log (' \
		'datedone INTEGER NOT NULL,' \
		'person TEXT NOT NULL COLLATE NOCASE,' \
		'taskname TEXT NOT NULL)'
	)
	connection.commit()


def create_task(data):
	cr = connection.cursor()
	cr.execute(
		'INSERT INTO task ' \
		'(taskname,description,person,datedue,repeatcount,repeatunit,repeatafter,neverdays,neverweeks,nevermonths) ' \
		'VALUES (:taskname,:description,:person,:datedue,:repeatcount,:repeatunit,:repeatafter,:neverdays,:neverweeks,:nevermonths)',
		data
	)
	connection.commit()


def update_task(id, data):
	cr = connection.cursor()
	cr.execute(
		'UPDATE task SET ' \
		'taskname=:taskname,description=:description,person=:person,datedue=:datedue,repeatcount=:repeatcount,' \
		'repeatunit=:repeatunit,repeatafter=:repeatafter,neverdays=:neverdays,neverweeks=:neverweeks,nevermonths=:nevermonths ' \
		'WHERE id=' + str(int(id)),
		data
	)
	connection.commit()


def update_task_done(id, datedue, datedone):
	cr = connection.cursor()
	cr.execute('UPDATE task SET datedue=?,datedone=? WHERE id=?', (datedue, datedone, id))
	connection.commit()


def delete_task(id):
	cr = connection.cursor()
	cr.execute('DELETE FROM task WHERE id=?', (id,))
	connection.commit()


def create_log(datedone, person, taskname):
	cr = connection.cursor()
	cr.execute('INSERT INTO log (datedone,person,taskname) VALUES (?,?,?)', (datedone, person, taskname))
	connection.commit()


def read_task(id):
	pass
	cr = connection.cursor()
	#TODO: What happens if no records are found?
	cr.execute('SELECT taskname,description,person,datedue,repeatcount,repeatunit,repeatafter,neverdays,neverweeks,nevermonths FROM task WHERE id=?', (id,))
	return cr.fetchone()


def read_task_list(is_due, person, sort):
	sql = ['SELECT id,taskname,description,person,datedue,datedone FROM task']
	data = []
	if is_due:
		sql.append('WHERE datedue < ?')
		data.append(int(time.time()))
	if person:
		sql.append('AND' if is_due else 'WHERE')
		sql.append('person=?')
		data.append(person)
	if sort:
		sql.append('ORDER BY')
		if sort == SORT_DATEDUE:
			sql.append('datedue,datedone DESC')
		elif sort == SORT_DATEDONE:
			sql.append('datedone DESC')
		elif sort == SORT_PERSON:
			sql.append('person,taskname')
		else:
			sql.append('taskname,person')
	cr = connection.cursor()
	cr.execute(' '.join(sql), data)
	return cr.fetchall()


def read_person_list():
	cr = connection.cursor()
	cr.execute('SELECT DISTINCT person FROM task WHERE person > "" ORDER BY person')
	return cr.fetchall()


def read_log_list(person, sort):
	sql = ['SELECT datedone,person,taskname FROM log']
	data = []
	if person:
		sql.append('WHERE person=?')
		data.append(person)
	if sort:
		sql.append('ORDER BY')
		if sort == SORT_TASKNAME:
			sql.append('taskname,datedone DESC')
		elif sort == SORT_PERSON:
			sql.append('person,datedone DESC')
		else:
			sql.append('datedone DESC')
	cr = connection.cursor()
	cr.execute(' '.join(sql), data)
	return cr.fetchall()
