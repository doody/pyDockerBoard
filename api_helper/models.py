from django.db import models


class UpdateRecord(models.Model):
    provider = models.CharField(max_length=50, primary_key=True)
    last_update = models.DateTimeField(auto_now=True)


class User(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField(primary_key=True)
    redmine_id = models.IntegerField(blank=True, null=True)
    redmine_token = models.CharField(max_length=100, blank=True, null=True)
    gitlab_id = models.IntegerField(blank=True, null=True)
    gitlab_token = models.CharField(max_length=100, blank=True, null=True)


class GITGroup(models.Model):
    id = models.BigIntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=100)
    updated_at = models.DateTimeField(blank=True, null=True)


class GITProject(models.Model):
    id = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)
    web_url = models.URLField()
    name = models.CharField(max_length=100)
    last_activity_at = models.DateTimeField()
    group = models.ForeignKey('GITGroup')


class GITCommit(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    message = models.TextField(blank=True, null=True)
    author = models.ForeignKey('User', related_name="author")
    committer = models.ForeignKey('User', related_name="committer")
    authored_date = models.DateTimeField()
    committed_date = models.DateTimeField()


class GITBranch(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey('GITProject')
    is_default = models.BooleanField(default=False)
    is_protected = models.BooleanField(default=False)
    last_commit = models.ForeignKey('GITCommit')


class RMProject(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    git_project = models.ForeignKey('GITProject', blank=True, null=True)


class RMTracker(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)


class RMStatus(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)


class RMPriority(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)


class RMCategory(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)


class RMIssue(models.Model):
    id = models.IntegerField(primary_key=True)
    project = models.ForeignKey('RMProject')
    tracker = models.ForeignKey('RMTracker')
    status = models.ForeignKey('RMStatus')
    priority = models.ForeignKey('RMPriority')
    author = models.ForeignKey('User')
    category = models.ForeignKey('RMCategory', blank=True, null=True)
    subject = models.CharField(max_length=100)
    created_on = models.DateTimeField()
    updated_on = models.DateTimeField()
    git_branch = models.ForeignKey('GITBranch', blank=True, null=True)
    test_result = models.CharField(max_length=10, blank=True, null=True)
    test_date = models.DateTimeField(blank=True, null=True)


class DKContainer(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    image = models.CharField(max_length=100)
    created_on = models.DateTimeField()
    is_running = models.BooleanField(default=False)
    git_branch = models.ForeignKey('GITBranch', blank=True, null=True)
    entry_point = models.CharField(max_length=30, blank=True, null=True)
    deploy_port = models.IntegerField(blank=True, null=True)
    deploy_commit = models.CharField(max_length=100, blank=True, null=True)