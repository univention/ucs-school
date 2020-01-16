Developer docu for building the UCS@school Kelvin REST API
==========================================================

The Univention style is brought in by the git submodule ``sphinx-univention``.

HTML is built using a Docker container with Sphinx: https://github.com/keimlink/docker-sphinx-doc

The initial ``docs`` content was created with::

    $ docker run -u "$(id -u):$(id -g)" -it --rm -v "$(pwd)/docs":/home/python/docs keimlink/sphinx-doc:1.7.1 sphinx-quickstart docs
