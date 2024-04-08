import struct

from django.http import JsonResponse, HttpResponse
from django.core import serializers
from django.views import View
from myApp.models import *
from djangoProject.settings import DBG, USER_REPOS_DIR, BASE_DIR
import json
import os
import shutil
import sys
import subprocess
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
    userProject = UserProject.objects.get(user_id=userId,project_id=projectId)
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
    try:
      userProjectRepos = UserProjectRepo.objects.filter(project_id=projectId)
      for userProjectRepo in userProjectRepos:
        repoId = userProjectRepo.repo_id.id
        repo = Repo.objects.get(id=repoId)
        
        os.system("gh repo view " + repo.remote_path + " | grep description > " + os.path.join(USER_REPOS_DIR, descLogName))
        desc = open(os.path.join(USER_REPOS_DIR, descLogName), "r").readlines()[0]
        desc = desc.split(":", 2)[1].strip()
        os.system("rm -f " + os.path.join(USER_REPOS_DIR, descLogName))
        if desc.isspace():
          desc = None
        response["data"].append({"repoId" : repoId, 
                                "repoRemotePath" : repo.remote_path,
                                "name" : repo.name,
                                "repoIntroduction" : desc})
    except Exception as e:
      return JsonResponse(genUnexpectedlyErrorInfo(response, e))
    
    return JsonResponse(response)

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
      if userProject == None:
        return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
      # check if repo exists
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
        repoName = repoRemotePath.split("/")[-1]
        localPath = os.path.join(USER_REPOS_DIR, repoName)
        DBG("repoName=" + repoName, " localPath=" + localPath)
        if localHasRepo == False:
          # if dir not exists, then clone
          if not os.path.exists(localPath):
            r = os.system("gh repo clone " + repoRemotePath + " " + localPath)
            if r != 0:
              return JsonResponse(genResponseStateInfo(response, 5, "clone repo fail"))
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
    if userProject == None:
      return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
    
    if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
      return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
    
    data = []
    try:
      log = str(getCounter()) + "_getRepoBranches.log"
      commitLog = str(getCounter()) + "_commitInfo.log"
      remotePath = Repo.objects.get(id=repoId).remote_path
      os.system("gh api -H \"Accept: application/vnd.github+json\" -H \
                \"X-GitHub-Api-Version: 2022-11-28\" /repos/" + remotePath + "/branches > " + os.path.join(USER_REPOS_DIR, log))
      ghInfo = json.load(open(os.path.join(USER_REPOS_DIR, log), encoding="utf-8"))
      for it in ghInfo:
        sha = it["commit"]["sha"]
        cmd = "gh api /repos/" + remotePath + "/commits/" + sha + " > " + os.path.join(USER_REPOS_DIR, commitLog)
        os.system(cmd)
        commitInfo = json.load(open(os.path.join(USER_REPOS_DIR, commitLog), encoding="utf-8"))
        data.append({"branchName" : it["name"],
                      "lastCommit" : {
                        "sha" : sha,
                        "authorName" : commitInfo["commit"]["author"]["name"],
                        "authorEmail" : commitInfo["commit"]["author"]["email"],
                        "commitDate" : commitInfo["commit"]["author"]["date"],
                        "commitMessage" : commitInfo["commit"]["message"]
                      }
                      })
      response["data"] = data
      # os.system("rm -f " + os.path.join(USER_REPOS_DIR, log))
      # os.system("rm -f " + os.path.join(USER_REPOS_DIR, commitLog))
    except Exception as e:
      return genUnexpectedlyErrorInfo(response, e)
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
    if userProject == None:
      return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
    
    if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
      return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
    
    data = []
    try:
      log = str(getCounter()) + "_getCommitHistory.log"
      localPath = Repo.objects.get(id=repoId).local_path
      getSemaphore(repoId)
      os.system("cd " + localPath + " && git checkout " + branchName + " && git pull")
      cmd = "cd " + localPath + " && bash " + os.path.join(BASE_DIR, "myApp/get_commits.sh") + " > " + os.path.join(USER_REPOS_DIR, log)
      os.system(cmd)
      releaseSemaphore(repoId)
      try:
        ghInfo = json5.load(open(os.path.join(USER_REPOS_DIR, log), encoding="utf-8"))
      except Exception as e:
        DBG("in GetCommitHistory has excp : " + str(e))
      response["data"] = ghInfo
      os.system("rm -f " + os.path.join(USER_REPOS_DIR, log))
    except Exception as e:
      return genUnexpectedlyErrorInfo(response, e)
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
    if userProject == None:
      return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
    
    if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
      return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
    
    data = []
    try:
      log = "getIssueList.log"
      remotePath = Repo.objects.get(id=repoId).remote_path
      os.system("gh api -H \"Accept: application/vnd.github+json\" -H \
                \"X-GitHub-Api-Version: 2022-11-28\" /repos/" + remotePath + "/issues?state=all > " + os.path.join(USER_REPOS_DIR, log))
      ghInfo = json.load(open(os.path.join(USER_REPOS_DIR, log), encoding="utf-8"))
      for it in ghInfo:
        data.append({"issueId" : it["number"],
                    "issuer" : it["user"]["login"],
                    "issueTitle" : it["title"],
                    "issueTime" : it["updated_at"],
                    "isOpen" : it["state"] == "open",
                    "ghLink" : it["html_url"]})
      response["data"] = data
    except Exception as e:
      return genUnexpectedlyErrorInfo(response, e)
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
    if userProject == None:
      return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
    
    if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
      return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
    
    data = []
    try:
      log = "getPrList.log"
      remotePath = Repo.objects.get(id=repoId).remote_path
      os.system("gh api  /repos/" + remotePath + "/pulls?state=all > " + os.path.join(USER_REPOS_DIR, log))
      ghInfo = json.load(open(os.path.join(USER_REPOS_DIR, log), encoding="utf-8"))
      for it in ghInfo:
        data.append({"prId" : it["number"],
                    "prIssuer" : it["user"]["login"],
                    "prTitle" : it["title"],
                    "prTime" : it["updated_at"],
                    "isOpen" : it["state"] == "open",
                    "ghLink" : it["html_url"],
                    "fromBranchName" : it["head"]["ref"],
                    "toBranchName" : it["base"]["ref"]})
      response["data"] = data
    except Exception as e:
      return genUnexpectedlyErrorInfo(response, e)
    return JsonResponse(response)
  
  
def _getFileTree(dirPath):
  if os.path.isfile(dirPath):
    return {"name" : os.path.basename(dirPath)}
  children = []
  fs = os.listdir(dirPath)
  for f in fs:
    if f == ".git":
      continue
    children.append(_getFileTree(os.path.join(dirPath, f)))
  return {"name" : os.path.basename(dirPath), "children" : children}
    

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
    if userProject == None:
      return JsonResponse(genResponseStateInfo(response, 2, "user not in project"))
    
    if not UserProjectRepo.objects.filter(project_id=projectId, repo_id=repoId).exists():
      return JsonResponse(genResponseStateInfo(response, 3, "no such repo in project"))
    
    data = []
    try:
      localPath = Repo.objects.get(id=repoId).local_path
      getSemaphore(repoId)
      os.system("cd " + localPath + " && git checkout " + branch + " && git pull")
      r = _getFileTree(localPath)
      for item in r["children"]:
        data.append(item)
      response["data"] = data
      releaseSemaphore(repoId)
    except Exception as e:
      return genUnexpectedlyErrorInfo(response, e)
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
    genResponseStateInfo(response, 0, "get file tree ok")
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
    
    data = ""
    try:
      localPath = Repo.objects.get(id=repoId).local_path
      getSemaphore(repoId)
      os.system("cd " + localPath + " && git checkout " + branch + " && git pull")
      filePath = localPath + path#os.path.join(localPath, path)
      DBG(filePath)
      data = "警告：这是一个二进制文件，请登录 github 查看"
      try:
        data = open(filePath).read()
      except Exception as e:
        pass
      response["data"] = data
      releaseSemaphore(repoId)
    except Exception as e:
      return genUnexpectedlyErrorInfo(response, e)
    return JsonResponse(response)