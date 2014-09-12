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
import json
import re
import bcrypt
import base64
from django import template

register = template.Library()

@register.filter
def dollar_filter(val):
    return "{:,.2f}".format(val)
	