import mimetypes
import struct
import datetime
import subprocess
import requests
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core import serializers
from django.views import View
from myApp.models import *
from djangoProject.settings import DBG, USER_REPOS_DIR, BASE_DIR
import json
import os
import shutil
import sys
import json5

repo_semaphore = {}


def getSemaphore(repoId):
    repoId = str(repoId)
    if not repo_semaphore.__contains__(repoId):
        repo_semaphore[repoId] = True
        return
    while repo_semaphore[repoId] == True:
        continue
    repo_semaphore[repoId] = True
    return


def releaseSemaphore(repoId):
    repo_semaphore[repoId] = False
    return


MERET = 0


def getCounter():
    global MERET
    MERET = MERET + 1
    return MERET - 1


def isProjectExists(projectId):
    try:
        project = Project.objects.get(id=projectId)
        return project
    except Exception as e:
        return None


def isUserInProject(userId, projectId):
    try:
        userProject = UserProject.objects.get(user_id=userId, project_id=projectId)
        return userProject
    except Exception as e:
        return None


def genUnexpectedlyErrorInfo(response, e):
    response["errcode"] = -1
    response['message'] = "unexpectedly error : " + str(e)
    return response


def genResponseStateInfo(response, errcode, message):
    response["errcode"] = errcode
    response['message'] = message
    return response


def checkCMDError(err, errcode, response):
    if "Failed" in err or "422" in err or "fatal" in err or "403" in err or "rejected" in err:
        print("err is :", err)
        response["message"] = "error at gh api :" + err
        response["errcode"] = errcode
        return True, response
    else:
        return False, response


class GetProjectName(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get project name ok")
        response["data"] = {}
        response["data"]["name"] = ""
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        response["data"]["name"] = project.name
        return JsonResponse(response)


class GetBindRepos(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get bind repos ok")
        response["data"] = []
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        descLogName = str(getCounter()) + "_getRepoDesc.log"
        print("*********", descLogName)
        try:
            userProjectRepos = UserProjectRepo.objects.filter(project_id=projectId)
            for userProjectRepo in userProjectRepos:
                repoId = userProjectRepo.repo_id.id
                repo = Repo.objects.get(id=repoId)

                os.system("gh repo view " + repo.remote_path + " | grep description > " + os.path.join(USER_REPOS_DIR,
                                                                                                       descLogName))
                desc = open(os.path.join(USER_REPOS_DIR, descLogName), "r").readlines()[0]
                desc = desc.split(":", 2)[1].strip()
                os.system("rm -f " + os.path.join(USER_REPOS_DIR, descLogName))
                if desc.isspace():
                    desc = None
                response["data"].append({"repoId": repoId,
                                         "repoRemotePath": repo.remote_path,
                                         "name": repo.name,
                                         "repoIntroduction": desc})
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))

        return JsonResponse(response)


class GetRepoAllFiles(View):
    def post(self, request):
        # 检查权限
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get repo all files ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        dirPath = str(kwargs.get('dirPath'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(pk=repoId)
        owner = str.split(repo.remote_path, "/")[0]
        repo = str.split(repo.remote_path, "/")[1]
        print(owner, repo)
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{dirPath}"
        resp = requests.get(url)
        data = []
        if resp.status_code == 200:
            files = resp.json()
            for file in files:
                data.append({"name": file['name'], "type": file['type']})
            response["data"] = {"files": data}
            return JsonResponse(response)
        else:
            return JsonResponse(genResponseStateInfo(response, 4, "get repo all files fail, maybe path is wrong"))


class GetRepoFile(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get repo all files ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        filePath = str(kwargs.get('filePath'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(pk=repoId)
        file_path = repo.local_path + "/" + filePath
        try:
            if not os.path.isfile(file_path):
                return JsonResponse(genResponseStateInfo(response, 1, "file does not exists"))
            with open(file_path, 'r') as file:
                file_content = file.read()
            content_type, _ = mimetypes.guess_type(file_path)
            return FileResponse(file_content, content_type=content_type)
        except FileNotFoundError:
            return JsonResponse(genResponseStateInfo(response, 1, "file does not exists"))


class UserBindRepo(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "bind ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoRemotePath = kwargs.get('repoRemotePath')
        DBG("userId=" + userId + " projectId=" + projectId + " repoRemotePath=" + repoRemotePath)
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        user = User.objects.get(id=userId)
        token = user.token
        # check if repo exists
        if token is None or not validate_token(token):
            return JsonResponse(genResponseStateInfo(response, 6, "wrong token with this user"))
        try:
            localHasRepo = False
            s = Repo.objects.filter(remote_path=repoRemotePath)
            if len(s) != 0:
                localHasRepo = True
                repoId = s[0].id
                userProjectRepo = UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId)
                if len(userProjectRepo) != 0:
                    return JsonResponse(genResponseStateInfo(response, 4, "duplicate repo"))
            # clone & repo
            print(repoRemotePath)
            repoName = repoRemotePath.split("/")[-1]
            localPath = os.path.join(USER_REPOS_DIR, repoName)
            DBG("repoName=" + repoName, " localPath=" + localPath)
            if localHasRepo == False:
                # if dir not exists, then clone
                if not os.path.exists(localPath):
                    os.makedirs(localPath)
                    subprocess.run(['git', 'credential-cache', 'exit'], cwd=localPath)
                    subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                    subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                    print(f"https://{token}@github.com/{repoRemotePath}.git")
                    result = subprocess.run(["git", "clone", f"https://{token}@github.com/{repoRemotePath}.git",
                                             f"{localPath}"], cwd=localPath, stderr=subprocess.PIPE, text=True)
                    print("out is ", result.stdout)
                    print("err is ", result.stderr)
                    if "fatal" in result.stderr or "403" in result.stderr or "rejected" in result.stderr:
                        response["message"] = result.stderr
                        return JsonResponse(genResponseStateInfo(response, 5, "clone failed"))
            # insert Repo
            repo = None
            s = Repo.objects.filter(remote_path=repoRemotePath)
            if len(s) != 0:
                repo = s[0]
            else:
                repoEntry = Repo(name=repoName, local_path=localPath, remote_path=repoRemotePath)
                repoEntry.save()
                # insert UserProjectRepo
                repo = Repo.objects.get(name=repoName, local_path=localPath, remote_path=repoRemotePath)
            user = User.objects.get(id=userId)
            project = Project.objects.get(id=projectId)
            userProjectRepoEntry = UserProjectRepo(user_id=user, project_id=project, repo_id=repo)
            userProjectRepoEntry.save()

            subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
            subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class UserUnbindRepo(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "unbind ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(user_id=userId, project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project that bind by this user"))

        try:
            userProjectRepo = UserProjectRepo.objects.get(user_id=userId, project_id=projectId, repo_id=repoId)
            userProjectRepo.delete()
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))

        return JsonResponse(response)


class GetRepoBranches(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get branches ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 4, "invalid token"))

        data = []
        try:
            remotePath = Repo.objects.get(id=repoId).remote_path
            command = [
                "gh", "api",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "-H", f"Authorization: token {token}",
                f"/repos/{remotePath}/branches",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print("err is :", result.stderr)
            flag, response = checkCMDError(result.stderr, 5, response)
            if flag:
                return JsonResponse(response)
            ghInfo = json.loads(result.stdout)
            for it in ghInfo:
                sha = it["commit"]["sha"]
                cmd = [
                    "gh", "api",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "-H", f"Authorization: token {token}",
                    f"/repos/{remotePath}/commits/{sha}",
                ]
                cmd_result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print("out is :", cmd_result.stdout)
                flag, response = checkCMDError(cmd_result.stderr, 6, response)
                if flag:
                    return JsonResponse(response)
                commitInfo = json.loads(cmd_result.stdout)
                data.append({"branchName": it["name"],
                             "lastCommit": {
                                 "sha": sha,
                                 "authorName": commitInfo["commit"]["author"]["name"],
                                 "authorEmail": commitInfo["commit"]["author"]["email"],
                                 "commitDate": commitInfo["commit"]["author"]["date"],
                                 "commitMessage": commitInfo["commit"]["message"]
                             }
                             })
            response["data"] = data
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class GetCommitHistory(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get commit history ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        branchName = kwargs.get('branchName')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))

        repo = Repo.objects.get(id=repoId)
        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 5, "invalid token"))

        data = []
        try:
            localPath = repo.local_path
            remotePath = repo.remote_path
            if not is_independent_git_repository(localPath):
                return JsonResponse(genResponseStateInfo(response, 4, "this is not git repository???"))
            getSemaphore(repoId)
            cmd = [
                "gh", "api",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "-H", f"Authorization: token {token}",
                f"/repos/{remotePath}/commits?sha={branchName}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            flag, response = checkCMDError(result.stderr, 5, response)
            if flag:
                print("err is ", result.stderr)
                return JsonResponse(response)
            releaseSemaphore(repoId)
            ghInfo = json.loads(result.stdout)
            for info in ghInfo:
                sha = info["sha"]
                if not Commit.objects.filter(sha=sha).exists():
                    tmp_commit = Commit.objects.create(repo_id=Repo.objects.get(id=repoId), sha=sha,
                                                       committer_name=info["commit"]["author"]["name"])
                else:
                    tmp_commit = Commit.objects.filter(sha=sha)[0]
                data.append({"commithash": sha, "author": info["commit"]['author']['name'],
                             "authorEmail": info['commit']['author']['email'],
                             "commitTime": info["commit"]["author"]["date"],
                             "commitMessage": info["commit"]["message"],
                             "status": tmp_commit.review_status}
                            )
                response["data"] = data
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class GetIssueList(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get issue list ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))

        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 4, "invalid token"))

        data = []
        try:
            remotePath = Repo.objects.get(id=repoId).remote_path
            cmd = [
                "gh", "api",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "-H", f"Authorization: token {token}",
                f"/repos/{remotePath}/issues?state=all",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            flag, response = checkCMDError(result.stderr, 5, response)
            if flag:
                print("err is :", result.stderr)
                return JsonResponse(response)
            ghInfo = json.loads(result.stdout)
            for it in ghInfo:
                data.append({"issueId": it["number"],
                             "issuer": it["user"]["login"],
                             "issueTitle": it["title"],
                             "issueTime": it["updated_at"],
                             "isOpen": it["state"] == "open",
                             "ghLink": it["html_url"]})
            response["data"] = data
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class GetPrList(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get pr list ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))

        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 4, "invalid token"))

        data = []
        try:
            remotePath = Repo.objects.get(id=repoId).remote_path
            cmd = [
                "gh", "api",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "-H", f"Authorization: token {token}",
                f"/repos/{remotePath}/pulls?state=all",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            flag, response = checkCMDError(result.stderr, 5, response)
            if flag:
                print("err is :", result.stderr)
                return JsonResponse(response)
            ghInfo = json.loads(result.stdout)
            for it in ghInfo:
                data.append({"prId": it["number"],
                             "prIssuer": it["user"]["login"],
                             "prTitle": it["title"],
                             "prTime": it["updated_at"],
                             "isOpen": it["state"] == "open",
                             "ghLink": it["html_url"],
                             "fromBranchName": it["head"]["ref"],
                             "toBranchName": it["base"]["ref"]})
            response["data"] = data
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


def _getFileTree(dirPath):
    if os.path.isfile(dirPath):
        return {"name": os.path.basename(dirPath)}
    children = []
    fs = os.listdir(dirPath)
    for f in fs:
        if f == ".git":
            continue
        children.append(_getFileTree(os.path.join(dirPath, f)))
    return {"name": os.path.basename(dirPath), "children": children}


class GetFileTree(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get file tree ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        branch = str(kwargs.get('branch'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)

        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 4, "invalid token"))

        data = []
        localPath = repo.local_path
        try:
            remotePath = repo.remote_path
            getSemaphore(repoId)
            subprocess.run(["git", "remote", "add", "tmp", f"https://{token}@github.com/{remotePath}.git"],
                           cwd=localPath, check=True)
            print(f"https://{token}@github.com/{remotePath}.git")
            subprocess.run(['git', 'pull', 'tmp', f'{branch}'], stderr=subprocess.PIPE, cwd=localPath,
                           text=True, check=True)
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath, check=True)
            cmd = ["git", "checkout", f"{branch}"]
            subprocess.run(cmd, cwd=localPath)
            r = _getFileTree(localPath)
            for item in r["children"]:
                data.append(item)
            response["data"] = data
            releaseSemaphore(repoId)
        except Exception as e:
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath, check=True)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class GetContent(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "get file ok")
        userId = str(kwargs.get('userId'))
        projectId = str(kwargs.get('projectId'))
        repoId = str(kwargs.get('repoId'))
        branch = str(kwargs.get('branch'))
        path = str(kwargs.get('path'))
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))

        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)

        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 4, "invalid token"))

        data = ""
        localPath = repo.local_path
        try:
            remotePath = repo.remote_path
            getSemaphore(repoId)
            subprocess.run(["git", "remote", "add", "tmp", f"https://{token}@github.com/{remotePath}.git"],
                           cwd=localPath, check=True)
            print(f"https://{token}@github.com/{remotePath}.git")
            subprocess.run(['git', 'pull', 'tmp', f'{branch}'], stderr=subprocess.PIPE, cwd=localPath,
                           text=True, check=True)
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath, check=True)
            cmd = ["git", "checkout", f"{branch}"]
            subprocess.run(cmd, cwd=localPath, check=True)
            filePath = localPath + path  # os.path.join(localPath, path)
            DBG(filePath)
            data = "警告：这是一个二进制文件，请登录 github 查看"
            try:
                data = open(filePath).read()
            except Exception as e:
                pass
            response["data"] = data
            releaseSemaphore(repoId)
        except Exception as e:
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath, check=True)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


def validate_token(token):
    headers = {'Authorization': 'token ' + token, 'Content-Type': 'application/json; charset=utf-8'}
    response = requests.get('https://api.github.com/user', headers=headers)
    print(token, response.status_code)
    if response.status_code == 200:
        return True
    return False


def is_independent_git_repository(path):
    print(os.path.join(path, '.git'))
    if os.path.exists(os.path.join(path, '.git')):
        return True
    else:
        return False


class GitCommit(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "git commit ok")

        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')

        files = kwargs.get('files')
        branch = kwargs.get('branch')
        message = kwargs.get('message')

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
        localPath = repo.local_path
        try:
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
                subprocess.run(['git', 'pull', 'tmp', f'{branch}'], cwd=localPath)
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
                subprocess.run(["git", "commit", "-m", message], cwd=localPath, check=True)

                result = subprocess.run(["git", "push", "tmp", branch], cwd=localPath, stderr=subprocess.PIPE,
                                        text=True, check=True)
                print("out is ", result.stdout)
                print("err is ", result.stderr)
                if "fatal" in result.stderr or "403" in result.stderr or "rejected" in result.stderr:
                    subprocess.run(["git", "reset", "--hard", "HEAD^1"], cwd=localPath, check=True)
                    response["message"] = result.stderr
                    errcode = 7
                else:
                    result = subprocess.run(["git", "log", "-1", "--pretty=format:%H"], cwd=localPath,
                                            capture_output=True, text=True, check=True)
                    current_commit_sha = result.stdout.strip()
                    print(current_commit_sha)
                    Commit.objects.create(repo_id=repo, sha=current_commit_sha, committer_name=user.name,
                                          committer_id=user,
                                          review_status=None)
                    # cooperate & file commit update
                    for file in files:
                        FileUserCommit.objects.create(user_id=user,
                                                      repo_id=repo,
                                                      branch=branch, file=file['path'], commit_sha=current_commit_sha)
                        # modify Cooperate
                        tmp = FileUserCommit.objects.filter(repo_id=repo, branch=branch, file=file['path']).exclude(
                            user_id=user)
                        if tmp.exists():
                            for item in tmp:
                                user2 = item.user_id
                                if not Cooperate.objects.filter(user1_id=user, user2_id=user2,
                                                                project_id=project).exists():
                                    Cooperate.objects.create(user1_id=user, user2_id=user2, project_id=project)
                                cooperate = Cooperate.objects.get(user1_id=user, user2_id=user2, project_id=project)
                                cooperate.relation += 1
                                cooperate.save()
                                if not Cooperate.objects.filter(user1_id=user2, user2_id=user,
                                                                project_id=project).exists():
                                    Cooperate.objects.create(user1_id=user2, user2_id=user, project_id=project)
                                cooperate = Cooperate.objects.get(user1_id=user2, user2_id=user, project_id=project)
                                cooperate.relation += 1
                                cooperate.save()
                    UserProjectActivity.objects.create(user_id=user, project_id=project,
                                                       option=UserProjectActivity.COMMIT_CODE)
                    errcode = 0
                subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                response['errcode'] = errcode
                releaseSemaphore(repoId)
            else:
                return JsonResponse(genResponseStateInfo(response, 6, "wrong token with this user"))
        except Exception as e:
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class GitPr(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        response = {}
        genResponseStateInfo(response, 0, "git pr ok")

        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        branch = kwargs.get('branch')
        title = kwargs.get('title')
        body = kwargs.get('body')
        base = kwargs.get('base')

        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None or not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo == None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        applicant = User.objects.get(id=userId)
        token = applicant.token
        try:
            localPath = Repo.objects.get(id=repoId).local_path
            remotePath = Repo.objects.get(id=repoId).remote_path
            getSemaphore(repoId)
            if token is not None or validate_token(token):
                subprocess.run(['git', 'credential-cache', 'exit'], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                log_path = os.path.join(USER_REPOS_DIR, str(getCounter()) + "_prOutput.log")

                command = [
                    "gh", "api",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "-H", f"Authorization: token {token}",
                    f"/repos/{remotePath}/pulls",
                    "-f", f"title={title}",
                    "-f", f"body={body}",
                    "-f", f"head={branch}",
                    "-f", f"base={base}"
                ]

                result = subprocess.run(command, cwd=localPath, capture_output=True, text=True)
                if "Failed" in result.stderr or "422" in result.stderr or "fatal" in result.stderr or "403" in result.stderr or "rejected" in result.stderr:
                    print(result.stdout)
                    print(result.stderr)
                    response["message"] = json.loads(result.stdout)["errors"][0]["message"]
                    response["errcode"] = 7
                    return JsonResponse(response)
                output = json.loads(result.stdout)
                print("------- pr number:", output["number"])
                Pr.objects.create(applicant_id=applicant, repo_id=repo, src_branch=branch, dst_branch=base,
                                  pr_number=output["number"], applicant_name=applicant.name, pr_status=Pr.OPEN)

                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                response['errcode'] = 0
                releaseSemaphore(repoId)
                os.system("rm -f " + log_path)
            else:
                return JsonResponse(genResponseStateInfo(response, 6, "wrong token with this user"))
        except Exception as e:
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class GitBranchCommit(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "git commit ok")

        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')

        files = kwargs.get('files')
        branch = kwargs.get('branch')
        message = kwargs.get('message')

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
        localPath = repo.local_path
        try:
            remotePath = repo.remote_path
            getSemaphore(repoId)
            if token is None or not validate_token(token):
                subprocess.run(['git', 'credential-cache', 'exit'], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                result = subprocess.run(["git", "checkout", "-b", branch], cwd=localPath, stderr=subprocess.PIPE,
                                        text=True)
                if "fatal" in result.stderr or "403" in result.stderr or "rejected" in result.stderr:
                    response["message"] = result.stderr
                    response["errcode"] = 7
                    return JsonResponse(response)
                log_path = os.path.join(USER_REPOS_DIR, str(getCounter()) + "_commitOutput.log")
                print(log_path)
                subprocess.run(["git", "remote", "add", "tmp", f"https://{token}@github.com/{remotePath}.git"],
                               cwd=localPath)
                for file in files:
                    path = os.path.join(localPath, file.get('path'))
                    content = file.get('content')
                    try:
                        with open(path, 'w') as f:
                            f.write(content)
                    except Exception as e:
                        print(f"Failed to overwrite file {path}: {e}")
                    subprocess.run(["git", "add", path], cwd=localPath)
                subprocess.run(["git", "commit", "-m", message], cwd=localPath)

                result = subprocess.run(["git", "push", "tmp", branch], cwd=localPath, stderr=subprocess.PIPE,
                                        text=True)
                print("out is ", result.stdout)
                print("err is ", result.stderr)
                if "fatal" in result.stderr or "403" in result.stderr or "rejected" in result.stderr:
                    subprocess.run(["git", "branch", "-D", branch], cwd=localPath)
                    response["message"] = result.stderr
                    errcode = 7
                else:
                    result = subprocess.run(["git", "log", "-1", "--pretty=format:%H"], cwd=localPath,
                                            capture_output=True, text=True)
                    current_commit_sha = result.stdout.strip()
                    print(current_commit_sha)
                    Commit.objects.create(repo_id=repo, sha=current_commit_sha, committer_name=user.name,
                                          committer_id=user,
                                          review_status=None)
                    for file in files:
                        FileUserCommit.objects.create(user_id=user,
                                                      repo_id=repo,
                                                      branch=branch, file=file['path'],
                                                      commit_sha=current_commit_sha)
                        # modify Cooperate
                        tmp = FileUserCommit.objects.filter(repo_id=repo, branch=branch, file=file['path']).exclude(
                            user_id=user)
                        if tmp.exists():
                            for item in tmp:
                                user2 = item.user_id
                                if not Cooperate.objects.filter(user1_id=user, user2_id=user2,
                                                                project_id=project).exists():
                                    Cooperate.objects.create(user1_id=user, user2_id=user2, project_id=project)
                                cooperate = Cooperate.objects.get(user1_id=user, user2_id=user2, project_id=project)
                                cooperate.relation += 1
                                cooperate.save()
                                if not Cooperate.objects.filter(user1_id=user2, user2_id=user,
                                                                project_id=project).exists():
                                    Cooperate.objects.create(user1_id=user2, user2_id=user, project_id=project)
                                cooperate = Cooperate.objects.get(user1_id=user2, user2_id=user, project_id=project)
                                cooperate.relation += 1
                                cooperate.save()
                    UserProjectActivity.objects.create(user_id=user, project_id=project,
                                                       option=UserProjectActivity.COMMIT_CODE)
                    errcode = 0
                subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.name"], cwd=localPath)
                subprocess.run(["git", "config", "--unset-all", "user.email"], cwd=localPath)
                response['errcode'] = errcode
                releaseSemaphore(repoId)
                os.system("rm -f " + log_path)
            else:
                return JsonResponse(genResponseStateInfo(response, 6, "wrong token with this user"))
        except Exception as e:
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath)
            return JsonResponse(genUnexpectedlyErrorInfo(response, e))
        return JsonResponse(response)


class IsProjectReviewer(View):
    def post(self, request):
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "check reviewer ok")
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        response['flag'] = 0
        if not UserProject.objects.filter(project_id=projectId, user_id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 2, "user is not in Project"))
        tmp = UserProject.objects.get(project_id=projectId, user_id=userId)
        if tmp is None or tmp.role == UserProject.NORMAL:
            return JsonResponse(genResponseStateInfo(response, 1, "user is not reviewer"))
        else:
            response['flag'] = 1
            return JsonResponse(response)


def isProjectReviewer(userId, projectId):
    if not UserProject.objects.filter(project_id=projectId, user_id=userId).exists():
        return False
    tmp = UserProject.objects.get(project_id=projectId, user_id=userId)
    if tmp is None or tmp.role == UserProject.NORMAL:
        return False
    else:
        return True


def getCommitComment(commitId, projectId):
    comments = []
    commitComments = CommitComment.objects.filter(commit_id=commitId)
    for commit in commitComments:
        reviewer = User.objects.get(id=commit.reviewer_id_id)
        if UserProject.objects.filter(project_id=projectId, user_id=reviewer.id).exists():
            role = UserProject.objects.get(project_id=projectId, user_id=reviewer.id).role
        else:
            role = None
        comments.append({"commenterName": reviewer.name, "comment": commit.comment, "commenterId": reviewer.id,
                         "commenterRole": role})
    return comments


class GetCommitDetails(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "get commit ok")
        sha = kwargs.get('sha')
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        branch = kwargs.get('branch')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))
        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 6, "invalid token"))

        getSemaphore(repoId)
        owner = str.split(repo.remote_path, "/")[0]
        repo_name = str.split(repo.remote_path, "/")[1]
        command = [
            "gh", "api",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
            "-H", f"Authorization: token {token}",
            f"/repos/{owner}/{repo_name}/commits/{sha}"
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            remotePath = repo.remote_path
            localPath = repo.local_path
            subprocess.run(["git", "remote", "add", "tmp", f"https://{token}@github.com/{remotePath}.git"],
                           cwd=localPath, check=True)
            print(f"https://{token}@github.com/{remotePath}.git")
            subprocess.run(['git', 'pull', 'tmp', f'{branch}'], stderr=subprocess.PIPE, cwd=localPath,
                           text=True, check=True)
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath, check=True)
            output = result.stdout
            data = json.loads(output)
            commit = {}

            commit["sha"] = data["sha"]

            if not Commit.objects.filter(sha=sha).exists():
                tmp_commit = Commit.objects.create(repo_id=repo, sha=sha,
                                                   committer_name=data["commit"]["committer"]["name"])
            else:
                tmp_commit = Commit.objects.filter(sha=sha)[0]
            changes = []
            for file in data["files"]:
                prev = subprocess.run(['git', 'show', f'{sha}^:{file["filename"]}'], text=True,
                                      capture_output=True,
                                      cwd=localPath)
                if "fatal" in prev.stderr:
                    prev = None
                else:
                    prev = prev.stdout
                next = subprocess.run(['git', 'show', f'{sha}:{file["filename"]}'], text=True,
                                      capture_output=True,
                                      cwd=localPath, check=True)
                changes.append({"filename": file["filename"], "status": file["status"], "patch": file["patch"],
                                "prev_file": prev, "now_file": next.stdout})
            commit["files"] = changes
            commit["committer_name"] = tmp_commit.committer_name
            commit["comments"] = getCommitComment(tmp_commit.id, projectId)
            commit["status"] = tmp_commit.review_status
            commit["reviewerName"] = tmp_commit.reviewer_id.name if tmp_commit.reviewer_id is not None else None
            response["commit"] = commit
            releaseSemaphore(repoId)
            return JsonResponse(response)
        except subprocess.CalledProcessError as e:
            print("命令执行失败:", e)
            print("错误输出:", e.stderr)
            subprocess.run(["git", "remote", "rm", "tmp"], cwd=localPath, check=True)
            response["message"] = str(e)
            response["errcode"] = -1
            releaseSemaphore(repoId)
            return JsonResponse(response)


class ModifyCommitStatus(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "modify commit status ok")
        sha = kwargs.get('sha')
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        status = kwargs.get('reviewStatus')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))
        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 6, "invalid token"))

        if not isProjectReviewer(userId, projectId):
            return JsonResponse(genResponseStateInfo(response, 7, "permission denied"))
        if not Commit.objects.filter(sha=sha).exists():
            return JsonResponse(genResponseStateInfo(response, 10, "commit is not exists"))

        tmp_commit = Commit.objects.filter(sha=sha)[0]
        if tmp_commit.review_status is not None:
            return JsonResponse(genResponseStateInfo(response, 9, "can not approve/reject twice"))
        if status == 0 or status == 1:
            tmp_commit.review_status = Commit.Y if status == 1 else Commit.N
            tmp_commit.reviewer_id = User.objects.get(id=userId)
            tmp_commit.save()
        else:
            return JsonResponse(
                genResponseStateInfo(response, 8, "wrong review status, must approve/reject please"))
        return JsonResponse(response)


class CommentCommit(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "comment commit ok")
        sha = kwargs.get('sha')
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        comment = kwargs.get('comment')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))
        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 6, "invalid token"))

        if not isProjectReviewer(userId, projectId):
            return JsonResponse(genResponseStateInfo(response, 7, "permission denied"))

        if not Commit.objects.filter(sha=sha).exists():
            return JsonResponse(genResponseStateInfo(response, 8, "commit is not exists"))

        reviewer = User.objects.get(id=userId)
        tmp_commit = Commit.objects.filter(sha=sha)[0]
        CommitComment.objects.create(commit_id=tmp_commit, reviewer_id=reviewer, comment=comment)
        return JsonResponse(response)


class ShowCanAssociateTasks(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "show associate tasks ok")
        projectId = kwargs.get('projectId')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        tasks = Task.objects.filter(project_id=project)
        data = []
        for task in tasks:
            if task.status == Task.COMPLETED:
                continue
            data.append({"taskName": task.name, "taskId": task.id})
        response["data"] = data
        return JsonResponse(response)


class AssociatePrTask(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "associate pr with task ok")
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        prId = kwargs.get('prId')
        taskId = kwargs.get('taskId')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        user = User.objects.get(id=userId)
        if userProject is None or user is None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))

        if Pr.objects.filter(pr_number=prId, repo_id=repo).exists():
            pr = Pr.objects.get(pr_number=prId, repo_id=repo)
        else:
            return JsonResponse(genResponseStateInfo(response, 6, f"no sucn pr{prId} in repo{repoId}"))

        if pr.applicant_id != user and pr.applicant_id is not None:
            return JsonResponse(genResponseStateInfo(response, 9, "you can not associate"))

        if not Task.objects.filter(id=taskId, project_id=project).exists():
            return JsonResponse(genResponseStateInfo(response, 7, "no such task in project"))
        task = Task.objects.get(id=taskId)
        if task.status == Task.COMPLETED:
            return JsonResponse(genResponseStateInfo(response, 8, "task is completed"))
        Pr_Task.objects.create(pr_id=pr, task_id=task)

        return JsonResponse(response)


class ResolvePr(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "pr resolve ok")
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        prId = kwargs.get('prId')
        action = kwargs.get('action')
        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        user = User.objects.get(id=userId)
        if userProject is None or user is None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))
        token = user.token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 6, "invalid token"))
        if not isProjectReviewer(userId, projectId):
            return JsonResponse(genResponseStateInfo(response, 7, "Insufficient authority"))

        getSemaphore(repoId)
        owner = str.split(repo.remote_path, "/")[0]
        repo_name = str.split(repo.remote_path, "/")[1]

        try:
            if action == 0:
                command = [
                    "gh", "api",
                    "--method", "PATCH",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "-H", f"Authorization: token {token}",
                    f"/repos/{owner}/{repo_name}/pulls/{prId}",
                    "-f", "state=closed"
                ]
            else:
                command = [
                    "gh", "api",
                    "--method", "PUT",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "-H", f"Authorization: token {token}",
                    f"/repos/{owner}/{repo_name}/pulls/{prId}/merge"
                ]

            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print("out is ", result.stdout)
            print("err is ", result.stderr)
            if "conflict" in result.stderr:
                response["message"] = result.stderr
                errcode = 8
            elif "fatal" in result.stderr or "403" in result.stderr or "rejected" in result.stderr:
                response["message"] = result.stderr
                errcode = 9
            else:
                errcode = 0

            if Pr.objects.filter(pr_number=prId, repo_id=repo).exists():
                pr = Pr.objects.get(pr_number=prId, repo_id=repo)
                pr.status = Pr.MERGED if action == 1 else Pr.CLOSED
            else:
                command = [
                    "gh", "api",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "-H", f"Authorization: token {token}",
                    f"/repos/{owner}/{repo_name}/pulls/{prId}"
                ]
                output = subprocess.run(command, capture_output=True, text=True, check=True)
                output = json.loads(output.stdout)
                print("+++++++++++\n", output)
                pr = Pr.objects.create(repo_id=repo, src_branch=output["head"]["label"].split(':')[1],
                                       dst_branch=output["base"]["label"].split(':')[1],
                                       pr_number=output["number"], applicant_name=output["user"]["login"],
                                       pr_status=Pr.MERGED if action == 1 else Pr.CLOSED)
            pr.reviewer_id = user
            pr.save()

            if action == 1:
                pr_tasks = Pr_Task.objects.filter(pr_id=pr)
                tasks = [pr_task.task_id for pr_task in pr_tasks]
                for task in tasks:
                    if task.status == Task.COMPLETED:
                        continue
                    task.status = Task.COMPLETED
                    task.complete_time = datetime.datetime.now()
                    print(task.id, " is completed with pr")
                    task.save()
                    subtasks = Task.objects.filter(parent_id=task.id)
                    for i in subtasks:
                        if i.status == Task.COMPLETED:
                            continue
                        i.status = Task.COMPLETED
                        i.complete_time = datetime.datetime.now()
                        print(i.id, " is completed with pr")
                        i.save()
            UserProjectActivity.objects.create(user_id=user, project_id=project,
                                               option=UserProjectActivity.FINISH_TASK)
            response['errcode'] = errcode
            releaseSemaphore(repoId)
            return JsonResponse(response)
        except subprocess.CalledProcessError as e:
            print("命令执行失败:", e)
            print("错误输出:", e.stderr)
            response["message"] = e.stderr
            response["errcode"] = -1
            releaseSemaphore(repoId)
            return JsonResponse(response)


def getPrStatus(status, merged):
    if status == "closed" and merged:
        return Pr.MERGED
    elif status == "open":
        return Pr.OPEN
    elif status == "closed" and not merged:
        return Pr.CLOSED
    else:
        return Pr.DRAFT


def parsePrStatus(status):
    if status == 1:
        return "open"
    elif status == 2:
        return "closed"
    elif status == 3:
        return "merged"
    else:
        return "draft"


class GetPrDetails(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "get pr details ok")
        prId = kwargs.get('prId')
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')

        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))
        token = User.objects.get(id=userId).token
        if token is None or validate_token(token) == False:
            return JsonResponse(genResponseStateInfo(response, 6, "invalid token"))

        getSemaphore(repoId)
        owner = str.split(repo.remote_path, "/")[0]
        repo_name = str.split(repo.remote_path, "/")[1]
        command = [
            "gh", "api",
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
            "-H", f"Authorization: token {token}",
            f"/repos/{owner}/{repo_name}/pulls/{prId}"
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output = result.stdout
            jsonOutput = json.loads(output)
            if not Pr.objects.filter(pr_number=prId, repo_id=repo).exists():
                pr = Pr.objects.create(repo_id=repo, src_branch=jsonOutput["head"]["label"].split(':')[1],
                                       dst_branch=jsonOutput["base"]["label"].split(':')[1],
                                       pr_number=prId, applicant_name=jsonOutput["user"]["login"])
            else:
                pr = Pr.objects.get(repo_id=repo, pr_number=prId)
            pr.pr_status = getPrStatus(jsonOutput["state"], jsonOutput["merged"])
            pr.save()
            data = {
                "state": parsePrStatus(pr.pr_status),
                "title": jsonOutput["title"],
                "body": jsonOutput["body"],
                "merge_commit_sha": jsonOutput["merge_commit_sha"],
                "branch": jsonOutput["head"]["ref"],
                "base": jsonOutput["base"]["ref"],
                "commits": []
            }
            command = [
                "gh", "api",
                "-H", "Accept: application/vnd.github+json",
                "-H", "X-GitHub-Api-Version: 2022-11-28",
                "-H", f"Authorization: token {token}",
                f"/repos/{owner}/{repo_name}/pulls/{prId}/commits"
            ]
            res = subprocess.run(command, capture_output=True, text=True, check=True)
            out = json.loads(res.stdout)
            for commit in out:
                sha = commit["sha"]
                if Commit.objects.filter(sha=sha).exists():
                    commit_obj = Commit.objects.get(sha=sha)
                else:
                    commit_obj = Commit.objects.create(
                        repo_id=repo,
                        sha=sha,
                        committer_name=commit["commit"]["committer"]["name"]
                    )
                data["commits"].append({"commitId": commit_obj.pk,
                                        "sha": sha, "author": commit["commit"]["author"]["name"],
                                        "time": commit["commit"]["author"]["date"],
                                        "message": commit["commit"]["message"]})
            response["data"] = data
            releaseSemaphore(repoId)
            return JsonResponse(response)
        except subprocess.CalledProcessError as e:
            print("命令执行失败:", e)
            print("错误输出:", e.stderr)
            response["message"] = e.stderr
            response["errcode"] = -1
            releaseSemaphore(repoId)
            return JsonResponse(response)


class GetFileCommits(View):
    def post(self, request):
        DBG("---- in " + sys._getframe().f_code.co_name + " ----")
        response = {'message': "404 not success", "errcode": -1}
        try:
            kwargs: dict = json.loads(request.body)
        except Exception:
            return JsonResponse(response)
        genResponseStateInfo(response, 0, "get user commits for file ok")
        userId = kwargs.get('userId')
        projectId = kwargs.get('projectId')
        repoId = kwargs.get('repoId')
        file = kwargs.get('file')
        branch = kwargs.get('branch')

        project = isProjectExists(projectId)
        if project == None:
            return JsonResponse(genResponseStateInfo(response, 1, "project does not exists"))
        userProject = isUserInProject(userId, projectId)
        if userProject == None:
            return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
        if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
            return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
        repo = Repo.objects.get(id=repoId)
        if repo is None:
            return JsonResponse(genResponseStateInfo(response, 4, "no such repo"))
        if not User.objects.filter(id=userId).exists():
            return JsonResponse(genResponseStateInfo(response, 5, "user is not exist"))

        getSemaphore(repoId)
        fileUserCommits = FileUserCommit.objects.filter(repo_id=repoId, file=file, branch=branch)
        commits = {}
        for fuc in fileUserCommits:
            if not (fuc.user_id_id in commits):
                commits[fuc.user_id_id] = []
            commits[fuc.user_id_id].append(fuc.commit_sha)
            print(fuc.commit_sha)
        data = []
        for key in commits.keys():
            data.append({"userId": key, "commits": commits[key], "count": len(commits[key])})
        response["data"] = data
        releaseSemaphore(repoId)
        return JsonResponse(response)
