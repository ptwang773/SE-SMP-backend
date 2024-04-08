from django.db import models
import datetime


class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    create_time = models.DateTimeField(auto_now_add=True)
    last_login_time = models.DateTimeField()
    NORMAL = 'A'
    ILLEGAL = 'B'
    ADMIN = 'C'
    STATUS_LIST = (
        (NORMAL, 'NORMAL'),
        (ILLEGAL, 'ILLEGAL'),
        (ADMIN, 'ADMIN'),
    )
    RED = 'A'
    ORANGE = 'B'
    GREEN = 'C'
    BLUE = 'D'
    PURPLE = 'E'
    COLOR_LIST = (
        (RED, 'RED'),
        (ORANGE, 'ORG'),
        (GREEN, 'GREEN'),
        (BLUE, 'BLUE'),
        (PURPLE, 'PUR')
    )
    color  = models.CharField(max_length=10, choices=COLOR_LIST)
    status = models.CharField(max_length=2, choices=STATUS_LIST)


class Project(models.Model):
    id = models.AutoField(primary_key=True)
    create_time = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(default=0)
    COMPLETED = 'A'
    INPROGRESS = 'B'
    NOTSTART = 'C'
    ILLEGAL = 'D'
    NORMAL = 'A'
    DISABLE = 'B'
    STATUS_LIST = (
        (COMPLETED, 'COMPLETED'),
        (INPROGRESS, 'INPROGRESS'),
        (NOTSTART, 'NOTSTART'),
        (ILLEGAL, 'ILLEGAL'),
    )

    ACCESS_LIST = (
        (NORMAL, 'NORMAL'),
        (DISABLE, 'DISABLE'),
    )
    status = models.CharField(max_length=2, choices=STATUS_LIST)
    access = models.CharField(max_length=2, choices=ACCESS_LIST, default=NORMAL)
    name = models.CharField(max_length=255)
    outline = models.TextField()
    manager_id = models.ForeignKey(User, on_delete=models.CASCADE)


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    create_time = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(default="2050-12-31")
    complete_time = models.DateTimeField(default="2050-12-31")
    deadline = models.DateTimeField()
    outline = models.TextField()
    COMPLETED = 'A'
    INPROGRESS = 'B'
    NOTSTART = 'C'
    STATUS_LIST = (
        (COMPLETED, 'COMPLETED'),
        (INPROGRESS, 'INPROGRESS'),
        (NOTSTART, 'NOTSTART'),
    )
    status = models.CharField(max_length=2, choices=STATUS_LIST)
    contribute_level = models.IntegerField(default=0)
    parent_id = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)


class Group(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    outline = models.TextField()
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    PRIVATE = 'PRI'
    PUBLIC = 'PUB'
    TYPE_LIST = (
    (PRIVATE, 'PRIVATE'),
    (PUBLIC, 'PUBLIC')
    )
    type          = models.CharField(max_length=5, choices=TYPE_LIST)


class Notice(models.Model):
    id = models.AutoField(primary_key=True)
    belongingTask = models.ForeignKey(Task, on_delete=models.CASCADE)
    deadline = models.DateTimeField()
    content = models.TextField()


class MyFile(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)


class Message(models.Model):
    id = models.AutoField(primary_key=True)
    TEXT = 'A'
    PIC = 'B'
    FILE = 'C'
    TYPE_LIST = (
        (TEXT, 'TEXT'),
        (PIC, 'PIC'),
        (FILE, 'FILE'),
    )
    CHECKED, UNCHECKED = 'C', 'UC'
    STATUS_LIST = (
        (CHECKED, 'CHECKED'),
        (UNCHECKED, 'UNCHECKED'),
    )
    status = models.CharField(max_length=2, choices=STATUS_LIST)
    type = models.CharField(max_length=2, choices=TYPE_LIST)
    content = models.CharField(max_length=255)  # TODO use FILE
    group_id = models.ForeignKey(Group, on_delete=models.CASCADE)
    send_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receive_user')
    receive_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='send_user')
    time = models.DateTimeField(auto_now_add=True)


class Document(models.Model):
    id            = models.AutoField(primary_key=True)
    name          = models.CharField(max_length=255)
    outline       = models.TextField()
    content       = models.TextField()
    time          = models.DateTimeField(auto_now_add=True)
    project_id    = models.ForeignKey(Project, on_delete=models.CASCADE)
    user_id       = models.ForeignKey(User, on_delete=models.CASCADE)
  
class UserCollectDoc(models.Model):
  id            = models.AutoField(primary_key=True)
  user_id       = models.ForeignKey(User, on_delete=models.CASCADE)
  doc_id        = models.ForeignKey(Document, on_delete=models.CASCADE)
  
class UserAccessDoc(models.Model):
  id            = models.AutoField(primary_key=True)
  user_id       = models.ForeignKey(User, on_delete=models.CASCADE)
  doc_id        = models.ForeignKey(Document, on_delete=models.CASCADE)
  
class UserDocLock(models.Model):
  doc_id        = models.ForeignKey(Document, on_delete=models.CASCADE, unique=True)
  user_id       = models.ForeignKey(User, on_delete=models.CASCADE)

class Post(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    content = models.TextField()
    post_time = models.TimeField(auto_now_add=True)
    PROJ_ALL = 'PROJ_ALL'
    PROJ_ONE = 'PROJ_ONE'
    SYS_PROJ = 'SYS_PROJ'
    SYS_ALL = 'SYS_ALL'
    TYPE_LIST = (
        (PROJ_ALL, 'PROJ_ALL'),
        (PROJ_ONE, 'PROJ_ONE'),
        (SYS_PROJ, 'SYS_PROJ'),
        (SYS_ALL, 'SYS_ALL'),
    )
    post_type = models.CharField(max_length=10, choices=TYPE_LIST)
    receiver_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_id')
    is_received = models.BooleanField()
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='receiver_id')
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)


class Repo(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    local_path = models.CharField(max_length=255)  # TODO
    remote_path = models.CharField(max_length=255)


class Progress(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    COMMIT = 'A'
    ISSUE = 'B'
    PR = 'C'
    TYPE_LIST = (
        (COMMIT, 'COMMIT'),
        (ISSUE, 'ISSUE'),
        (PR, 'PR'),
    )
    type = models.CharField(max_length=2, choices=TYPE_LIST)
    remote_path = models.CharField(max_length=255)
    repo_id = models.ForeignKey(Repo, on_delete=models.CASCADE)


class UserProject(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    NORMAL = 'A'
    ADMIN = 'B'
    DEVELOPER = "C"
    ROLE_LIST = (
        (NORMAL, 'NORMAL'),
        (ADMIN, 'ADMIN'),
        (DEVELOPER, 'DEVELOPER'),
    )
    role = models.CharField(max_length=3, choices=ROLE_LIST)


class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    NORMAL = 'A'
    ADMIN = 'B'
    ROLE_LIST = (
        (NORMAL, 'NORMAL'),
        (ADMIN, 'ADMIN'),
    )
    role = models.CharField(max_length=2, choices=ROLE_LIST)


class UserTask(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE)


class UserDocument(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    document_id = models.ForeignKey(Document, on_delete=models.CASCADE)


class UserProjectRepo(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    project_id = models.ForeignKey(Project, on_delete=models.CASCADE)
    repo_id = models.ForeignKey(Repo, on_delete=models.CASCADE)


class ProgressTask(models.Model):
    repo_id = models.ForeignKey(Repo, on_delete=models.CASCADE)
    progress_id = models.ForeignKey(Progress, on_delete=models.CASCADE)

# TODO : add enum check in function
