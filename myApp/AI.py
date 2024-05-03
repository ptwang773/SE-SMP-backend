import subprocess

import openai
import os
from django.http import JsonResponse
from django.views import View
import json
import datetime

from myApp.models import *
from myApp.userdevelop import genResponseStateInfo, isUserInProject, isProjectExists, is_independent_git_repository, \
    getSemaphore, releaseSemaphore, genUnexpectedlyErrorInfo

# from google.cloud import language_v1
# import git

# openai.organization = "org-fBoqj45hvJisAEGMR5cvPnDS"
openai.api_key = "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"

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


class CreateLabel(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        task = kwargs.get("")
        client = language_v1.LanguageServiceClient()
        document = {"content": task, "type_": language_v1.Document.Type.PLAIN_TEXT}
        data = client.analyze_sentiment(request={'document': document})
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = data
        return JsonResponse(response)


class CreateCommitMessage(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        sha = kwargs.get("sha")
        repo_path = '/path/to/your/repository'
        repo = git.Repo(repo_path)
        commit = repo.commit(sha)
        parent_commit = commit.parents[0] if commit.parents else None
        diff = commit.diff(parent_commit) if parent_commit else commit.diff()
        data = []
        for file_diff in diff:
            data.append("File:" + file_diff.a_path)
            data.append("Diff:")
            data.append(file_diff.diff)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = data
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
            subprocess.run(['git', 'credential-cache', 'exit'], cwd=localPath, check=True)
            subprocess.run(["git", "checkout", branch], cwd=localPath, check=True)
            subprocess.run(['git', 'pull', f'{branch}'], cwd=localPath)
            for file in files:
                path = os.path.join(localPath, file.get('path'))
                print(path)
                content = file.get('content')
                print("$$$$$$$$$$ modify file ", path)
                try:
                    with open(path, 'w') as f:
                        f.write(content)
                except Exception as e:
                    print(f"Failed to overwrite file {path}: {e}")
                subprocess.run(["git", "add", path], cwd=localPath, check=True)

            diff = subprocess.run(["git", "diff"], cwd=localPath, stderr=subprocess.PIPE,
                                  text=True, check=True)

            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=localPath, check=True)
            subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
            subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
            releaseSemaphore(repoId)
        except Exception as e:
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo.local_path, check=True)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))

        model = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "请针对以下git diff内容,为此次commit生成一些合适的message," +
                                            diff.stderr + ", speak English"},
            ]
        )

        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = model["choices"][0]["message"]["content"]
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
