#!/usr/bin/env python3

# This file is part of the project "Omogomigen" which is licensed under
# the zlib License (see LICENSE file). Please include every file from
# the project when distributing. Copyright (C) 2019 Thomas Munk.

VERSION = '0.9.0'

import os.path
import time
from datetime import date, datetime, timedelta
import argparse
import tornado.ioloop
import tornado.web
import database
from tagbuilder import Tag, TagE

WHAT_ALLTASKS = 1
WHAT_DUETASKS = 2
WHAT_LOG = 3
WHO_ALLPERSONS = ''
TASK_NEW = -1
REPEATUNIT_DAYS = 1
REPEATUNIT_WEEKS = 2
REPEATUNIT_MONTHS = 3
REPEATAFTER_DUE = 1
REPEATAFTER_DONE = 2
WEB_DATE_FORMAT = '%Y-%m-%d'
WEB_TIME_FORMAT = '%H:%M'

def date_time_string(timestamp, no_midnight):
	if not timestamp:
		return '(never)'
	if type(timestamp) is datetime:
		dt = timestamp
	else:
		dt = datetime.fromtimestamp(timestamp)
	if no_midnight and dt.hour == 0 and dt.minute == 0:
		return dt.strftime(args.dateformat)
	else:
		return dt.strftime(args.dateformat + args.timeformat)

# ---------- Main page -------------------------------------------------

class MainHandler(tornado.web.RequestHandler):

	def get(self):
		select_identity = None
		identity = tornado.escape.url_unescape(self.get_cookie('identity', ''))
		if not identity:
			persons = database.read_person_list()
			if persons:
				select_identity = Tag('label', (
					'Please select your identity&emsp;',
					Tag('select', (Tag('option', value='', label='(None)'), [TagE('option', row['person']) for row in persons]), onchange='event_select_identity_onchange(this.value)')
				), class_='standout')
		Tag('html', (
			Tag('head', (
				Tag('meta', charset='UTF-8'),
				Tag('title', 'Omogomigen'),
				Tag('meta', name='viewport', content='width=device-width,initial-scale=1'),
				Tag('link', rel='manifest', href='/static/omogomigen.webmanifest'),
				Tag('link', rel='stylesheet', type='text/css', href='/static/omogomigen.css'),
				Tag('script', '', src='/static/omogomigen.js'),
			)),
			Tag('body', (
				Tag('div', (
					select_identity,
					Tag('a', Tag('img', id='logo', src='/static/omogomigen.png', alt=True), href='/'),
					Tag('div', '', id='level1')
				), id='main')
			), onload='event_body_onload()')
		)).render(self.write, '<!DOCTYPE html>\n')

# ---------- HTML API --------------------------------------------------

class ApiHtmlTaskListHandler(tornado.web.RequestHandler):

	def post(self):
		identity = tornado.escape.url_unescape(self.get_cookie('identity', ''))
		body = tornado.escape.json_decode(self.request.body)
		level = body['level']
		who = str(body.get('who', identity))
		what = int(body.get('what', WHAT_DUETASKS if who else WHAT_ALLTASKS))
		sort = int(body.get('sort', database.SORT_DATEDUE if what == WHAT_DUETASKS else database.SORT_PERSON))
		if what == WHAT_LOG and sort == database.SORT_DATEDONE:
			sort = database.SORT_DATEDUE

		# List level 3 is always included - create common tag variable here
		if level <= 3:
			tag = Tag('div', id='level3')
			if what == WHAT_LOG:
				rows = database.read_log_list(who, sort)
				last = None
				if sort == database.SORT_TASKNAME:
					for row in rows:
						#TODO: What if taskname is the same for multiple tasks? (not difference by id here)
						#TODO: What if we log other things than tasknames here?
						curr = row['taskname']
						if curr != last:
							tag.add(TagE('h2', curr))
							table = Tag('table')
							tag.add(table)
							last = curr
						#TODO: Swap columns? (more consistent)
						table.add(Tag('tr', (TagE('td', row['person']) if who == WHO_ALLPERSONS else None, Tag('td', date_time_string(row['datedone'], False)))))
				elif sort == database.SORT_PERSON:
					for row in rows:
						curr = row['person']
						if curr != last:
							tag.add(TagE('h2', curr))
							table = Tag('table')
							tag.add(table)
							last = curr
						table.add(Tag('tr', (Tag('td', date_time_string(row['datedone'], False)), TagE('td', row['taskname']))))
				else:
					for row in rows:
						datedone = row['datedone']
						curr = date.fromtimestamp(datedone)
						if curr != last:
							tag.add(Tag('h2', curr.strftime(args.dateformat)))
							table = Tag('table')
							tag.add(table)
							last = curr
						#TODO: time-format should come from args.timeformat (problem: starts default with comma):
						table.add(Tag('tr', (Tag('td', datetime.fromtimestamp(datedone).strftime('%H:%M')), TagE('td', row['person']) if who == WHO_ALLPERSONS else None, TagE('td', row['taskname']))))
			else:
				for row in database.read_task_list(what == WHAT_DUETASKS, who, sort):
					taskitem = Tag('article')
					can_check = what == WHAT_DUETASKS and who and who == identity
					if what == WHAT_ALLTASKS:
						taskitem.add(Tag('input', type='image', src='/static/edit.svg', alt='Edit', onclick='event_button_taskedit_onclick(%d)' % row['id']))
					elif can_check:
						taskitem.add(Tag('input', type='image', src='/static/check.svg', alt='Check', onclick='event_button_taskcheck_onclick(this, %d)' % row['id']))
					person = row['person']
					taskitem.add(TagE('div', (
						TagE('strong', row['taskname']),
						' (%s)' % person if who == WHO_ALLPERSONS and person else None
					)))
					description = row['description']
					if description:
						taskitem.add(TagE('div', description))
					s = date_time_string(row['datedone'], False)
					taskitem.add(Tag('div', (
						Tag('b', 'Done:'),
						Tag('output', s) if can_check else s
					)))
					s = date_time_string(row['datedue'], True)
					taskitem.add(Tag('div', (
						Tag('b', 'Due:'),
						Tag('output', s) if can_check else s
					)))
					tag.add(taskitem)
			if who != WHO_ALLPERSONS:
				#TODO: Add possibility (button) to sign out from identity -> delete cookie -> page reload -> select identity
				pass
			if not tag.content:
				# Div-tag can't be empty
				tag.add('')

			# List level 2 is maybe included - add on top of common tag variable
			if level <= 2:
				tag = Tag('div', (
					(Tag('button', 'New task', type='button', onclick='event_button_taskedit_onclick(%d)' % TASK_NEW), '&emsp;') if what == WHAT_ALLTASKS else None,
					Tag('select', (
						Tag('option', 'Sort by due (oldest)', value=database.SORT_DATEDUE, selected=sort == database.SORT_DATEDUE) if what != WHAT_LOG else None,
						Tag('option', 'Sort by done (newest)', value=database.SORT_DATEDONE, selected=sort == database.SORT_DATEDONE),
						Tag('option', 'Sort by task name', value=database.SORT_TASKNAME, selected=sort == database.SORT_TASKNAME),
						Tag('option', 'Sort by person', value=database.SORT_PERSON, selected=sort == database.SORT_PERSON)
					), id='selsort', onchange='event_select_sort_onchange()'),
					tag
				), id='level2')

				# List level 1 is maybe included - add on top of common tag variable
				if level <= 1:
					tag = Tag('div', (
						Tag('select', (
							Tag('option', 'All tasks', value=WHAT_ALLTASKS, selected=what == WHAT_ALLTASKS),
							Tag('option', 'Due tasks', value=WHAT_DUETASKS, selected=what == WHAT_DUETASKS),
							Tag('option', 'Log', value=WHAT_LOG, selected=what == WHAT_LOG)
						), id='selwhat', onchange='event_select_what_onchange()'),
						Tag('select',
							#[Tag('option', 'All persons', value=WHO_ALLPERSONS, selected=who == WHO_ALLPERSONS)] +
							#[Tag('option', row['person'], selected=who == row['person']) for row in database.read_person_list()],
							(
							Tag('option', 'All persons', value=WHO_ALLPERSONS, selected=who == WHO_ALLPERSONS),
							[TagE('option', row['person'], selected=who == row['person']) for row in database.read_person_list()]
							),
						id='selwho', onchange='event_select_who_onchange()'),
						tag
					), id='level1')
		self.set_header('Content-Type', 'text/plain')
		tag.render(self.write)


class ApiHtmlTaskEditHandler(tornado.web.RequestHandler):

	def post(self):
		body = tornado.escape.json_decode(self.request.body)
		taskid = body['task_id']
		if taskid == TASK_NEW:
			row = {
				'taskname': '',
				'description': None,
				'person': tornado.escape.url_unescape(self.get_cookie('identity', '')),
				'datedue': time.time(),
				'repeatcount': 1,
				'repeatunit': 1,
				'repeatafter': 1,
				'neverdays': 0,
				'neverweeks': 0,
				'nevermonths': 0
			}
		else:
			row = database.read_task(taskid)
		form = Tag('form', id='taskedit')
		form.add(Tag('input', type='hidden', name='task_id', value=taskid))
		#TODO: Learn and add all relevant attributes on all input types
		form.add(Tag('label', ('Task name<br/>', Tag('input', type='text', name='taskname', size=40, maxlength=40, value=row['taskname']))))
		form.add(Tag('label', ('Description<br/>', Tag('input', type='text', name='description', class_='wide', maxlength=250, value=row['description']))))
		form.add(Tag('label', ('Person<br/>', Tag('input', type='text', name='person', list='personlist', size=30, maxlength=30, value=row['person']))))
		form.add(Tag('datalist',
			(
			Tag('option', 'Not assigned', value=''),
			[TagE('option', row['person']) for row in database.read_person_list()]
			),
			id='personlist'))

		dt = datetime.fromtimestamp(row['datedue'])
		form.add(Tag('label', (
			'Due from<br/>',
			Tag('input', type='date', name='duedate', value=dt.strftime(WEB_DATE_FORMAT)),
			'&emsp;',
			Tag('input', type='time', name='duetime', value=None if taskid == TASK_NEW or (dt.hour == 0 and dt.minute == 0) else dt.strftime(WEB_TIME_FORMAT)))))
		repeatunit = row['repeatunit']
		repeatafter = row['repeatafter']
		form.add(Tag('label', (
			'Repeat<br>',
			Tag('input', type='number', name='repeatcount', min=1, max=999, value=row['repeatcount']),
			'&emsp;',
			Tag('select', (
				Tag('option', 'days', value=REPEATUNIT_DAYS, selected=repeatunit == REPEATUNIT_DAYS),
				Tag('option', 'weeks', value=REPEATUNIT_WEEKS, selected=repeatunit == REPEATUNIT_WEEKS),
				Tag('option', 'months', value=REPEATUNIT_MONTHS, selected=repeatunit == REPEATUNIT_MONTHS)),
				name='repeatunit'),
			'&emsp;',
			Tag('select', (
				Tag('option', 'after due', value=REPEATAFTER_DUE, selected=repeatafter == REPEATAFTER_DUE),
				Tag('option', 'after done', value=REPEATAFTER_DONE, selected=repeatafter == REPEATAFTER_DONE)),
				name='repeatafter'))))
		neverdays = row['neverdays']
		form.add(Tag('label', (
			'Never due (days)<br>',
			Tag('input', type='checkbox', name='neverday0', checked=neverdays & 1 > 0),
			' M&emsp;',
			Tag('input', type='checkbox', name='neverday1', checked=neverdays & 2 > 0),
			' T&emsp;',
			Tag('input', type='checkbox', name='neverday2', checked=neverdays & 4 > 0),
			' W&emsp;',
			Tag('input', type='checkbox', name='neverday3', checked=neverdays & 8 > 0),
			' T&emsp;',
			Tag('input', type='checkbox', name='neverday4', checked=neverdays & 16 > 0),
			' F&emsp;',
			Tag('input', type='checkbox', name='neverday5', checked=neverdays & 32 > 0),
			' S&emsp;',
			Tag('input', type='checkbox', name='neverday6', checked=neverdays & 64 > 0),
			' S')))
		never = row['neverweeks']
		form.add(Tag('label', (
			'Never due (week numbers)<br>',
			Tag('input', type='text', name='neverweeks', class_='wide', list='neverweekslist',
				value=', '.join([str(n + 1) for n in range(53) if never & (1 << n)])))))
		form.add(Tag('datalist', (
			Tag('option', 'None', value=''),
			Tag('option', 'Odd week numbers', value=', '.join(str(n) for n in range(1, 54, 2))),
			Tag('option', 'Even week numbers', value=', '.join(str(n) for n in range(2, 53, 2)))),
			id='neverweekslist'))
		never = row['nevermonths']
		form.add(Tag('label', (
			'Never due (month numbers)<br>',
			Tag('input', type='text', name='nevermonths', class_='wide', list='nevermonthslist',
				value=', '.join([str(n + 1) for n in range(12) if never & (1 << n)])))))
		form.add(Tag('datalist', (
			Tag('option', 'None', value=''),
			Tag('option', 'Winter', value='12, 1, 2'),
			Tag('option', 'Spring', value='3, 4, 5'),
			Tag('option', 'Summer', value='6, 7, 8'),
			Tag('option', 'Autumn', value='9, 10, 11')),
			id='nevermonthslist'))

		buttons = Tag('div')
		buttons.add(Tag('button', 'Save', type='button', onclick='event_button_tasksave_onclick()'))
		if taskid != TASK_NEW:
			buttons.add('&emsp;')
			buttons.add(Tag('button', 'Delete', type='button', onclick='event_button_taskdelete_onclick()'))
		buttons.add('&emsp;')
		buttons.add(Tag('button', 'Cancel', type='button', onclick='event_button_taskcancel_onclick()'))

		self.set_header('Content-Type', 'text/plain')
		Tag('div', (form, buttons), id='level1').render(self.write)

		#def mypr(s):
		#	print(s, end='')
		#form.render(mypr)

# ---------- CMD API ---------------------------------------------------

class ApiCmdTaskSaveHandler(tornado.web.RequestHandler):

	def post(self):
		body = tornado.escape.json_decode(self.request.body)
		#print(body)
		msg = []
		taskid = int(body['task_id'])
		s = body['taskname'].strip()
		if not len(s) in range(1, 41):
			msg.append('Empty or too long task name.')
		data = {'taskname': s}
		s = body['description'].strip()
		if len(s) > 250:
			msg.append('Too long description.')
		data['description'] = s if s else None
		s = body['person'].strip().title()
		if len(s) > 30:
			msg.append('Too long person name - use first names only.')
		data['person'] = s if s else None
		s = body['duetime']
		#TODO: Browsers can clear duedate to empty string - be able to handle that
		if s:
			n = int(datetime.strptime(body['duedate'] + 'T' + s, WEB_DATE_FORMAT + 'T' + WEB_TIME_FORMAT).timestamp())
		else:
			n = int(datetime.strptime(body['duedate'], WEB_DATE_FORMAT).timestamp())
		data['datedue'] = n

		s = body['repeatcount'].strip()
		n = int(s) if s else 0
		if n < 1 or n > 999:
			msg.append('Invalid repeat number.')
		data['repeatcount'] = n

		s = body['repeatunit'].strip()
		n = int(s) if s else 0
		if n < REPEATUNIT_DAYS or n > REPEATUNIT_MONTHS:
			msg.append('Invalid repeat unit.')
		data['repeatunit'] = n

		s = body['repeatafter'].strip()
		n = int(s) if s else 0
		if n < REPEATAFTER_DUE or n > REPEATAFTER_DONE:
			msg.append('Invalid repeat after.')
		data['repeatafter'] = n

		n = 1 if body['neverday0'] == True else 0
		if body['neverday1'] == True:
			n |= 0b10
		if body['neverday2'] == True:
			n |= 0b100
		if body['neverday3'] == True:
			n |= 0b1000
		if body['neverday4'] == True:
			n |= 0b10000
		if body['neverday5'] == True:
			n |= 0b100000
		if body['neverday6'] == True:
			n |= 0b1000000
		if n == 0b1111111:
			msg.append('Never due on every day.')
		data['neverdays'] = n

		n = 0
		for s in body['neverweeks'].split(','):
			if s.strip():
				i = int(s) - 1
				if i in range(53):
					n |= 1 << i
		data['neverweeks'] = n

		n = 0
		for s in body['nevermonths'].split(','):
			if s.strip():
				i = int(s) - 1
				if i in range(12):
					n |= 1 << i
		data['nevermonths'] = n

		#print(data)

		if msg:
			self.write({'ok': False, 'msg': '\n'.join(msg)})
		else:
			try:
				database.create_task(data) if taskid == TASK_NEW else database.update_task(taskid, data)
				self.write({'ok': True})
			except Exception as e:
				self.write({'ok': False, 'msg': str(e)})


class ApiCmdTaskDeleteHandler(tornado.web.RequestHandler):

	def post(self):
		body = tornado.escape.json_decode(self.request.body)
		taskid = body['task_id']
		try:
			database.delete_task(taskid)
			self.write({'ok': True})
		except Exception as e:
			self.write({'ok': False, 'msg': str(e)})


class ApiCmdTaskCheckHandler(tornado.web.RequestHandler):

	def post(self):

		def never_on_date(dt):
			return (1 << dt.weekday()) & neverdays or (1 << (dt.isocalendar()[1] - 1)) & neverweeks or (1 << (dt.month - 1)) & nevermonths

		def add_months(dt, n):
			y, m = divmod(dt.month + n, 12)
			r = date(dt.year + y, m + 1, 1) - timedelta(days=1)
			return datetime(r.year, r.month, min(r.day, dt.day), dt.hour, dt.minute)

		def write_error(s):
			self.write({'ok': False, 'msg': s})

		body = tornado.escape.json_decode(self.request.body)
		taskid = body['task_id']
		row = database.read_task(taskid)
		repeatcount = row['repeatcount']
		repeatunit = row['repeatunit']
		repeatafter = row['repeatafter']
		neverdays = row['neverdays']
		neverweeks = row['neverweeks']
		nevermonths = row['nevermonths']
		datedone = int(time.time())
		dt = datetime.fromtimestamp(datedone)
		dt_due = datetime.fromtimestamp(row['datedue'])
		if dt_due > dt:
			# Not due yet - check can be pressed in another browser
			write_error('Not due yet')
			return
		#TODO: Can the 2 whiles possibly run forever? Do we need a too-many-loops-break?
		if repeatafter == REPEATAFTER_DUE:
			while dt_due <= dt or never_on_date(dt_due):
				if repeatunit == REPEATUNIT_DAYS:
					dt_due += timedelta(days=repeatcount)
				elif repeatunit == REPEATUNIT_WEEKS:
					dt_due += timedelta(weeks=repeatcount)
				elif repeatunit == REPEATUNIT_MONTHS:
					dt_due = add_months(dt_due, repeatcount)
				else:
					break
		elif repeatafter == REPEATAFTER_DONE:
			if repeatunit == REPEATUNIT_DAYS:
				dt += timedelta(days=repeatcount)
			elif repeatunit == REPEATUNIT_WEEKS:
				dt += timedelta(weeks=repeatcount)
			elif repeatunit == REPEATUNIT_MONTHS:
				dt = add_months(dt, repeatcount)
			while never_on_date(dt):
				dt += timedelta(days=1)
			dt_due = datetime(dt.year, dt.month, dt.day, dt_due.hour, dt_due.minute)
		try:
			database.create_log(datedone, row['person'], row['taskname'])
			database.update_task_done(taskid, int(dt_due.timestamp()), datedone)
			self.write({'ok': True, 'datedone': date_time_string(datedone, False), 'datedue': date_time_string(dt_due, True)})
		except Exception as e:
			write_error(str(e))

# ---------- Main ------------------------------------------------------

def create_application():
	global args

	parser = argparse.ArgumentParser()
	parser.add_argument('--port', help='Server port to listen on', type=int, default=8888)
	parser.add_argument('--dateformat', help='Date format (strftime)', type=str, default='Week %V, %x')
	parser.add_argument('--timeformat', help='Time format (strftime) added to dateformat', type=str, default=', %H:%M')
	parser.add_argument('--locale', help='Locale for date/time format', type=str)
	parser.add_argument('database', help='Path of SQLite 3 database file to be used. Will be created if nessecary.', type=str)
	args = parser.parse_args()

	if args.locale:
		import locale
		locale.setlocale(locale.LC_TIME, args.locale)

	return tornado.web.Application([
		(r'/', MainHandler),
		(r'/api/html/tasklist', ApiHtmlTaskListHandler),
		(r'/api/html/taskedit', ApiHtmlTaskEditHandler),
		(r'/api/cmd/tasksave', ApiCmdTaskSaveHandler),
		(r'/api/cmd/taskdelete', ApiCmdTaskDeleteHandler),
		(r'/api/cmd/taskcheck', ApiCmdTaskCheckHandler)
	], static_path=os.path.join(os.path.dirname(__file__), 'static'))


if __name__ == '__main__':
	app = create_application()
	database.connect(args.database)
	app.listen(args.port)
	tornado.ioloop.IOLoop.current().start()
