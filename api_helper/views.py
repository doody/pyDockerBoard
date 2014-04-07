from datetime import timedelta
import json

from django.utils import timezone
from django.http import HttpResponse

from api_helper.models import UpdateRecord
import handler


def fetch_git_project(request):
    # Get last update record
    update_record, created = UpdateRecord.objects.get_or_create(provider="GITLAB")
    duration = timezone.now().replace(tzinfo=None) - update_record.last_update.replace(tzinfo=None)

    force_update = False or created
    if 'force_update' in request.GET:
        force_update = True

    # Do not update if last update time less then 1 hour and not force update
    if duration < timedelta(hours=1) and not force_update:
        return HttpResponse(json.dumps({'status': "OK", 'last_update': str(update_record.last_update)}))

    error = handler.get_gitlab_projects()

    if error is not None:
        return HttpResponse(json.dumps({'status': "ERROR", 'message': error}))

    update_record.last_update = timezone.now()
    update_record.save()

    return HttpResponse(json.dumps({'status': "OK", 'last_update': str(update_record.last_update)}))


def fetch_redmine_project(request):
    # Get last update record
    update_record, created = UpdateRecord.objects.get_or_create(provider="REDMINE")

    if created is True:
        error = handler.get_redmine_issues()
    else:
        error = handler.get_redmine_issues(last_update=update_record.last_update)

    if error is not None:
        print error
        return HttpResponse(json.dumps({'status': "ERROR", 'message': error}))

    update_record.last_update = timezone.now()
    update_record.save()

    return HttpResponse(json.dumps({'status': "OK", 'last_update': str(update_record.last_update)}))


def fetch_docker_container(request):
    # Get last update record
    update_record, created = UpdateRecord.objects.get_or_create(provider="DOCKER")
    duration = timezone.now().replace(tzinfo=None) - update_record.last_update.replace(tzinfo=None)

    force_update = False
    if 'force_update' in request.GET:
        force_update = True

    # Do not update if last update time less then 1 hour and not force update
    if duration < timedelta(hours=1) and not force_update:
        return HttpResponse(json.dumps({'status': "OK", 'last_update': str(update_record.last_update)}))

    error = handler.get_docker_container_list()

    if error is not None:
        return HttpResponse(json.dumps({'status': "ERROR", 'message': error}))

    update_record.last_update = timezone.now()
    update_record.save()

    return HttpResponse(json.dumps({'status': "OK", 'last_update': str(update_record.last_update)}))