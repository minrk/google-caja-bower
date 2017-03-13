"""invoke script for google-caja"""
from contextlib import contextmanager
import glob
import json
import os
from os.path import (exists, basename, join)
import shutil
from urllib.request import urlretrieve

cd = os.chdir
cp = shutil.copy2

from invoke import task

caja_mirror = "https://github.com/google/caja"
dest = "."
build_version = 0
patch_version = 0

upstream_parent = 'upstream'


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
def clean(ctx):
    """remove generated results"""
    for js in glob.glob("*.js"):
        print("removing %s" % js)
        os.remove(js)

@task
def ant(ctx, rev):
    """build caja with ant"""
    upstream = fetch(ctx, rev)
    with open("{}/tools/svnversion-nocolon".format(upstream), 'w') as f:
        f.write("#!/bin/sh\necho '%s'\n" % rev)
    with cd(upstream):
        ctx.run("ant jars-no-src")

@task
def fetch(ctx, rev):
    """fetch the actual google-caja repo from a tag"""
    # https://github.com/google/caja/archive/v6005.tar.gz
    if not exists(upstream_parent):
        os.mkdir(upstream_parent)
    path = os.path.abspath(join(upstream_parent, 'caja-%s' % rev))
    fname = path + '.tar.gz'
    url = 'https://github.com/google/caja/archive/v%s.tar.gz' % rev
    if not os.path.exists(fname):
        print("Downloading %s -> %s" % (url, fname))
        try:
            urlretrieve(url, fname)
        except Exception:
            if os.path.exists(fname):
                os.remove(fname)
            raise
    if not os.path.exists(path):
        with cd(upstream_parent):
            ctx.run("tar -xzf '{}'".format(fname))
    return path

@task
def minify(ctx):
    """generate minified js with uglify.js
    
    There are problems with the minified output of ant.
    """
    for (src, minified) in [
        ("caja.js", "caja-minified.js"),
        ("html-sanitizer-bundle.js", "html-sanitizer-minified.js"),
        ("html-css-sanitizer-bundle.js", "html-css-sanitizer-minified.js"),
    ]:
        ctx.run("uglifyjs %s > %s" % (src, minified))

@task
def build(ctx, rev):
    """build javascript targets, and stage them"""
    clean(ctx)
    upstream = fetch(ctx, rev)
    ant(ctx, rev)
    for f in glob.glob("{}/ant-lib/com/google/caja/plugin/*.js".format(upstream)):
        shutil.copy(f, basename(f))
    minify(ctx)
    version(ctx, rev)

@task
def version(ctx, rev):
    """write the svn revision to bower.json"""
    vs = "%s.%i.%i" % (rev, build_version, patch_version)
    with open("bower.json") as f:
        info = json.load(f)
    info['version'] = vs
    with open("bower.json", 'w') as f:
        json.dump(info, f, sort_keys=True, indent=2)
    return vs

@task
def release(ctx, rev):
    """publish a release of the package"""
    build(ctx, rev)
    vs = version(ctx, rev)
    
    ctx.run("git commit -a -m 'release %s'" % vs)
    ctx.run("git tag '%s'" % vs)
    print("Run `invoke push` to publish this tag")

@task
def push(ctx):
    ctx.run("git push")
    ctx.run("git push --tags")
