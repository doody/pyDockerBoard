from django.conf.urls import patterns, url

from dashboard import views, api


urlpatterns = patterns('',
                       url(r'^$', views.index),
                       url(r'^start/(?P<issue_id>\d+)/$', api.start_container),
                       url(r'^stop/(?P<issue_id>\d+)/$', api.stop_container),
                       url(r'^delete/(?P<issue_id>\d+)', api.delete_container),
                       url(r'^deploy/(?P<issue_id>\d+)/status/$', api.check_deploy_status),
                       url(r'^deploy/(?P<issue_id>\d+)/update/$', api.update_deploy_status),
                       url(r'^test/(?P<issue_id>\d+)/(?P<status>\w+)/$', api.change_test_result),
                       url(r'^(?P<group_name>\w+)/$', views.view_group_project),
                       url(r'^(?P<group_name>\w+)/(?P<project_name>\w+)/$', views.view_group_project),
                       url(r'^(?P<group_name>\w+)/(?P<project_name>\w+)/issues/$', views.view_issue_table),
                       # url(r'^docker', views.fetch_docker_container)
)