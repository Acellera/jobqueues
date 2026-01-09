import yaml
import setuptools_scm

try:
    __version__ = setuptools_scm.get_version()
except Exception:
    print("Could not get version. Defaulting to version 0")
    __version__ = "0"

# Fix conda meta.yaml
with open("package/jobqueues/recipe_template.yaml", "r") as f:
    recipe = yaml.load(f, Loader=yaml.FullLoader)

recipe["package"]["version"] = __version__

with open("package/jobqueues/recipe.yaml", "w") as f:
    yaml.dump(recipe, f)
