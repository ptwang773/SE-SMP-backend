from django.http import JsonResponse
from myApp.models import *
from django.views import View
from myApp.userChat import delete_user_from_groups
import json
import datetime


# --------------------project level--------------------


class newProject(View):
    def post(self, request):
        response = {'message': "404 not success", "errcode": 1}

        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectName = kwargs.get("projectName")
        projectIntro = kwargs.get("projectIntro")

        project = Project.objects.create(name=projectName, outline=projectIntro, manager_id=request.user, status='B')
        project.save()

        UserProject.objects.create(user_id=request.user, project_id=project, role=UserProject.DEVELOPER)
        response['errcode'] = 0
        response['message'] = "success"
        return JsonResponse(response)


class watchAllProject(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        userProjectRepo = UserProject.objects.filter(user_id=request.user)
        projectList = []
        for i in userProjectRepo:
            projectList.append({
                "projectId": i.project_id.id,
                "projectName": i.project_id.name,
                "projectIntro": i.project_id.outline,
                "state": i.project_id.status,
                "deadline": str(i.project_id.create_time.year) + "-" + str(i.project_id.create_time.month) + "-" + str(
                    i.project_id.create_time.day),
                "managerId": i.project_id.manager_id.id,
                "managerName": i.project_id.manager_id.name,
                "access":i.project_id.access
            })
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = projectList
        return JsonResponse(response)


class deleteProject(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}

        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        tasks = Task.objects.filter(project_id=projectId)
        tasks.delete()
        Project.objects.filter(id=projectId).delete()
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class modifyProject(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        projectName = kwargs.get("projectName", "")
        if projectName != "":
            project = Project.objects.get(id=projectId)
            project.name = projectName
            project.save()

        projectOutline = kwargs.get("projectIntro", "")
        if projectOutline != "":
            project = Project.objects.get(id=projectId)
            project.outline = projectOutline
            project.save()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class modifyProjectStatus(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        status = kwargs.get("status", "")
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        project = Project.objects.get(id=projectId)
        project.status = status
        project.save()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


# ----------------------task level----------------------


class addTask(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        name = kwargs.get("taskName", "")
        projectId = kwargs.get("projectId", 0)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        if UserProject.objects.filter(user_id=request.user, project_id=projectId, role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "permission denied"
            response['data'] = None
            return JsonResponse(response)

        project = Project.objects.get(id=projectId)
        deadline = datetime.datetime(year=2030, month=12, day=31)
        task = Task.objects.create(name=name, project_id=project, deadline=deadline)
        task.status = Task.NOTSTART
        task.order = task.id
        task.save()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = name
        return JsonResponse(response)


class addSubTask(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        time = kwargs.get("deadline", "")
        year, month, day = time.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        contribute = kwargs.get("contribute", 0)
        name = kwargs.get("subTaskName", "")
        projectId = kwargs.get("projectId", -1)
        belongTask = kwargs.get("fatherTaskId", -1)
        managerId = kwargs.get("managerId", -1)
        t = kwargs.get("start_time", "")
        y, m, d = t.split("-")
        y = int(y)
        m = int(m)
        d = int(d)

        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)
        if Task.objects.filter(id=belongTask).count() == 0:
            response['errcode'] = 1
            response['message'] = "task not exist"
            response['data'] = None
            return JsonResponse(response)
        if User.objects.filter(id=managerId).count() == 0:
            response['errcode'] = 1
            response['message'] = "user not exist"
            response['data'] = None
            return JsonResponse(response)
        if UserProject.objects.filter(user_id=request.user, project_id=projectId, role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "permission denied"
            response['data'] = None
            return JsonResponse(response)

        # use time[0] as year time[1] as month time[2] as day
        deadline = datetime.datetime(year=year, month=month, day=day)
        startTime = datetime.datetime(year=y, month=m, day=d)
        task = Task.objects.create(name=name, deadline=deadline, contribute_level=contribute, project_id_id=projectId,
                                   parent_id_id=belongTask, start_time=startTime)
        task.status = Task.NOTSTART
        task.save()

        UserTask.objects.create(user_id_id=managerId, task_id=task)

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class showTaskList(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}

        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        taskList = Task.objects.filter(project_id_id=projectId, parent_id=None).order_by("order")
        data = []
        cur_time = datetime.datetime.now()
        for i in taskList:
            tmp = {"taskName": i.name, "taskId": i.id}
            subTasks = Task.objects.filter(parent_id=i)
            subTaskList = []
            for j in subTasks:
                sub_tmp = {"deadline": j.deadline, "contribute": j.contribute_level,
                           "intro": j.outline, 'managerId': UserTask.objects.get(task_id=j).user_id_id,
                           "subTaskName": j.name, "subTaskId": j.id, "start_time": j.start_time,
                           "complete_time": j.complete_time}

                if j.status != Task.COMPLETED:
                    if cur_time > j.deadline:
                        sub_tmp["status"] = 'E'  # 延期未完成
                    elif cur_time < j.start_time:
                        sub_tmp["status"] = 'C'  # 未开始
                    else:
                        sub_tmp["status"] = 'B'  # 进行中
                else:
                    if j.complete_time > j.deadline:
                        sub_tmp["status"] = 'D'  # 延期完成
                    else:
                        sub_tmp["status"] = 'A'  # 按时完成

                subTaskList.append(sub_tmp)
            tmp["subTaskList"] = subTaskList
            data.append(tmp)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = data
        return JsonResponse(response)


class modifyTaskContent(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        taskId = kwargs.get("taskId", -1)

        deadline = kwargs.get("deadline", "")
        year, month, day = deadline.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        contribute = kwargs.get("contribute", 0)
        taskName = kwargs.get("taskName", "")
        managerId = kwargs.get("managerId", -1)
        startTime = kwargs.get("start_time", "")
        y, m, d = startTime.split("-")
        y = int(y)
        m = int(m)
        d = int(d)

        if Task.objects.filter(id=taskId).count() == 0:
            response['errcode'] = 1
            response['message'] = "task not exist"
            response['data'] = None
            return JsonResponse(response)
        task = Task.objects.get(id=taskId)

        projectId = task.project_id_id
        if UserProject.objects.filter(user_id=request.user, project_id=projectId, role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "permission denied"
            response['data'] = None
            return JsonResponse(response)

        task.deadline = datetime.datetime(year=year, month=month, day=day)
        task.start_time = datetime.datetime(year=y, month=m, day=d)
        task.contribute_level = contribute
        task.name = taskName
        task.save()

        UserTask.objects.filter(task_id=task).delete()
        UserTask.objects.create(user_id_id=managerId, task_id=task)

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class completeTask(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        taskId = kwargs.get("taskId", -1)
        if Task.objects.filter(id=taskId).count() == 0:
            response['errcode'] = 1
            response['message'] = "task not exist"
            response['data'] = None
            return JsonResponse(response)

        task = Task.objects.get(id=taskId)
        projectId = task.project_id_id
        if UserProject.objects.filter(user_id=request.user, project_id=projectId,
                                      role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "permission denied"
            response['data'] = None
            return JsonResponse(response)

        intro = kwargs.get("intro", "")

        task.status = Task.COMPLETED
        task.outline = intro
        task.complete_time = datetime.datetime.now()
        task.save()

        subtasks = Task.objects.filter(parent_id=taskId)
        for i in subtasks:
            i.status = Task.COMPLETED
            i.save()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class watchMyTask(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        taskList = Task.objects.filter(project_id_id=projectId, parent_id=None).order_by("order")
        cur_time = datetime.datetime.now()
        data = []
        for i in taskList:
            tmp = {"taskName": i.name, "taskId": i.id}
            subTasks = UserTask.objects.filter(user_id=request.user, task_id__parent_id=i)
            subTaskList = []
            for subtask in subTasks:
                j = Task.objects.get(id=subtask.task_id_id)
                sub_tmp = {"deadline": j.deadline, "contribute": j.contribute_level,
                           "intro": j.outline, 'managerId': UserTask.objects.get(task_id=j).user_id_id,
                           "subTaskName": j.name, "subTaskId": j.id, "start_time": j.start_time,
                           "complete_time": j.complete_time}

                if j.status != Task.COMPLETED:
                    if cur_time > j.deadline:
                        sub_tmp["status"] = 'E'  # 延期未完成
                    elif cur_time < j.start_time:
                        sub_tmp["status"] = 'C'  # 未开始
                    else:
                        sub_tmp["status"] = 'B'  # 进行中
                else:
                    if j.complete_time > j.deadline:
                        sub_tmp["status"] = 'D'  # 延期完成
                    else:
                        sub_tmp["status"] = 'A'  # 按时完成

                subTaskList.append(sub_tmp)
            tmp["subTaskList"] = subTaskList
            data.append(tmp)

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = data
        return JsonResponse(response)


class removeTask(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        taskId = kwargs.get("taskId", -1)
        if Task.objects.filter(id=taskId).count() == 0:
            response['errcode'] = 1
            response['message'] = "task not exist"
            response['data'] = None
            return JsonResponse(response)

        task = Task.objects.get(id=taskId)
        projectId = task.project_id_id
        if UserProject.objects.filter(user_id=request.user, project_id=projectId,
                                      role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "permission denied"
            response['data'] = None
            return JsonResponse(response)
        task.delete()

        subtasks = Task.objects.filter(parent_id=taskId)
        for i in subtasks:
            i.delete()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


# ----------member level---------------------------


class showPersonList(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}

        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        personList = UserProject.objects.filter(project_id_id=projectId)
        res = []
        for person in personList:
            res.append({
                "peopleId": person.user_id.id,
                "peopleName": person.user_id.name,
                "peopleJob": person.role,
                "peopleEmail": person.user_id.email,
            })

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = res
        return JsonResponse(response)


class modifyRole(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        peopleId = kwargs.get("personId", -1)
        if User.objects.filter(id=peopleId).count() == 0:
            response['errcode'] = 1
            response['message'] = "user not exist"
            response['data'] = None
            return JsonResponse(response)

        role = kwargs.get("role", "")
        if role not in [UserProject.ADMIN, UserProject.NORMAL, UserProject.DEVELOPER]:
            response['errcode'] = 1
            response['message'] = "role not exist"
            response['data'] = None
            return JsonResponse(response)

        if UserProject.objects.filter(user_id=request.user, project_id_id=projectId,
                                      role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "user not admin"
            response['data'] = None
            return JsonResponse(response)

        userProject = UserProject.objects.get(user_id=peopleId, project_id=projectId)
        userProject.role = role
        userProject.save()
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class addMember(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        nameOrEmail = kwargs.get("nameOrEmail", "")
        if User.objects.filter(name=nameOrEmail).count() == 0 and User.objects.filter(email=nameOrEmail).count() == 0:
            response['errcode'] = 1
            response['message'] = "user not exist"
            response['data'] = None
            return JsonResponse(response)

        if User.objects.filter(name=nameOrEmail).count() > 0:
            peopleId = User.objects.get(name=nameOrEmail).id
        else:
            peopleId = User.objects.get(email=nameOrEmail).id

        if UserProject.objects.filter(user_id_id=peopleId, project_id_id=projectId).count() != 0:
            response['errcode'] = 2
            response['message'] = "user already in project"
            response['data'] = None
            return JsonResponse(response)

        if UserProject.objects.filter(user_id=request.user, project_id_id=projectId,
                                      role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "user not admin"
            response['data'] = None
            return JsonResponse(response)

        UserProject.objects.create(user_id_id=peopleId, project_id_id=projectId, role=UserProject.NORMAL)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class removeMember(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        peopleId = kwargs.get("personId", -1)
        if User.objects.filter(id=peopleId).count() == 0:
            response['errcode'] = 1
            response['message'] = "user not exist"
            response['data'] = None
            return JsonResponse(response)

        if UserProject.objects.filter(user_id=peopleId, project_id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "user not in project"
            response['data'] = None
            return JsonResponse(response)

        if UserProject.objects.filter(user_id=request.user, project_id_id=projectId,
                                      role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "user not admin"
            response['data'] = None
            return JsonResponse(response)

        a = UserProject.objects.filter(user_id_id=peopleId, project_id_id=projectId)

        # ids=[]
        # for i in a:
        #     ids.append(i.user_id)
        delete_user_from_groups(user_id=int(peopleId), project_id=int(projectId))

        UserProject.objects.filter(user_id_id=peopleId, project_id_id=projectId).delete()
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class getEmail(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        peopleId = kwargs.get("personId", -1)
        if User.objects.filter(id=peopleId).count() == 0:
            response['errcode'] = 1
            response['message'] = "user not exist"
            return JsonResponse(response)

        user = User.objects.get(id=peopleId)
        email = str(user.email)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = email
        return JsonResponse(response)


# -----------------notice level------------------------
class notice(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        taskId = kwargs.get("taskId", -1)
        deadline = kwargs.get("deadline", "")
        year, month, day, hour, minute = deadline.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        if Task.objects.filter(id=taskId).count() == 0:
            response['errcode'] = 1
            response['message'] = "task not exist"
            response['data'] = None
            return JsonResponse(response)

        msg = Notice.objects.create(belongingTask_id=taskId,
                                    deadline=datetime.datetime(year=year, month=month, day=day, hour=hour,
                                                               minute=minute))
        msg.save()
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None
        return JsonResponse(response)


class showNoticeList(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)

        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        taskList = Task.objects.filter(project_id_id=projectId)
        data = []
        for i in taskList:
            notices = Notice.objects.filter(belongingTask=i)
            for j in notices:
                sub_tmp = {"noticeId": j.id, "taskId": i.id, "deadline": j.deadline}
                data.append(sub_tmp)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = data

        return JsonResponse(response)


class modifyNotice(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        noticeId = kwargs.get("noticeId", -1)
        if Notice.objects.filter(id=noticeId).count() == 0:
            response['errcode'] = 1
            response['message'] = "notice not exist"
            response['data'] = None
            return JsonResponse(response)
        notice = Notice.objects.get(id=noticeId)
        deadline = kwargs.get("deadline", "")
        year, month, day, hour, minute = deadline.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        notice.deadline = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        notice.save()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None

        return JsonResponse(response)


class removeNotice(View):
    def post(self, request):
        response = {'errcode': 1, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        noticeId = kwargs.get("noticeId", -1)
        if Notice.objects.filter(id=noticeId).count() == 0:
            response['errcode'] = 1
            response['message'] = "notice not exist"
            response['data'] = None
            return JsonResponse(response)
        this_notice = Notice.objects.get(id=noticeId)
        this_notice.delete()

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = None

        return JsonResponse(response)


class test(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        # try:
        #     kwargs: dict = json.loads(request.body)
        # except Exception:
        #     return JsonResponse(response)
        projects = Project.objects.all()
        ids = []
        for i in projects:
            tmp = {"id": i.id}
            u2p = UserProject.objects.filter(project_id=i.id)
            roles = []
            for j in u2p:
                roles.append(j.role)
            tmp["roles"] = roles
            tmp["status"] = i.status
            ids.append(tmp)

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = ids
        return JsonResponse(response)


class showContribute(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        if UserProject.objects.filter(user_id=request.user, project_id_id=projectId,
                                      role=UserProject.NORMAL).count() > 0:
            response['errcode'] = 3
            response['message'] = "user not admin"
            response['data'] = None
            return JsonResponse(response)

        members = UserProject.objects.filter(project_id_id=projectId)
        ans = {}
        for member in members:
            i = member.user_id
            cb = 0
            tasks = UserTask.objects.filter(user_id=i)
            for task in tasks:
                j = task.task_id
                if j.project_id_id == projectId:
                    cb += j.contribute_level
            ans[i.name] = cb

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = ans
        return JsonResponse(response)


class changeOrder(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        task1Id = kwargs.get("task1Id", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "task1 not exist"
            response['data'] = None
            return JsonResponse(response)

        task2Id = kwargs.get("task2Id", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "task2 not exist"
            response['data'] = None
            return JsonResponse(response)

        if task1Id == 0 or task2Id == 0:
            response['errcode'] = 0
            response['message'] = "not change"
            return JsonResponse(response)

        task1 = Task.objects.get(id=task1Id)
        task2 = Task.objects.get(id=task2Id)
        order1 = task1.order
        order2 = task2.order
        task1.order = order2
        task2.order = order1
        task1.save()
        task2.save()

        response['errcode'] = 0
        response['message'] = "success"
        return JsonResponse(response)


class ProjectInfo(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        projectId = kwargs.get("projectId", -1)
        if Project.objects.filter(id=projectId).count() == 0:
            response['errcode'] = 1
            response['message'] = "project not exist"
            response['data'] = None
            return JsonResponse(response)

        if User.objects.filter(id=request.user.id, status=User.ADMIN).count() == 0:
            response['errcode'] = 3
            response['message'] = "user not admin"
            response['data'] = request.user.id
            return JsonResponse(response)

        i = Project.objects.get(id=projectId)
        ans = {
            "projectId": i.id,
            "projectName": i.name,
            "projectIntro": i.outline,
            "state": i.status,
            "deadline": str(i.create_time.year) + "-" + str(i.create_time.month) + "-" + str(
                i.create_time.day),
            "managerId": i.manager_id.id,
            "managerName": i.manager_id.name,
            "access":i.access
        }

        response['errcode'] = 0
        response['data'] = ans
        response['message'] = "success"
        return JsonResponse(response)
