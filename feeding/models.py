# -*- coding: utf-8 -*-
import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Feeding(models.Model):

    POSITION_CHOICES = (
        (1, u'左'),
        (2, u'右'),
    )
    user = models.ForeignKey(User)
    position = models.IntegerField(choices=POSITION_CHOICES, default=1)
    begin = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(blank=True, null=True)

    @property
    def duration(self):
        if not self.end:
            self.end = timezone.now()
        t = self.end - self.begin
        total_seconds = t.total_seconds()
        m = (total_seconds + 30) / 60
        return '%d 分钟' % m
