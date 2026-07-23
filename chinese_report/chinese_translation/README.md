
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt


运行
powershell
python -m uvicorn app.main:app --reload --reload-dir app


打开：

text
http://127.0.0.1:8000/


API 文档：

text
http://127.0.0.1:8000/docs


 初始管理员

一个全新的数据库会创建：

text
username: admin
password: change-me-admin-123


可以在第一次启动之前修改这些值：

powershell
$env:INITIAL_ADMIN_USERNAME="admin"
$env:INITIAL_ADMIN_PASSWORD="admin1234"
$env:SESSION_SECRET="a-long-random-session-secret"
python -m uvicorn app.main:app --reload --reload-dir app


 测试

powershell
pytest


当前测试套件包含 15 个测试。测试使用临时数据库，不会修改 `data/oj.db`。

 架构

text
请求
  -> 路由
  -> 服务
  -> 仓库
  -> sqlite

提交服务
  -> 评测器
  -> 运行器
  -> python 子进程


text
app/models/          pydantic 请求验证
app/routers/         异步 api 和 html 路由
app/services/        业务规则和权限
app/repositories/    参数化 sqlite 操作
app/judge/           子进程执行和结果比较
app/utils/           bcrypt、时间、错误和日志安全
frontend/templates/  jinja2 html 页面
frontend/static/     css 和题目表单 javascript
tests/               pytest 测试覆盖
data/oj.db            第一次启动时创建的数据库
data/backups/         管理员备份
report/report.md      项目报告
UPLOAD_ORDER.txt      带编号的提交顺序


 角色

- `student` 查看题目、提交 Python，并且只能查看自己受限的日志
- `teacher` 管理题目、查看所有提交、完整日志并进行重新评测
- `admin` 还可以管理用户、审计日志、备份和恢复

`is_active` 表示账户是否启用。在线状态通过 `last_seen_at` 计算。启动和正常关闭会清除所有在线状态值。退出登录会立即清除当前用户的在线状态。

 密码

密码只通过 `pwdlib[bcrypt]` 保存为带盐的 bcrypt 哈希值。

 评测器

每个测试用例都在独立的 Python 子进程中运行。项目从不使用 `eval()` 或 `exec()`。

text
AC 通过
WA 答案错误
RE 运行时错误或无效的 utf-8
TLE 超出时间限制
SE 系统错误


失败优先级：
SE -> TLE -> RE -> WA


兼容 Windows 的运行器在 `asyncio.to_thread` 中使用 `subprocess.Popen`。临时提交文件保存在操作系统的临时目录中，因此评测器创建 `main.py` 时，Uvicorn reload 不会重新启动。

 日志

大型日志字段最多保留 4000 个 Unicode 字符。学生响应中会移除隐藏测试用例的输入、预期输出和 stdout。绝对服务器路径会被清理。

审计操作包括：

text
VIEW_FULL_JUDGE_LOG
REJUDGE_SUBMISSION
UPDATE_USER_ROLE
DISABLE_USER
CREATE_BACKUP
RESTORE_BACKUP


 备份

text
POST /api/admin/backups
GET  /api/admin/backups
POST /api/admin/backups/{backup_id}/restore


每个备份包含 `oj.db` 和 `manifest.json`。恢复操作会验证 manifest id、必需文件和 SQLite 完整性，并在替换成功之前保留一个安全副本。

 主要 API

text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me

GET /api/users
GET /api/users/{user_id}
PUT /api/users/{user_id}

GET    /api/problems
GET    /api/problems/{problem_id}
POST   /api/problems
PUT    /api/problems/{problem_id}
DELETE /api/problems/{problem_id}

POST /api/submissions
GET  /api/submissions
GET  /api/submissions/{submission_id}
POST /api/submissions/{submission_id}/rejudge
GET  /api/submissions/{submission_id}/logs

GET /api/logs
GET /api/audit-logs

POST /api/admin/backups
GET  /api/admin/backups
POST /api/admin/backups/{backup_id}/restore
