import subprocess

import openai
from openai import OpenAI
import os
from django.http import JsonResponse
from django.views import View
import json
import datetime

from myApp.models import *
from myApp.userdevelop import genResponseStateInfo, isUserInProject, isProjectExists, is_independent_git_repository, \
    getSemaphore, releaseSemaphore, genUnexpectedlyErrorInfo, validate_token

# openai.organization = "org-fBoqj45hvJisAEGMR5cvPnDS"
api_key = "sk-proj-YjxEM9CWA8GhasSyqtoGT3BlbkFJ1kL8VTIIZ5GxZCBWH3Tu"

text = """class getEmail(View):
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
        return JsonResponse(response)"""


# model = openai.ChatCompletion.create(
#     model="gpt-3.5-turbo",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "请针对以下代码给我生成单元测试代码," + text+", speak English"},
#     ]
# )
# print(model)

class UnitTest(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        text = kwargs.get("code")
        model = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "请针对以下代码给我生成单元测试代码," + text + ", speak English"},
            ]
        )

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = model["choices"][0]["message"]["content"]
        return JsonResponse(response)


class CodeReview(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        text = kwargs.get("code")
        model = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "请针对以下代码进行代码分析," + text + ", speak English"},
            ]
        )

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = model["choices"][0]["message"]["content"]
        return JsonResponse(response)


class GenerateCommitMessage(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        branch = kwargs.get('branch')
        files = kwargs.get('files')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)

        user = User.objects.get(id=userId)
        token = user.token
        if repo == None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        try:
            localPath = repo.local_path
            remotePath = repo.remote_path
            print(localPath)
            print("is git :", is_independent_git_repository(localPath))
            if not is_independent_git_repository(localPath):
                return JsonResponse(genResponseStateInfo(response, 999, " not git dir"))
            getSemaphore(repoId)
            if validate_token(token):
                subprocess.run(['git', 'credential-cache', 'exit'], cwd=localPath, check=True)
                subprocess.run(["git", "checkout", branch], cwd=localPath, check=True)
                subprocess.run(["git", "remote", "add", "tmp", f"https://{token}@github.com/{remotePath}.git"],
                               cwd=localPath)
                subprocess.run(['git', 'pull', f'{branch}'], cwd=localPath)
                for file in files:
                    path = os.path.join(localPath, file.get('path'))
                    content = file.get('content')
                    print("$$$$$$$$$$ modify file ", path,content)
                    try:
                        with open(path, 'w') as f:
                            f.write(content)
                    except Exception as e:
                        print(f"Failed to overwrite file {path}: {e}")
                diff = subprocess.run(["git", "diff"], cwd=localPath, capture_output=True,
                                      text=True, check=True)
                print("diff is :",diff.stdout)
                if diff.stdout is None:
                    return JsonResponse(genResponseStateInfo(response,7,"you have not modify file"))
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=localPath, check=True)
                subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                releaseSemaphore(repoId)
            else:
                return JsonResponse(genResponseStateInfo(response, 6, "wrong token with this user"))
        except Exception as e:
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo.local_path, check=True)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))

        client = OpenAI(
            # This is the default and can be omitted
            api_key=api_key,
        )
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "请针对以下git diff内容,为此次commit生成一些合适的message," +
                                            diff.stdout + ", speak English"},
            ],
            model="gpt-3.5-turbo",
        )
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = chat_completion["choices"][0]["message"]["content"]
        return JsonResponse(response)


class GenerateLabel(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        taskId = kwargs.get('taskId')
        if not Task.objects.filter(taskId=taskId).exists():
            return JsonResponse(genResponseStateInfo(response, 1, "task not exists"))
        task = Task.objects.get(id=taskId)
        model = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user",
                 "content": "请根据以下描述,从下列标签中选择若干个合适的作为总结，描述为：" + task.outline +
                            "\n可以选择的标签为：bug,documentation,duplicate,enhancement,good first issue,help wanted,"
                            "invalid,question,wontifx " +
                            ", speak English"},
            ]
        )

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = model["choices"][0]["message"]["content"]
        return JsonResponse(response)
