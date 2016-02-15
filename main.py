import sys
import os

sys.path.insert(1, os.path.join(os.path.abspath('.'),  'venv/lib/python2.7/site-packages'))

import urllib, urllib2
import json
import random

from flask import Flask, render_template, request, url_for, session, redirect
from flask_jsglue import JSGlue
from flask_oauth import OAuth

from google.appengine.api import urlfetch

app = Flask(__name__, static_url_path = "", static_folder = "static")
jsglue = JSGlue(app)
DEBUG = True
app.debug = DEBUG


FACEBOOK_APP_ID = '1118988874810352'
FACEBOOK_APP_SECRET = 'fbbc361a470fabae84ca176752e80515'

SECRET_KEY = 'dev123*Alopasdw1'
app.secret_key = SECRET_KEY
oauth = OAuth()

CLARIFAI_ID = '9GCHk6DcJOqdGx_KT3WbLb2JVUHYUhUkfF7HfC2J'
CLARIAI_SECRET = 'g6MxcRw_Ou0cb2c_PkQleV1UirufHZgL2o69o7Fy'

facebook = oauth.remote_app('facebook',
	base_url='https://graph.facebook.com/',
	request_token_url=None,
	access_token_url='/oauth/access_token',
	authorize_url='https://graph.facebook.com/oauth/authorize',
	consumer_key=FACEBOOK_APP_ID,
	consumer_secret=FACEBOOK_APP_SECRET,
	request_token_params={'scope': 'email, user_photos' }
)

def getClarifaiToken():
	form_fields = {'grant_type':'client_credentials','client_id':CLARIFAI_ID, 'client_secret':CLARIAI_SECRET}
	form_data = urllib.urlencode(form_fields)
	result = urlfetch.fetch(url="https://api.clarifai.com/v1/token/",
	payload=form_data,
	method=urlfetch.POST,
	headers={'Content-Type': 'application/x-www-form-urlencoded'})
	if result.status_code != 200:
		print "Clarifai connection error"
	data = json.loads(result.content)
	return data['access_token']
	"""
	method = "POST"
	handler = urllib2.HTTPHandler()
	opener = urllib2.build_opener(handler)
	values = {'grant_type':'client_credentials','client_id':CLARIFAI_ID, 'client_secret':CLARIAI_SECRET}
	data = urllib.urlencode(values)
	request = urllib2.Request("https://api.clarifai.com/v1/token/", data)
	request.get_method = lambda: method
	try:
		connection = opener.open(request)
	except urllib2.HTTPError,e:
		connection = e
	if connection.code == 200:
		data = connection.read()
	else:
		print "Clarifai connection error"

	data = json.loads(data)
	print "CLARIFAI ACCESS TOKEN", data['access_token']
	return data['access_token']
	"""


def getTags(url, clarifai_token):
	form_fields = {'url':url}
	form_data = urllib.urlencode(form_fields)
	result = urlfetch.fetch(url="https://api.clarifai.com/v1/tag",
	payload=form_data,
	method=urlfetch.POST,
	headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization':'Bearer ' + clarifai_token})
	if result.status_code != 200:
		print "Clarifai connection error"
	data = json.loads(result.content)
	classList = data["results"][0]["result"]["tag"]["classes"]
	return classList

	"""
	method = "POST"
	handler = urllib2.HTTPHandler()
	opener = urllib2.build_opener(handler)
	param = {'url':url}
	data = urllib.urlencode(param)
	request = urllib2.Request('https://api.clarifai.com/v1/tag', data)
	request.add_header('Authorization', 'Bearer ' + clarifai_token)
	request.get_method = lambda: method
	try:
		connection = opener.open(request)
	except urllib2.HTTPError,e:
		connection = e

	if connection.code == 200:
		data = connection.read()
	else:
		print "Clarifai connection error"

	data = json.loads(data)

	classList = data["results"][0]["result"]["tag"]["classes"]
	return classList
	"""

def getImages(USER_ID, ACCESS_TOKEN, COUNT):
	result = urlfetch.fetch("https://graph.facebook.com/v2.5/"+USER_ID+"/photos?access_token=" + ACCESS_TOKEN)
	if result.status_code != 200:
		print "FB Connection error"
	#result = urllib2.urlopen("https://graph.facebook.com/v2.5/"+USER_ID+"/photos?access_token=" + ACCESS_TOKEN)
	json_result = json.loads(result.content)
	images = list()
	cnt = 0
	images += json_result['data']
	cnt += len(json_result['data'])
	print "COUNT", cnt, COUNT
	while json_result['paging'].has_key('next'):
		if cnt>COUNT:
			break
		result = urlfetch.fetch(json_result['paging']['next'])
		if result.status_code != 200:
			print "FB Connection error"
		#result = urllib2.urlopen(json_result['paging']['next'])
		json_result = json.loads(result.content)
		images += json_result['data']
		cnt += len(json_result['data'])

	img_details = list()
	tag_img = dict()
	for i in images:
		img = dict()
		img['id'] = i['id']
		img_url = 'https://graph.facebook.com/v2.5/'+ i['id'] + "?access_token="+ ACCESS_TOKEN + '&fields=images'
		result = urlfetch.fetch(img_url)
		if result.status_code != 200:
			print "FB Connection error"
		#result = urllib2.urlopen(img_url)
		json_result = json.loads(result.content)
		img['url'] = json_result['images'][0]['source']
		img_details.append(img)
		clarifai_token = getClarifaiToken()
		tags = getTags(img['url'], clarifai_token)
		for t in tags:
			if tag_img.has_key(t):
				tag_img[t].append(img)
			else:
				tag_img[t]=[img]


	my_randoms = random.sample(xrange(COUNT), COUNT/10)
	rand_images = list()
	for i in my_randoms:
		rand_images.append(img_details[i])
	return {"images":img_details, "rand_images":rand_images, "tag_imgs":tag_img}

@app.route('/login')
def login():

	session['permanent'] = True
	return facebook.authorize(callback=url_for('facebook_authorized',
		next=request.args.get('next') or request.referrer or None,
		_external=True))

@app.route("/facebook_authorized")
@facebook.authorized_handler
def facebook_authorized(resp):
	if resp is None or 'access_token' not in resp:
		return redirect(url_for('/'))
	session['logged_in'] = True
	session['facebook_token'] = resp['access_token']
	result = urlfetch.fetch("https://graph.facebook.com/me?access_token="+resp['access_token'])
	if result.status_code != 200:
		print "FB Connection error"
	str = result.content
	params = json.loads(str)
	for k in params:
		session[k] = params[k]
	cnt = 60
	imgs = getImages(session['id'], session['facebook_token'], cnt)
	for k in imgs.keys():
		session[k] = imgs[k]
	print "AFTER AUTH", session.keys()
	session.pop("logged_in", None)
	session.pop("permanent", None)
	session.pop("_permanent", None)
	return render_template('userhome.html', session=session)


@facebook.tokengetter
def get_facebook_oauth_token():
	return session.get('oauth_token')

@app.route("/tagsearch", methods=['POST'])
def tagsearch():
	tag = request.form['tag']
	sess = request.form['session']
	l = sess.find('{')
	r = sess.rfind('}')
	sess = sess[l:r+1]
	sess = sess.replace("{u\'","{\"")
	sess = sess.replace(" u\'"," \"")
	sess = sess.replace("'",'"')
	session = json.loads(sess)
	"""
	return render_template('tagsearch.html', session=session)
	"""
	if tag not in session["tag_imgs"].keys():
		return render_template('userhome.html', session=session)
	return render_template('tagsearch.html', session=session, images=session["tag_imgs"][tag])


@app.route("/")
def hello():
	return render_template('home.html')

if __name__ == "__main__":
	app.run()