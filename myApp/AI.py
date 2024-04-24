import openai
import os
from django.http import JsonResponse
from django.views import View
import json
import datetime
from google.cloud import language_v1
import git

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
