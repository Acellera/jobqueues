broker_url = "pyamqp://guest@localhost:5462//"
result_backend = "rpc://"

imports = ("jobqueues.celeryfiles.tasks",)

task_routes = {
    "jobqueues.celeryfiles.tasks.run_simulation": "gpu",
}
