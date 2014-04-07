from datetime import datetime
import json

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404

from api_helper import handler
from api_helper.models import *


def return_400_error_message(message=None):
    response = HttpResponse(json.dumps({'status': "ERROR", 'message': message}))
    response.status_code = 400
    return response


def start_container(request, issue_id=None):
    if issue_id is None:
        return return_400_error_message("Issue ID cannot be None")
    else:
        # Get related git branch
        try:
            git_branch = GITBranch.objects.filter(name="t" + str(issue_id))[0]
        except GITBranch.DoesNotExist:
            return return_400_error_message("Cannot find branch")

        # Start docker container
        print 'Starting Docker Container : ' + str(issue_id)

        try:
            container = git_branch.dkcontainer_set.all()[:1].get()
            container_id = container.id
        except DKContainer.DoesNotExist:
            create_result = handler.create_container(str(issue_id))
            if create_result['status'] == "OK":
                container_id = create_result['container_id']
            else:
                return return_400_error_message(create_result['message'])

        # Start Container
        start_result = handler.start_container(container_id)

        if start_result['status'] != "OK":
            return return_400_error_message(start_result['message'])

        # Inspect Container Info
        inspect_result = handler.inspect_container(container_id)

        if inspect_result['status'] != "OK":
            return return_400_error_message(inspect_result['message'])

        # Save container info to DB
        c = DKContainer(
            id=inspect_result['id'],
            image=inspect_result['image'],
            created_on=inspect_result['created_on'],
            git_branch=git_branch,
            is_running=inspect_result['is_running'],
            deploy_port=inspect_result['deploy_port']
        )
        c.save()

        # Build and deploy
        handler.deploy_container(git_branch.project.name,
                                 git_branch.name,
                                 inspect_result['deploy_port'])

        return HttpResponse(json.dumps({'status': "OK"}))


def stop_container(request, issue_id=None):
    if issue_id is None:
        return return_400_error_message("Issue ID cannot be None")
    else:
        # Get related git branch
        try:
            git_branch = GITBranch.objects.filter(name="t" + str(issue_id))[0]
        except GITBranch.DoesNotExist:
            return return_400_error_message("Cannot find branch")

        container = git_branch.dkcontainer_set.all()[0]
        container_id = container.id

        # Stop docker container
        result = handler.stop_container(container_id)

        if result['status'] != "OK":
            return return_400_error_message(result['message'])

        container.is_running = False
        container.save()

        return HttpResponse(json.dumps({'status': "OK"}))


def delete_container(request, issue_id=None):
    if issue_id is None:
        return return_400_error_message("Issue ID cannot be None")
    else:
        # Get related git branch
        try:
            git_branch = GITBranch.objects.filter(name="t" + str(issue_id))[0]
        except GITBranch.DoesNotExist:
            return return_400_error_message("Cannot find branch")

        # Stop docker container
        container = git_branch.dkcontainer_set.all()[0]
        container_id = container.id

        result = handler.delete_container(container_id)

        if result['status'] != "OK":
            return return_400_error_message(result['message'])

        container.delete()

        return HttpResponse(json.dumps({'status': "OK"}))


def change_test_result(request, issue_id=None, status=None):
    if issue_id is None:
        return return_400_error_message("Issue ID cannot be None")
    else:
        # Get related issue branch
        try:
            issue = RMIssue.objects.get(pk=issue_id)
        except RMIssue.DoesNotExist:
            return return_400_error_message("Cannot find issue")

    if issue is not None:
        issue.test_result = status
        issue.test_date = datetime.now()
        issue.save()

    return HttpResponse(json.dumps({'status': "OK"}))


def check_deploy_status(request, issue_id=None):
    if issue_id is None:
        return return_400_error_message("Issue ID cannot be None")
    else:
        # Get related issue branch
        try:
            issue = RMIssue.objects.get(pk=issue_id)
        except RMIssue.DoesNotExist:
            return return_400_error_message("Cannot find issue")

    container = issue.git_branch.dkcontainer_set.all()[0]

    return HttpResponse(json.dumps({'status': "OK",
                                    'deploy_port': container.deploy_port,
                                    'entry_point': container.entry_point,
                                    'commit': container.deploy_commit}))


@csrf_exempt
def update_deploy_status(request, issue_id=None):
    if request.method == "POST":
        if issue_id is None:
            return return_400_error_message("Issue ID cannot be None")
        else:
            # Get related issue branch
            try:
                issue = RMIssue.objects.get(pk=issue_id)
            except RMIssue.DoesNotExist:
                return return_400_error_message("Cannot find issue")

        print request.body
        json_data = json.loads(request.body)
        if json_data['package_name'] is None:
            return return_400_error_message("package_name cannot be None")

        if json_data['commit_id'] is None:
            return return_400_error_message("commit_id cannot be None")

        container = issue.git_branch.dkcontainer_set.all()[0]
        container.entry_point = json_data['package_name']
        container.deploy_commit = json_data['commit_id']
        container.save()

        return HttpResponse(json.dumps({'status': "OK"}))

    else:
        raise Http404