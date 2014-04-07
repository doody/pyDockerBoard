import json
import re
from datetime import datetime

from dateutil import parser
import requests

from api_helper.models import DKContainer, RMProject, GITProject, RMTracker, RMPriority, RMStatus, RMCategory, User, \
    GITBranch, RMIssue, GITGroup, GITCommit
from pyDockerBoard import settings


def get_docker_container_list():
    # Fetch docker info
    r = requests.get(settings.DOCKER_API_URL + '/containers/json')

    if r.status_code != 200:
        return r.text

    for container in r.json():
        c = DKContainer(
            id=container['Id'],
            image=container['Image'],
            created_on=datetime.fromtimestamp(container['Created'])
        )
        c.save()

        ports = container['Ports']

        for port in ports:
            if port['PrivatePort'] == 8080:
                c.deploy_port = port['PublicPort']
                c.save()


def get_redmine_issues(last_update=None):
    # Fetch project issues
    headers = {'X-Redmine-API-Key': settings.REDMINE_API_KEY}

    http_params = {}
    if last_update is not None:
        http_params['updated_on'] = ">=" + last_update.strftime('%Y-%m-%d')

    r = requests.get(settings.REDMINE_API_URL + '/issues.json', headers=headers, params=http_params, verify=False)

    if r.status_code != 200:
        return r.text

    total_count = r.json()['total_count']
    limit = r.json()['limit']

    pages = total_count / limit

    for page in range(pages):
        if page == 0:
            issues = r.json()['issues']
        else:
            http_params['offset'] = page * limit
            print http_params
            issues = requests.get(settings.REDMINE_API_URL + '/issues.json',
                                  params=http_params, headers=headers, verify=False).json()['issues']

            if r.status_code != 200:
                return r.text

        for issue in issues:
            project = RMProject.objects.get_or_create(name=issue['project']['name'])[0]
            try:
                git_project = GITProject.objects.get(name=project.name)
                project.git_project = git_project
                project.save()
            except GITProject.DoesNotExist:
                continue

            if project is not None:
                tracker = RMTracker.objects.get_or_create(id=issue['tracker']['id'],
                                                          name=issue['tracker']['name'])[0]
                status = RMStatus.objects.get_or_create(id=issue['status']['id'],
                                                        name=issue['status']['name'])[0]
                priority = RMPriority.objects.get_or_create(id=issue['priority']['id'],
                                                            name=issue['priority']['name'])[0]
                # This is an optional field
                if 'category' in issue:
                    category = RMCategory.objects.get_or_create(id=issue['category']['id'],
                                                                name=issue['category']['name'])[0]
                else:
                    category = None

                # Fetch user info
                r = requests.get(settings.REDMINE_API_URL + '/users/' + str(issue['author']['id']) + '.json',
                                 headers=headers, verify=False)

                if r.status_code == 200:
                    resp_user = r.json()['user']
                    author = User.objects.get_or_create(email=resp_user['mail'])[0]
                    author.redmine_id = resp_user['id']
                    author.save()

                    branch_name = "t" + str(issue['id'])
                    try:
                        branch = GITBranch.objects.get(name=branch_name, project=project.git_project)
                        issue_to_save = RMIssue(
                            id=issue['id'],
                            project=project,
                            tracker=tracker,
                            status=status,
                            priority=priority,
                            author=author,
                            category=category,
                            subject=issue['subject'],
                            created_on=issue['created_on'],
                            updated_on=issue['updated_on'],
                            git_branch=branch
                        )

                    except GITBranch.DoesNotExist:
                        issue_to_save = RMIssue(
                            id=issue['id'],
                            project=project,
                            tracker=tracker,
                            status=status,
                            priority=priority,
                            author=author,
                            category=category,
                            subject=issue['subject'],
                            created_on=issue['created_on'],
                            updated_on=issue['updated_on']
                        )

                    issue_to_save.save()


def get_gitlab_projects():
    # Fetch git group data
    headers = {'PRIVATE-TOKEN': settings.GIT_LAB_API_KEY}
    r = requests.get(settings.GIT_LAB_API_URL + '/groups', headers=headers, verify=False)

    if r.status_code != 200:
        return r.text

    for group in r.json():
        g = GITGroup(
            id=group['id'],
            name=group['name'],
            path=group['path']
        )
        g.save()

    # Fetch git project data
    r = requests.get(settings.GIT_LAB_API_URL + '/projects', headers=headers, verify=False)

    if r.status_code != 200:
        return r.text

    for project in r.json():
        g = GITGroup.objects.get(id=project['namespace']['id'])
        g.description = project['namespace']['description']
        g.updated_at = project['namespace']['updated_at']
        g.save()

        p = GITProject(
            id=project['id'],
            description=project['description'],
            web_url=project['web_url'],
            name=project['name'],
            last_activity_at=project['last_activity_at'],
            group=g
        )
        p.save()

        # Fetch git branch
        r = requests.get(settings.GIT_LAB_API_URL + '/projects/' + str(p.id) + '/repository/branches',
                         headers=headers, verify=False)

        if r.status_code != 200:
            return r.text

        for branch in r.json():
            try:
                author = User.objects.get(email=branch['commit']['author']['email'])
            except User.DoesNotExist:
                author = User(
                    username=branch['commit']['author']['name'],
                    email=branch['commit']['author']['email']
                )
                author.save()

            try:
                committer = User.objects.get(email=branch['commit']['committer']['email'])
            except User.DoesNotExist:
                committer = User(
                    username=branch['commit']['committer']['name'],
                    email=branch['commit']['committer']['email']
                )
                committer.save()

            c = GITCommit(
                id=branch['commit']['id'],
                message=branch['commit']['message'],
                author=author,
                committer=committer,
                authored_date=branch['commit']['authored_date'],
                committed_date=branch['commit']['committed_date'],
            )
            c.save()

            try:
                b = GITBranch.objects.get(project=p, name=branch['name'])
            except GITBranch.DoesNotExist:
                b = GITBranch(
                    project=p,
                    name=branch['name'],
                    is_protected=branch['protected'],
                    last_commit=c
                )
                b.save()


def create_container(name=None):
    # Create Container
    params = {'name': "t" + name}
    post_data = {'Hostname': "t" + name,
                 'Image': "scott/tomcat6"}
    headers = {'content-type': 'application/json'}

    print "API - Creating Container: " + name

    r = requests.post(settings.DOCKER_API_URL + '/containers/create',
                      data=json.dumps(post_data), headers=headers, params=params)

    if r.status_code == 500:
        extract_container_id = re.search('The name (\w+) is already assigned to (\w+).', r.text).group(2)
        if extract_container_id:
            print "API - Name already assign to: " + extract_container_id
            return {'status': "OK", 'container_id': extract_container_id}
        else:
            return {'status': "ERROR", 'message': r.text}

    elif r.status_code == 201:
        return {'status': "OK", 'container_id': r.json()['Id']}
    else:
        return {'status': "ERROR", 'message': r.text}


def start_container(container_id=None):
    if container_id is None:
        return {'status': "ERROR", 'message': "Container id cannot be None"}

    # Start Container
    post_data = {'PublishAllPorts': True}
    headers = {'content-type': 'application/json'}

    print "API - Start container: " + container_id

    r = requests.post(settings.DOCKER_API_URL + '/containers/' + str(container_id) + '/start',
                      data=json.dumps(post_data), headers=headers)

    if r.status_code == 500:
        extract_container_id = re.search('The container (\w+) is already running.', r.text).group(1)
        print "API - Container already running :" + extract_container_id
        if extract_container_id[:12] != container_id:
            return {'status': "ERROR", 'message': r.text}
    elif r.status_code != 204:
        return {'status': "ERROR", 'message': r.text}

    return {'status': "OK", 'container_id': container_id}


def inspect_container(container_id=None):
    if container_id is None:
        return {'status': "ERROR", 'message': "Container id cannot be None"}

    print "API - Inspecting container: " + container_id

    # Inspect Container Info
    r = requests.get(settings.DOCKER_API_URL + '/containers/' + str(container_id) + '/json')

    if r.status_code != 200:
        return {'status': "ERROR", 'message': r.text}

    return {'status': "OK",
            'id': r.json()['ID'],
            'deploy_port': r.json()['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort'],
            'image': r.json()['Image'],
            'created_on': parser.parse(r.json()['Created']),
            'is_running': r.json()['State']['Running']}


def deploy_container(project_name=None, branch_name=None, deploy_port=None):
    if project_name is None:
        return {'status': "ERROR", 'message': "Project name cannot be None"}

    if branch_name is None:
        return {'status': "ERROR", 'message': "Branch name cannot be None"}

    if deploy_port is None:
        return {'status': "ERROR", 'message': "Deploy port cannot be None"}

    print "API - Deploying container: " + branch_name + ", At port: " + deploy_port

    # Calling Jenkins to build and deploy
    requests.get(settings.JENKINS_API_URL + '/' + project_name + '/buildWithParameters?BRANCH=' +
                 branch_name + '&DEPLOYPORT=' + deploy_port)

    return {'status': "OK"}


def stop_container(container_id=None):
    if container_id is None:
        return {'status': "ERROR", 'message': "Container id cannot be None"}

    print "API - Stopping container: " + container_id

    r = requests.post(settings.DOCKER_API_URL + '/containers/' + str(container_id) + '/stop')

    if r.status_code != 204:
        return {'status': "ERROR", 'message': r.text}

    return {'status': "OK"}


def delete_container(container_id=None):
    if container_id is None:
        return {'status': "ERROR", 'message': "Container id cannot be None"}

    print "API - Delete container: " + container_id

    r = requests.delete(settings.DOCKER_API_URL + '/containers/' + str(container_id))

    if r.status_code != 204:
        return {'status': "ERROR", 'message': r.text}

    return {'status': "OK"}