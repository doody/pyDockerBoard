from django.conf.urls import patterns, url

from api_helper import views


urlpatterns = patterns('',
                       url(r'^git_projects', views.fetch_git_project),
                       url(r'^redmine_issues', views.fetch_redmine_project),
                       url(r'^docker', views.fetch_docker_container)
)