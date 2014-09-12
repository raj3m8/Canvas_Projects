from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.template.loader import get_template
from django.template import Context, loader
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from pymongo import Connection
import time
import pymongo
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
from datetime import datetime, date, timedelta
from time import mktime
from django.core.mail import send_mail
import urllib
import os
from settings import db
import json
import re
import bcrypt
import base64
from django import template

def signup(request):
	return render_to_response('signup.html')

def contact_us(request):
	user = get_user(request)
	return render_to_response('contact_us.html', {"user": user})

def rules(request):
	user = get_user(request)
	return render_to_response('rules.html', {"user": user})

def create_listing(request):
	user = get_user(request)
	return render_to_response('create_listing.html', {"user": user})

def account(request):
	user = get_user(request)
	return render_to_response('account.html', {"user": user})

def item(request, item_id):
	user = get_user(request)
	item = db.item.find_one({'_id': ObjectId(item_id)})
	item['id'] = str(item['_id'])

	main_image = item['image'][0]
	secondary_images = item['image']

	return render_to_response('item.html', {"user": user, "item": item, "main_image": main_image, "secondary_images": secondary_images})

@csrf_exempt
def watch_item(request):
	user = get_user(request)
	item_id = request.POST['item_id']
	db.user.update({'user': user}, {'$addToSet': {'watch_list': item_id}})
	return HttpResponse(True)

def create_listing_submit(request):
	return HttpResponse(True)

def user_page(request, user_profile):
	cur_user = get_user(request)
	total_ratings = 0

	ratings_cursor = db.review.find({"reviewee": user_profile})
	ratings = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}

	for r in ratings_cursor:
		ratings[str(int(r['rating']))] += 1
		total_ratings += 1

	has_interacted = True if cur_user in db.user.find_one({'user': user_profile})['user_interaction_list'] else False

	rating_cursor = db.review.find_one({"reviewer": cur_user, "reviewee": user_profile})
	if rating_cursor is not None:
		current_rating = rating_cursor['rating']
	else:
		current_rating = 0

	print current_rating

	return render_to_response('user_page.html', {"user": cur_user, "user_profile": user_profile, "ratings": ratings, "total_ratings": total_ratings, 'has_interacted': has_interacted, "current_rating": current_rating})

@csrf_exempt
def rate_user(request):
	user = get_user(request)
	rated_user = request.POST['user']
	rating = int(request.POST['rating'])

	print user, rated_user, rating

	db.review.update({'reviewer': user, 'reviewee': rated_user}, {'$set': {'rating': rating}}, True)
	return HttpResponse(True)

def home(request, search_val=None):
	item_list = []
	item_cursor = db.item.find()

	for i in item_cursor:
		i['id'] = str(i['_id'])
		if search_val is not None:
			if search_val in i['title'].lower():
				item_list.append(i)
		else:
			item_list.append(i)

	user = get_user(request)
	return render_to_response('index.html', {'items': item_list, "user": user})

@csrf_exempt
def signup_sub(request):
	p = request.POST

	email = request.POST["email"]
	user = request.POST["user"]
	pswd = request.POST["password"]
	pswd_auth = request.POST["password2"]

	# Make sure all user fields are valid
	if db.user.find_one({"email": email}) is not None:
		return HttpResponse(json.dumps({"title": "Error", "text": "An account already exists with that email address"}), mimetype="application/json")

	if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
		return HttpResponse(json.dumps({"title": "Error", "text": "The email address entered is not valid"}), mimetype="application/json")

	if db.user.find_one({"user": user}) is not None:
		return HttpResponse(json.dumps({"title": "Error", "text": "An account already exists with that username"}), mimetype="application/json")

	if pswd != pswd_auth:
		return HttpResponse(json.dumps({"title": "Error", "text": "Passwords do not match"}), mimetype="application/json")

	if len(pswd) < 8:
		return HttpResponse(json.dumps({"title": "Error", "text": "Passwords must be 8 characters"}), mimetype="application/json")

	# Create encrypted password
	salt = bcrypt.gensalt()
	hashed_password = bcrypt.hashpw(base64.b64encode(pswd), salt)

	db.user.insert({"user": user, "email": email, "password": hashed_password, "salt": salt})

	user.save()

	return HttpResponse(json.dumps({"title": "Success", "text": "Your account has been created, go to the <a href='/login/'><b>login</b></a> page now"}), mimetype="application/json")

def login_home(request):
	return render_to_response('login.html')

@csrf_exempt
def login_submit(request):
	user = request.POST["user"]
	password = request.POST["password"]

	user_cursor = db.user.find_one({"user": user})

	if user_cursor is not None and str(user_cursor['password']) == bcrypt.hashpw(base64.b64encode(password), str(user_cursor['password'])):
		request.session["user"] = user
		return HttpResponse(True)
	else:
		return HttpResponse(False)

def logout(request):
	try:
		del(request.session["user"])
	except:
		pass

	return HttpResponseRedirect(reverse("login"))

def get_user(request):
	return request.session["user"] if "user" in request.session else None

@csrf_exempt
def current_listings(request):
	item_list_cursor = db.item.find({'seller': get_user(request), 'expiration': {'$gte': datetime.now()}})
	item_list = list()

	for i in item_list_cursor:
		i['id'] = str(i['_id'])
		item_list.append(i)

	return render_to_response('current_listings.html', {'items': item_list})

@csrf_exempt
def sold_listings(request):
	item_list_cursor = db.item.find({'seller': get_user(request), 'sold': True})
	item_list = list()

	for i in item_list_cursor:
		i['id'] = str(i['_id'])
		item_list.append(i)

	return render_to_response('sold_listings.html', {'items': item_list})

@csrf_exempt
def expired_listings(request):
	item_list_cursor = db.item.find({'seller': get_user(request), 'expiration': {'$lte': datetime.now()}})
	item_list = list()

	for i in item_list_cursor:
		i['id'] = str(i['_id'])
		item_list.append(i)

	return render_to_response('expired_listings.html', {'items': item_list})

@csrf_exempt
def accept_offer(request):
	item_id = request.POST['item_id']
	offer = db.item.find_one({'_id': ObjectId(item_id)})['offer']

	db.item.update({'_id': ObjectId(item_id)}, {'$set': {'sold': True, 'sold_price': offer}})
	return HttpResponse(True)

@csrf_exempt
def del_listing(request):
	item_id = request.POST['item_id']

	db.item.update({'_id': ObjectId(item_id)}, {'$set': {'expiration': datetime.now()}})
	return HttpResponse(True)

@csrf_exempt
def relist(request):
	item_id = request.POST['item_id']
	price = float(request.POST['new_price'])

	new_expiration = datetime.now() + timedelta(days=30)

	db.item.update({'_id': ObjectId(item_id)}, {"$set": {'expiration': new_expiration, 'price': price, 'offer': 0}})
	return HttpResponse(True)



















