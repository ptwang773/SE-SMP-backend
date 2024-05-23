import subprocess

import openai
import requests
from openai import OpenAI
import os
from django.http import JsonResponse
from django.views import View
import json
import datetime

from myApp.models import *
from myApp.userdevelop import genResponseStateInfo, isUserInProject, isProjectExists, is_independent_git_repository, \
    genUnexpectedlyErrorInfo, validate_token
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, SummarizationPipeline
import nltk
from nltk.tokenize import WordPunctTokenizer

pipeline = None


def load_codeTrans_model():
    global pipeline
    if pipeline is None:
        # model_path = "/home/ptwang/Code/SE-SMP-backend/myApp/codeTrans/base/"
        model_path = "/root/project/SE-SMP-backend/myApp/codeTrans/base/"
        print("model path:", model_path)
        pipeline = SummarizationPipeline(
            model=AutoModelForSeq2SeqLM.from_pretrained(model_path),
            tokenizer=AutoTokenizer.from_pretrained(model_path),
            device="cpu"
        )


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

def request_trash(messages):
    url = 'https://gtapi.xiaoerchaoren.com:8932/v1/chat/completions'

    headers = {

        'Content-Type': 'application/json',

        'Authorization': 'Bearer sk-i0ipf6VCzrMI2F1o0cD27a1f24654794A6C2A21e8d617978'  # 输入网站发给你的转发key

    }

    data = {

        "model": "gpt-3.5-turbo",

        "messages": messages,

        "stream": False

    }

    response = requests.post(url, json=data, headers=headers)

    return response.json()


def request_cloudflare(messages):
    ACCOUNT_TAG = "3cec0af6cdabce0f9fafcd413f9370b4"
    GATEWAY = "openai"
    url = f"https://gateway.ai.cloudflare.com/v1/{ACCOUNT_TAG}/{GATEWAY}/openai/chat/completions"
    # 请求头部
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 请求数据
    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages
    }

    # 发送POST请求
    response = requests.post(url, headers=headers, json=data)

    # 处理响应
    if response.status_code == 200:
        response_data = response.json()
        # 在这里处理响应数据
        print(response_data)
        return response.json()
    else:
        print(f"Error: {response.status_code}")


class UnitTest(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        text = kwargs.get("code")

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "请针对以下代码给我生成单元测试代码," + text + ", speak English"}]
        chat = request_trash(messages)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = chat["choices"][0]["message"]["content"]
        return JsonResponse(response)


class CodeReview(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)

        text = kwargs.get("code")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "请针对以下代码进行代码分析," + text + ", speak English"},
        ]
        chat = request_trash(messages)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = chat["choices"][0]["message"]["content"]
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
            if validate_token(token):
                subprocess.run(['git', 'credential-cache', 'exit'], cwd=localPath, check=True)
                subprocess.run(["git", "checkout", branch], cwd=localPath, check=True)
                # subprocess.run(["git", "remote", "add", "tmp", f"https://{token}@github.com/{remotePath}.git"],
                #                cwd=localPath)
                # subprocess.run(['git', 'pull', f'{branch}'], cwd=localPath)
                print(1111)
                for file in files:
                    path = os.path.join(localPath, file.get('path'))
                    print(2222)
                    content = file.get('content')
                    print("$$$$$$$$$$ modify file ", path, content)
                    try:
                        with open(path, 'w') as f:
                            f.write(content)
                    except Exception as e:
                        print(f"Failed to overwrite file {path}: {e}")
                diff = subprocess.run(["git", "diff"], cwd=localPath, capture_output=True,
                                      text=True, check=True)
                print("diff is :", diff.stdout)
                if diff.stdout is None:
                    return JsonResponse(genResponseStateInfo(response, 7, "you have not modify file"))
                subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=localPath, check=True)
                # subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
            else:
                return JsonResponse(genResponseStateInfo(response, 6, "wrong token with this user"))
        except Exception as e:
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo.local_path, check=True)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))

        # messages = [
        #     {"role": "system", "content": "You are a helpful assistant."},
        #     {"role": "user", "content": "请针对以下git diff内容,为此次commit生成一些合适的message," +
        #                                 diff.stdout + ", speak English"},
        # ]
        # chat = request_trash(messages)

        load_codeTrans_model()
        nltk.data.path.append("/root/project/SE-SMP-backend/myApp/codeTrans/tokenizers/")
        nltk.data.path.append("/home/ptwang/Code/SE-SMP-backend/myApp/codeTrans/tokenizers/")  # check here
        tokenized_list = WordPunctTokenizer().tokenize(diff.stdout)
        tokenized_code = ' '.join(tokenized_list)
        print("tokenized code: " + tokenized_code)
        # 进行摘要生成
        output = pipeline([tokenized_code])
        print(output[0]['summary_text'])

        response['errcode'] = 0
        response['message'] = "success"
        # response['data'] = chat["choices"][0]["message"]["content"]
        response['data'] = output[0]['summary_text']
        return JsonResponse(response)


class GenerateLabel(View):
    def post(self, request):
        response = {'errcode': 0, 'message': "404 not success"}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        outline = kwargs.get('outline')
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",
             "content": "请根据以下描述,从下列标签中选择若干个合适的作为总结，描述为：" + outline +
                        "\n可以选择的标签为：bug,documentation,duplicate,enhancement,good first issue,help wanted,"
                        "invalid,question,wontifx " +
                        ", speak English"},
        ]
        chat = request_trash(messages)
        response['errcode'] = 0
        response['message'] = "success"
        response['data'] = chat["choices"][0]["message"]["content"]
        return JsonResponse(response)
