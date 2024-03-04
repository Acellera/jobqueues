import traceback
import versioneer

try:
    __version__ = versioneer.get_version()
except Exception:
    print(traceback.format_exc())
    print("Could not get version. Defaulting to version 0")
    __version__ = "0"


# Fix conda meta.yaml
with open("package/jobqueues/meta.yaml", "r") as f:
    text = f.read()

text = text.replace("BUILD_VERSION_PLACEHOLDER", __version__)

# import toml

# pyproject = toml.load("pyproject.toml")
# deps = pyproject["project"]["dependencies"]

# text = text.replace(
#     "DEPENDENCY_PLACEHOLDER",
#     "".join(["    - {}\n".format(dep.strip()) for dep in deps]),
# )

with open("package/jobqueues/meta.yaml", "w") as f:
    f.write(text)
