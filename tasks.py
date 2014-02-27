"""invoke script for google-caja"""
from contextlib import contextmanager
import glob
import json
import os
from os.path import (exists, basename)
import shutil

cd = os.chdir
cp = shutil.copy2

from invoke import run, task

caja_mirror = "https://github.com/minrk/google-caja-mirror"
upstream = "upstream"
dest = "."
build_version = 0
patch_version = 0

@contextmanager
def cd(path):
    """context manager for running in a working directory"""
    save = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(save)

@task
def clean():
    """remove generated results"""
    for js in glob.glob("*.js"):
        print("removing %s" % js)
        os.unlink(js)

@task
def ant():
    """build caja with ant"""
    fetch(False)
    cp("git-svn-revision", "{}/tools/svnversion-nocolon".format(upstream))
    with cd(upstream):
        run("ant jars-no-src")

@task
def fetch(update=True):
    """fetch the actual google-caja repo into %s""" % upstream
    if not exists(upstream):
        run("git clone {} {} --depth 1".format(caja_mirror, upstream))
    elif update:
        with cd(upstream):
            run("git pull")

@task
def minify():
    """generate minified js with uglify.js
    
    There are problems with the minified output of ant.
    """
    for (src, minified) in [
        ("caja.js", "caja-minified.js"),
        ("html-sanitizer-bundle.js", "html-sanitizer-minified.js"),
        ("html-css-sanitizer-bundle.js", "html-css-sanitizer-minified.js"),
    ]:
        run("uglifyjs %s > %s" % (src, minified))

@task
def build():
    """build javascript targets, and stage them"""
    clean()
    ant()
    for f in glob.glob("{}/ant-lib/com/google/caja/plugin/*.js".format(upstream)):
        shutil.copy(f, basename(f))
    minify()

@task
def version():
    """write the svn revision to bower.json"""
    fetch(False)
    with cd(upstream):
        result = run("../git-svn-revision")
    revision = int(result.stdout)
    vs = "%i.%i.%i" % (revision, build_version, build_version)
    with open("bower.json") as f:
        info = json.load(f)
    info['version'] = vs
    with open("bower.json", 'w') as f:
        json.dump(info, f, sort_keys=True, indent=2)
    return vs

@task
def release():
    """publish a release of the package"""
    vs = version()
    
    run("git commit -a -m 'release %s'" % vs)
    run("git tag '%s'" % vs)
    run("git push")
    run("git push --tags")
