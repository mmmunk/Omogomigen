let sel_what, sel_who, sel_sort;

function call_api(url, args, rsp_json, result_func) {
	fetch(url, {
		method: 'POST',
		headers: {'Content-Type': 'application/json'},
		body: JSON.stringify(args)
	})
	.then(rsp => {
		if (rsp.ok) {
			return rsp_json ? rsp.json() : rsp.text();
		} else {
			return Promise.reject('API HTTP Error ' + rsp.status + ': ' + rsp.statusText);
		}
	})
	.then(data => {
		result_func(data);
	})
	.catch(err => {
		alert(err);
	});
}

function replace_html(d, args, element_id) {
	call_api('/api/html/' + d, args, false, function(text) {
		if (text) document.getElementById(element_id).outerHTML = text;
	});
}

function execute_command(d, args, result_func) {
	call_api('/api/cmd/' + d, args, true, function(data) {
		if (data['ok']) result_func(data); else alert(data['msg']);
	});
}

function get_select_values() {
	sel_what = parseInt(document.getElementById('selwhat').value);
	sel_who = document.getElementById('selwho').value;
	sel_sort = parseInt(document.getElementById('selsort').value);
}

function event_body_onload() {
	replace_html('tasklist', {level: 1}, 'level1');
}

function event_select_what_onchange() {
	get_select_values();
	replace_html('tasklist', {level: 2, what: sel_what, who: sel_who, sort: sel_sort}, 'level2');
}

function event_select_who_onchange() {
	get_select_values();
	replace_html('tasklist', {level: 2, what: sel_what, who: sel_who, sort: sel_sort}, 'level2');
}

function event_select_sort_onchange() {
	get_select_values();
	replace_html('tasklist', {level: 3, what: sel_what, who: sel_who, sort: sel_sort}, 'level3');
}

function event_button_taskedit_onclick(id) {
	get_select_values();
	replace_html('taskedit', {task_id: id}, 'level1')
}

function event_button_taskcheck_onclick(button, id) {
	const article = button.parentElement;
	const outputs = article.getElementsByTagName('output');
	execute_command('taskcheck', {task_id: id}, function(data) {
		button.onlick = null;
		button.style.visibility = 'hidden';
		article.style.background = 'none';
		outputs[0].innerText = data['datedone'];
		outputs[1].innerText = data['datedue'];
	});
}

function event_button_tasksave_onclick() {
	const form = document.getElementById('taskedit');
	const inputs = form.querySelectorAll('input,select');
	let data = {};
	inputs.forEach(function(element) {
		data[element.name] = element.type == 'checkbox' ? element.checked : element.value;
	});
	execute_command('tasksave', data, function() {
		replace_html('tasklist', {level: 1, what: sel_what, who: sel_who, sort: sel_sort}, 'level1');
	});
}

function event_button_taskdelete_onclick() {
	if (confirm('Permanently delete the task?')) {
		const id = parseInt(document.getElementsByName('task_id')[0].value);
		execute_command('taskdelete', {task_id: id}, function() {
			replace_html('tasklist', {level: 1, what: sel_what, who: sel_who, sort: sel_sort}, 'level1');
		});
	}
}

function event_button_taskcancel_onclick() {
	replace_html('tasklist', {level: 1, what: sel_what, who: sel_who, sort: sel_sort}, 'level1');
}

function event_select_identity_onchange(value) {
	if (value) {
		document.cookie = 'identity=' + encodeURIComponent(value) + '; max-age=2592000';
		location.reload(true);
	}
}
