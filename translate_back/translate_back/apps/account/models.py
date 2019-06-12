# -*- coding utf-8 -*-
from django.db import models


# Create your models here.
# 个人信息
class Account(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='主键')
    nickName = models.CharField(verbose_name='微信昵称')
    avatarUrl = models.CharField(verbose_name='头像链接')
    gender = models.IntegerField(verbose_name='性别标识')
    country = models.CharField(verbose_name='国家')
    province = models.CharField(verbose_name='省份')
    city = models.CharField(verbose_name='城市')
    language = models.CharField(verbose_name='语言')
    penName = models.CharField(verbose_name='笔名')


# 译文投递表
class Article(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='主键')
    title = models.CharField(verbose_name='标题')
    originUrl = models.CharField(verbose_name='原文链接')
    status = models.IntegerField(default=0, verbose_name='投递状态0：审核中 1.审核通过 2. 审核拒绝')
    createAccount = models.ForeignKey(Account, verbose_name='创建者')
    createTime = models.DateTimeField(verbose_name='创建时间')
    auditAccount = models.ForeignKey(Account, verbose_name='审核者')
    auditTime = models.DateTimeField(verbose_name='审核时间')
    endTime = models.DateTimeField(verbose_name='翻译流程结束时间')


# 每期翻译记录
class Period(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='主键')
    name = models.CharField(verbose_name='期名称')
    mark = models.CharField(verbose_name='附加信息')
    published = models.BooleanField(default=False, verbose_name='是否发布')
    publishedTime = models.DateTimeField(verbose_name='发布时间')
    publishedAccount = models.ForeignKey(verbose_name='发布者')
    createTime = models.DateTimeField(verbose_name='创建时间')
    createAccount = models.ForeignKey(Account, verbose_name='创建者')


# 译文竞选表
class Campaign(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='主键')
    articleId = models.ForeignKey(Article, verbose_name='译文ID')
    periodId = models.ForeignKey(Period, verbose_name='所属期数')
    status = models.IntegerField(default=0, verbose_name='状态 0:默认未发布 1:已被竞选翻译 2:已被竞选校验 3:翻译完成 4:校验完成 5:流程结束')
    translateAccount = models.ForeignKey(Account, verbose_name='翻译者')
    translateStartTime = models.DateTimeField(verbose_name='翻译开始时间')
    translateEndTime = models.DateTimeField(verbose_name='翻译结束时间')
    checkAccount = models.ForeignKey(Account, verbose_name='校验者')
    checkStartTime = models.DateTimeField(verbose_name='校验开始时间')
    checkEndTime = models.DateTimeField(verbose_name='校验结束时间')

