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
import os

from lazypage.decorators import lazypage_decorator

from models import *


def get_is_feeding(user):
    return Feeding.objects.filter(user=user).filter(end__isnull=True).exists()


def get_statistics(feeding_qry):
    count = feeding_qry.count()
    ts = 0
    mls = 0
    for f in feeding_qry:
        ts += (f.end - f.begin).total_seconds()
        mls += f.ml
    rate = 100.0 * ts / (24 * 3600)
    rate = '%.2f' % rate

    m, s = divmod(ts, 60)
    h, m = divmod(m, 60)

    t = '%d:%d:%d' % (h, m, s)

    return count, mls, rate, t


def index(request):
    users = User.objects.filter(is_active=True).exclude(username='admin')
    return render_to_response('index.html', locals())


def feedings(request, username):
    info = request.GET.get('info')
    error = request.GET.get('error')
    is_all = request.GET.get('is_all')
    user = get_object_or_404(User, username=username)
    is_feeding = get_is_feeding(user)
    is_login = request.user.is_authenticated and (request.user == user or request.user.is_superuser)

    feedings = Feeding.objects.filter(user=user).order_by('-begin')
    if is_all:
        t = timezone.now()-timezone.timedelta(hours=24)
        feedings_24h = feedings.filter(begin__gte=t, end__isnull=False)
        count_24h, mls_24h, rate_24h, t_24h = get_statistics(feedings_24h)

        today = datetime.datetime.now().date()

        statistics = []
        for i in range(10):
            d = today - timezone.timedelta(days=i)
            feeding_qry = feedings.filter(end__gte=d, end__lte=d+timezone.timedelta(days=1))
            count, mls, rate, t = get_statistics(feeding_qry)
            s = {
                'date': d,
                'count': count,
                'mls': mls,
                'rate': rate,
                't': t,
            }
            statistics.append(s)
    else:
        feedings = feedings[:30]

    return render_to_response('feedings.html', locals())


@login_required
def left(request, username):
    user = get_object_or_404(User, username=username)
    assert request.user == user or request.user.is_superuser
    error = ''
    if get_is_feeding(user):
        error = u'请先结束，再开始新的哺乳!'
    else:
        Feeding.objects.create(user=user, position=1, begin=timezone.now())
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


@login_required
def right(request, username):
    user = get_object_or_404(User, username=username)
    assert request.user == user or request.user.is_superuser
    error = ''
    if get_is_feeding(user):
        error = u'请先结束，再开始新的哺乳!'
    else:
        Feeding.objects.create(user=user, position=2, begin=timezone.now())
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


@login_required
def end(request, username):
    user = get_object_or_404(User, username=username)
    assert request.user == user or request.user.is_superuser
    error = ''
    if not get_is_feeding(user):
        error = u'当前没有正在进行的哺乳!'
    else:
        for feeding in Feeding.objects.filter(user=user).filter(end__isnull=True):
            feeding.end = timezone.now()
            feeding.save()
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


@login_required
def manual(request, username):
    user = get_object_or_404(User, username=username)
    assert request.user == user or request.user.is_superuser
    ml = int(request.GET.get('ml', 0))
    error = ''
    if not ml:
        error = u'请输入正确的毫升数!'
    elif get_is_feeding(user):
        error = u'请先结束，再开始手喂!'
    else:
        Feeding.objects.create(user=user, position=3, begin=timezone.now(), end=timezone.now(), ml=ml)
    return HttpResponseRedirect('/%s/feedings/?error=%s' % (username, error))


def feedings_login(request, username):
    error = info = ''
    password = request.GET.get('password', '')
    user = auth.authenticate(username=username, password=password)

    if user is not None and user.is_active:
        auth.login(request, user)
        info = u'验证成功 请重新之前操作'
    else:
        error = u'密码不正确'
    url = '/%s/feedings/?error=%s&info=%s' % (username, error, info)
    return HttpResponseRedirect(url)


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


RSA_KEY_EXAMPLE = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxgXY9AGI22MfQPe/VecLzNfga8czch6kNLtIPFO1+ZPPpY6i
43D2dUKZ8zjpZ/QcOV4CALej19LfnhRWkU9iOomYpGAReevnhVRBcwu0+UHmIVn1
k+ovjG8XdMY9jKKeWw2Yu8xsb/DIrxJvVO0gce1oN15dDi89cyE1sCeovAM8fXvx
IxSDsdM4YZRlpxBxJEiCbMJ+gUEdUgQBJmOkuKsBGUfFVtjvjse+g49qcqa4vWq4
/Ft6mHSYJMsBQAIaJmjNlGuav1ocE+4ryp7LL9OSootjntSIDzxo2VfVQFsOL3h8
lSAyTr8j6pEDxy1xfIsNHvjuNHarF2h/r5z/UQIDAQABAoIBAH6iyK6quJHMXvVW
Opc97W7vc0aZmo3ViJ9sUXK6+foEi9tNT1/yIrq0f+1qLOHc25vYQaGhzva7lWPr
j7zXrnLPAb3E7ggxU9sRGdXv26k3emtDs2gHcKb3eGGmUUA50tlZ5Z3bylEAA+bp
/Casin4xG9+kyg/DKCITT9k6U47/xsXvZ1KdPmAYHnUHIw0H3ntxVWNNscjOHz0K
PKam6x9hC8DVmRDfRO25YGb3Aq1SQZHk8pADnEOYGkVJhe4E/Z8xG49nHXXTcdFr
PApJm85pip2rsgZP1tP5DfAGs1UkU9jFUF9QYQuh3E+K558cdOpBd5O6zV/DXtad
UAfgSBECgYEA5oxSCzVZzdkANiCMVmJ6N+trS3kcA6eyKlHMNwJRKhgP1+toYCg7
vDR5vT7a1+LQKeyLOqFVX9JaaE77X6b/hovneZblb/K0Io6aLuFPXzc1EasGYhZ1
mOkMGKnjM9T9QHJXIswMHZqArCmOohUABdGqW/YXS/KkI5OiON3DwH0CgYEA2+JO
t3nOB9Q0FTBBOcLyfycdaBUDQBq6JvGfYVGvQlORlRlqCIMR4VtHuAd5dB9t/hmW
d6xm75Z2XDJQiwffwYrEHEADfVVhbLvydj9I+JAkh4HnlOkuJCOISjeZmea0dFOd
1zggb377MuAo4vguzQV9gJYTNQoUpyF7EZqlpmUCgYB8y4oBnTBuV79gjT/J5uaH
bHyYzwbWB6lOdRaY1D1BDuNMmpXWLxEesD0RrnthjtnlR7CZ3QjMpJ3hhpdVUJ1S
pFp5G7A4Z+UQK6bUJ4wCW2zzkmMTJ1simUu98gAVZ35qqzn1kQQh5icuihQ2Mi3f
+H1B6DT2HHKy+1A9ffVfNQKBgQCcDm0RuOgqFEh2tU3Fof+bkPZE9YzeBVoS46/b
US8S4t7TNDtWGTgqei9XhC6F5PyauCxbeUeBSYdtfeQ+GHONGGCBMEmJvXwswOOf
WuD+UMcsSV1ECY7O5U0IZ5eja+KtIN9IbTRQDY5ZGFDMbZpBtmDRTzIIlcP8rj17
TAe/JQKBgQCkcFdvvPKgWRhiMpTjo1klyeI2saXiN1C8wIF24P9aXPzGrS4+iFxC
iN7MGIL/AA6/Bo3DVrmPc5spAiFOn5M2URapOnm3RVTJPUWD5OzLk/6AlpOx2YaK
+IUgKgPeZjBZhlOGPJD3WlxAy/xvPdDGhgBrSq8aXto8lTIk5eveBw==
-----END RSA PRIVATE KEY-----"""


@lazypage_decorator
def tools_rsa(request):

    import time
    time.sleep(3)

    rsa_key = rsa_pub_key = ''

    if request.method == 'POST':
        rsa_key = request.POST.get('rsa_key', '').strip()
        submit = request.POST.get('submit')

        if submit == u'私钥示例':
            rsa_key = RSA_KEY_EXAMPLE
            return render_to_response('tools_rsa.html', locals())
        elif submit == u'提取公钥':
            if not rsa_key:
                msg = u'请填写私钥'
                return render_to_response('tools_rsa.html', locals())
            open('/tmp/r.key', 'w').write(rsa_key)
        else:
            os.popen('openssl genrsa -out /tmp/r.key').read()
            rsa_key = open('/tmp/r.key').read()

        print 'rsa key:'
        print rsa_key

        rsa_pub_key = os.popen('openssl rsa -in /tmp/r.key -pubout').read()

        print 'rsa pub key'
        print rsa_pub_key

        if not rsa_pub_key:
            msg = u'私钥填写有误，请参考私钥示例'

    return render_to_response('tools_rsa.html', locals())

