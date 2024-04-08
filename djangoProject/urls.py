"""djangoProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

from myApp import userdevelop, manager, userBasic, userPlan, debug, AI, shareDoc,file,mail
from myApp import notice, userChat
from django.urls import re_path
from myApp import chatConsumer


websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<userId>\w+)/(?P<roomId>\w+)$",
            chatConsumer.ChatConsumer.as_asgi()),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/userBindRepo', userdevelop.UserBindRepo.as_view()),
    path('api/management/showUsers', manager.ShowUsers.as_view()),
    path('api/management/showAdmins', manager.ShowAdmins.as_view()),
    path('api/management/changeUserStatus', manager.ChangeUserStatus.as_view()),
    path('api/management/resetUserPassword', manager.ResetUserPassword.as_view()),
    path('api/management/showAllProjects', manager.ShowAllProjects.as_view()),
    path('api/management/changeProjectStatus', manager.ChangeProjectStatus.as_view()),
    path('api/management/changeProjectAccess', manager.ChangeProjectAccess.as_view()),
    path('api/management/showUsersLogin', manager.ShowUsersLogin.as_view()),
    path('api/management/getUserNum', manager.GetUserNum.as_view()),
    path('api/management/getProjectNum', manager.GetProjectNum.as_view()),
    path('api/management/getProjectsScale', manager.GetProjectScale.as_view()),
    path('api/develop/getProjectName', userdevelop.GetProjectName.as_view()),
    path('api/develop/getBindRepos', userdevelop.GetBindRepos.as_view()),
    path('api/develop/userBindRepo', userdevelop.UserBindRepo.as_view()),
    path('api/develop/userUnbindRepo', userdevelop.UserUnbindRepo.as_view()),
    path('api/develop/getRepoBranches', userdevelop.GetRepoBranches.as_view()),
    path('api/develop/getCommitHistory', userdevelop.GetCommitHistory.as_view()),
    path('api/develop/getIssueList', userdevelop.GetIssueList.as_view()),
    path('api/develop/getPrList', userdevelop.GetPrList.as_view()),
    path('api/develop/getFileTree', userdevelop.GetFileTree.as_view()),
    path('api/develop/getContent', userdevelop.GetContent.as_view()),
    path('api/register', userBasic.register),
    path('api/login', userBasic.login),
    path('api/getUserInfo', userBasic.get_user_information),
    path('api/user/information/password', userBasic.modify_password),
    path('api/showProfile', userBasic.show),
    path('api/editProfile', userBasic.modify_information),
    path('api/saveTopic', userBasic.save_topic),
    path('api/plan/newProject', userPlan.newProject.as_view()),
    path('api/plan/watchAllProject', userPlan.watchAllProject.as_view()),
    path('api/plan/addTask', userPlan.addTask.as_view()),
    path('api/plan/addSubTask', userPlan.addSubTask.as_view()),
    path('api/plan/showTaskList', userPlan.showTaskList.as_view()),
    path('api/plan/modifyTaskContent', userPlan.modifyTaskContent.as_view()),
    path('api/plan/showPersonList', userPlan.showPersonList.as_view()),
    path('api/plan/modifyRole', userPlan.modifyRole.as_view()),
    path('api/plan/addMember', userPlan.addMember.as_view()),
    path('api/plan/removeMember', userPlan.removeMember.as_view()),
    path('api/plan/deleteProject', userPlan.deleteProject.as_view()),
    path('api/plan/modifyProject', userPlan.modifyProject.as_view()),
    path('api/plan/completeTask', userPlan.completeTask.as_view()),
    path('api/plan/notice', userPlan.notice.as_view()),
    path('api/plan/watchMyTask', userPlan.watchMyTask.as_view()),
    path('api/plan/test', userPlan.test.as_view()),
    path('api/plan/removeTask', userPlan.removeTask.as_view()),
    path('api/plan/modifyProjectStatus', userPlan.modifyProjectStatus.as_view()),
    path('api/plan/showNoticeList', userPlan.showNoticeList.as_view()),
    path('api/plan/modifyNotice', userPlan.modifyNotice.as_view()),
    path('api/plan/removeNotice', userPlan.removeNotice.as_view()),
    path('api/echo', debug.echo),
    path('api/notice/userPostNoticeToAll', notice.UserPostNoticeToAll.as_view()),
    path('api/notice/userPostNoticeToOne', notice.UserPostNoticeToOne.as_view()),
    path('api/notice/sysPostNoticeInProject', notice.SysPostNoticeInProject.as_view()),
    path('api/notice/sysPostNoticeToAll', notice.SysPostNoticeToAll.as_view()),
    path('api/notice/userGetNotice', notice.UserGetNotice.as_view()),
    path('api/notice/userConfirmNotice', notice.UserConfirmNotice.as_view()),
    path('api/plan/getEmail', userPlan.getEmail.as_view()),
    path('api/ai/UnitTest', AI.UnitTest.as_view()),
    path('api/ai/CodeReview', AI.CodeReview.as_view()),
    path('api/plan/showContribute',userPlan.showContribute.as_view()),
    path('api/plan/changeOrder',userPlan.changeOrder.as_view()),
    path('api/doc/userDocList', shareDoc.UserDocList.as_view()),
    path('api/doc/userCollectDocList', shareDoc.UserCollectDocList.as_view()),
    path('api/doc/addDocToCollect', shareDoc.AddDocToCollect.as_view()),
    path('api/doc/delDocFromCollect', shareDoc.DelDocFromCollect.as_view()),
    path('api/doc/userCreateDoc', shareDoc.UserCreateDoc.as_view()),
    path('api/doc/userEditDocContent', shareDoc.UserEditDocContent.as_view()),
    path('api/doc/userGetDocLock', shareDoc.UserGetDocLock.as_view()),
    path('api/doc/userReleaseDocLock', shareDoc.UserReleaseDocLock.as_view()),
    path('api/doc/userEditDocOther', shareDoc.UserEditDocOther.as_view()),
    path('api/doc/userDelDoc', shareDoc.UserDelDoc.as_view()),
    path('api/doc/isDocLocked', shareDoc.IsDocLocked.as_view()),
    path('api/chat/discussions', userChat.get_user_public_groups),
    path('api/chat/private', userChat.get_user_private_groups),
    path('api/chat/getRoomMessages', userChat.get_room_content),
    path('api/chat/createRoom', userChat.create_public_group),
    path('api/chat/createPrivate', userChat.create_private_group),
    path('api/chat/addPerson', userChat.add_user_to_group),
    path('api/chat/deletePerson', userChat.delete_user_from_group),
    # path('api/doc/docTimeUpdate', shareDoc.DocTimeUpdate.as_view()),
    path('api/plan/ProjectInfo',userPlan.ProjectInfo.as_view()),
    path('api/file/uploadFile',file.uploadFile.as_view()),
    path('api/file/downloadFile',file.downloadFile.as_view()),
    path('api/file/watchFiles',file.watchFiles.as_view()),
    path('api/mailTest', mail.MailTest.as_view()),
]
