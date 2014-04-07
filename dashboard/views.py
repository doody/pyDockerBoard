import json
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from api_helper import handler

from api_helper.models import GITGroup, GITProject, GITBranch, RMIssue, RMStatus, UpdateRecord


def index(request):
    # Redirect to first group
    group = GITGroup.objects.all()[0]
    return HttpResponseRedirect(reverse('dashboard.views.view_group_project', args=(group.name, None)))


def view_group_project(request, group_name=None, project_name=None):
    # Get Group list
    group_list = GITGroup.objects.all()

    # Get Group
    try:
        group = GITGroup.objects.get(name=group_name)
    except GITGroup.DoesNotExist:
        context = {'group_list': group_list,
                   'error': "Group Not Found"}
        return render(request, "content_error.html", context)

    # Get project list
    project_list = GITProject.objects.filter(group=group)

    # Get Project if name provided
    if project_name is not None:
        try:
            project = GITProject.objects.get(name=project_name)
        except GITProject.DoesNotExist:
            context = {'group': group,
                       'group_list': group_list,
                       'error': "Project Not Found"}
            return render(request, "content_error.html", context)
    # Get first project in group when project name not specified
    else:
        if not project_list:
            context = {'group': group,
                       'group_list': group_list,
                       'error': "Project Not Found"}
            return render(request, "content_error.html", context)
        else:
            return HttpResponseRedirect(reverse('dashboard.views.view_group_project',
                                                args=(group.name, project_list[0].name)))

    # Get production status
    production_status = GITBranch.objects.filter(name__in=["master", "develop", "release"], project=project)

    context = {'group': group,
               'project': project,
               'group_list': group_list,
               'project_list': project_list,
               'production_status': production_status}

    return render(request, "project.html", context)


def view_issue_table(request, group_name=None, project_name=None):
    # Get Project if name provided
    if project_name is not None:
        try:
            project = GITProject.objects.get(name=project_name)
        except GITProject.DoesNotExist:
            return HttpResponse("Project Not Found")

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

    # Get issue list
    production_status = GITBranch.objects.filter(name__in=["master", "develop", "release"], project=project)

    resolved_status = RMStatus.objects.get(name="Resolved")
    feedback_status = RMStatus.objects.get(name="Feedback")
    resolved_issues = RMIssue.objects.filter(status__in=[resolved_status, feedback_status],
                                             project__git_project=project)

    context = {'production_status': production_status,
               'resolved_issues': resolved_issues}

    return render(request, "issue_table.html", context)