# -*- coding: utf-8 -*-

import StringIO
import HTMLParser
import BeautifulSoup
import xlwt

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib import auth
from models import *


def get_is_feeding(user):
    return Feeding.objects.filter(user=user).filter(end__isnull=True).exists()


def index(request):
    return render_to_response('index.html', locals())


# @login_required
def feedings(request, username):
    error = request.GET.get('error')
    user = get_object_or_404(User, username=username)
    is_feeding = get_is_feeding(user)
    feedings = Feeding.objects.filter(user=user).order_by('-begin')
    return render_to_response('feedings.html', locals())


def left(request, username):
    user = get_object_or_404(User, username=username)
    error = ''
    if get_is_feeding(user):
        error = u'请先结束，再开始新的哺乳!'
    else:
        Feeding.objects.create(user=user, position=1, begin=timezone.now())
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


def right(request, username):
    user = get_object_or_404(User, username=username)
    error = ''
    if get_is_feeding(user):
        error = u'请先结束，再开始新的哺乳!'
    else:
        Feeding.objects.create(user=user, position=2, begin=timezone.now())
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


def end(request, username):
    user = get_object_or_404(User, username=username)
    error = ''
    if not get_is_feeding(user):
        error = u'当前没有正在进行的哺乳!'
    else:
        for feeding in Feeding.objects.filter(user=user).filter(end__isnull=True):
            feeding.end = timezone.now()
            feeding.save()
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


def manual(request, username):
    user = get_object_or_404(User, username=username)
    ml = int(request.GET.get('ml', 0))
    error = ''
    if not ml:
        error = u'请输入正确的毫升数!'
    elif get_is_feeding(user):
        error = u'请先结束，再开始手喂!'
    else:
        Feeding.objects.create(user=user, position=3, begin=timezone.now(), end=timezone.now(), ml=ml)
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


def login(request):
    msg = ''
    next_url = request.GET.get('next', '/')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '/')
        user = auth.authenticate(username=username, password=password)
        print(username, password)
        if user is not None and user.is_active:
            auth.login(request, user)
            return HttpResponseRedirect(next_url)
        else:
            msg = u'username or password error'
    return render_to_response('login.html', locals())


def logout(request):
    if request.user.is_authenticated():
        auth.logout(request)
    return HttpResponseRedirect("/")


@login_required
def password(request):
    msg = ''
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        user = request.user

        if not user.check_password(password):
            msg = u'old password error'

        if password1 != password2:
            msg = u'two passwords not the same'

        if not msg:
            user.set_password(password1)
            user.save()
            return HttpResponseRedirect('/login/')

    return render_to_response('password.html', locals())


def output(request):
    data = request.POST.get('data')
    begin_index = int(request.POST.get('begin_index', 0))
    end_index = int(request.POST.get('end_index', 999))

    html_parser = HTMLParser.HTMLParser()

    wb = xlwt.Workbook()
    ws = wb.add_sheet('output')

    soup = BeautifulSoup.BeautifulSoup(data)

    thead_soup = soup.find('thead')
    th_soups = thead_soup.findAll(['th', 'td'])
    th_soups = th_soups[begin_index:end_index]

    j = 0
    for th_soup in th_soups:
        th = th_soup.getText()
        th = html_parser.unescape(th).strip()
        ws.write(0, j, th)
        j += 1

    tbody_soup = soup.find('tbody')
    tr_soups = tbody_soup.findAll('tr')

    i = 1
    for tr_soup in tr_soups:
        td_soups = tr_soup.findAll(['td', 'th'])
        td_soups = td_soups[begin_index:end_index]

        j = 0
        for td_soup in td_soups:
            td = td_soup.getText()
            td = html_parser.unescape(td).strip()
            ws.write(i, j, td)
            j += 1

        i += 1

    s = StringIO.StringIO()
    wb.save(s)
    s.seek(0)
    data = s.read()
    response = HttpResponse(data)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="output.xls"'

    return response
